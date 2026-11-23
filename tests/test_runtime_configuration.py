from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tests.aws_stubs import install_aws_stubs

install_aws_stubs()

import deployment_state
import globals


class RuntimeConfigurationTests(unittest.TestCase):
  def test_config_loaders_use_config_directory_environment_variable(self) -> None:
    values_by_file = {
      "config.json": {"digital_twin_name": "test-twin"},
      "config_iot_devices.json": [{"id": "sensor-1"}],
      "config_events.json": [{"condition": "value > 1"}],
      "config_hierarchy.json": {"root": "factory"},
      "config_providers.json": {"provider": "aws"},
    }

    with tempfile.TemporaryDirectory() as config_dir:
      for file_name, value in values_by_file.items():
        path = Path(config_dir) / file_name
        path.write_text(json.dumps(value), encoding="utf-8")

      with patch.dict(
        os.environ,
        {globals.CONFIG_DIR_ENV: config_dir},
        clear=False,
      ):
        globals.initialize_config()
        globals.initialize_config_iot_devices()
        globals.initialize_config_events()
        globals.initialize_config_hierarchy()
        globals.initialize_config_providers()

    self.assertEqual(values_by_file["config.json"], globals.config)
    self.assertEqual(
      values_by_file["config_iot_devices.json"],
      globals.config_iot_devices,
    )
    self.assertEqual(values_by_file["config_events.json"], globals.config_events)
    self.assertEqual(
      values_by_file["config_hierarchy.json"],
      globals.config_hierarchy,
    )
    self.assertEqual(
      values_by_file["config_providers.json"],
      globals.config_providers,
    )

  def test_aws_environment_overrides_credentials_file(self) -> None:
    file_credentials = {
      "aws_access_key_id": "file-access-key",
      "aws_secret_access_key": "file-secret-key",
      "aws_region": "file-region",
    }

    with tempfile.TemporaryDirectory() as config_dir:
      credentials_path = Path(config_dir) / "config_credentials.json"
      credentials_path.write_text(
        json.dumps(file_credentials),
        encoding="utf-8",
      )

      with patch.dict(
        os.environ,
        {
          globals.CONFIG_DIR_ENV: config_dir,
          "AWS_ACCESS_KEY_ID": "env-access-key",
          "AWS_SECRET_ACCESS_KEY": "env-secret-key",
          "AWS_REGION": "",
          "AWS_DEFAULT_REGION": "env-region",
        },
        clear=False,
      ):
        globals.initialize_config_credentials()

    self.assertEqual(
      {
        "aws_access_key_id": "env-access-key",
        "aws_secret_access_key": "env-secret-key",
        "aws_region": "env-region",
      },
      globals.config_credentials,
    )

  def test_aws_environment_can_supply_credentials_without_file(self) -> None:
    with tempfile.TemporaryDirectory() as config_dir:
      with patch.dict(
        os.environ,
        {
          globals.CONFIG_DIR_ENV: config_dir,
          "AWS_ACCESS_KEY_ID": "env-access-key",
          "AWS_SECRET_ACCESS_KEY": "env-secret-key",
          "AWS_REGION": "env-region",
          "AWS_DEFAULT_REGION": "",
        },
        clear=False,
      ):
        globals.initialize_config_credentials()

    self.assertEqual(
      {
        "aws_access_key_id": "env-access-key",
        "aws_secret_access_key": "env-secret-key",
        "aws_region": "env-region",
      },
      globals.config_credentials,
    )

  def test_state_and_config_snapshots_use_runtime_directories(self) -> None:
    config_values = {
      "config.json": {"digital_twin_name": "test-twin"},
      "config_iot_devices.json": [{"id": "sensor-1"}],
      "config_events.json": [],
      "config_hierarchy.json": {"root": "factory"},
    }

    with (
      tempfile.TemporaryDirectory() as config_dir,
      tempfile.TemporaryDirectory() as state_dir,
    ):
      for file_name, value in config_values.items():
        path = Path(config_dir) / file_name
        path.write_text(json.dumps(value), encoding="utf-8")

      globals.config = config_values["config.json"]
      globals.config_credentials = {"aws_region": "eu-west-1"}

      with patch.dict(
        os.environ,
        {
          globals.CONFIG_DIR_ENV: config_dir,
          deployment_state.STATE_DIR_ENV: state_dir,
        },
        clear=False,
      ):
        copied_paths = deployment_state.save_last_applied_config_state()

        self.assertEqual(
          Path(state_dir),
          Path(deployment_state.state_dir_path()),
        )
        self.assertEqual(
          {
            Path(state_dir) / "configs" / file_name
            for file_name in config_values
          },
          {Path(path) for path in copied_paths},
        )

        for file_name, value in config_values.items():
          snapshot_path = Path(state_dir) / "configs" / file_name
          self.assertEqual(
            value,
            json.loads(snapshot_path.read_text(encoding="utf-8")),
          )


@pytest.mark.parametrize("commands", [["init-state"], []], ids=["one-shot", "interactive"])
def test_cli_bootstraps_state_with_relative_paths(commands, tmp_path, monkeypatch):
  configs = REPO_ROOT / "configs" / "validation" / "valid"
  events = json.loads((configs / "config_events.json").read_text(encoding="utf-8"))
  events[0]["action"].update(external=False, pathToCode="source/not-mounted")
  (tmp_path / "events.json").write_text(json.dumps(events), encoding="utf-8")

  monkeypatch.setenv(globals.CONFIG_DIR_ENV, str(configs))
  monkeypatch.setenv("AWS_ACCESS_KEY_ID", "A" * 20)
  monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "B" * 40)
  monkeypatch.setenv("AWS_REGION", "eu-west-1")
  monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
  result = subprocess.run(
    [sys.executable, str(REPO_ROOT / "src" / "main.py"), *commands,
     "--events", "events.json", "--state", "state", "--output", "output", "--pems", "certs"],
    cwd=tmp_path, input="init-state\nexit\n", capture_output=True, text=True, timeout=30,
  )

  assert result.returncode == 0, result.stderr
  snapshot = tmp_path / "state" / "configs" / "config_events.json"
  assert json.loads(snapshot.read_text(encoding="utf-8")) == events
  assert (tmp_path / "certs").is_dir()
  assert (tmp_path / "output").is_dir()


if __name__ == "__main__":
  unittest.main()
