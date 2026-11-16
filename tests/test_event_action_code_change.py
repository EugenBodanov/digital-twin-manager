from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tests.aws_stubs import install_aws_stubs

install_aws_stubs()

import deployment_state
import globals
import resource_names
from deployers.aws.event_actions.lambda_actions import LambdaActionsDeployer


class EventActionCodeChangeTests(unittest.TestCase):
  def setUp(self) -> None:
    self.cwd = os.getcwd()
    self.tmp = tempfile.TemporaryDirectory()
    os.chdir(self.tmp.name)
    os.makedirs("microgrid/battery/trigger")
    self._write_code("v1")

    self.event = {
      "condition": "x == x",
      "action": {
        "type": "lambda",
        "functionName": "trigger",
        "external": False,
        "pathToCode": "microgrid/battery/trigger",
      },
    }
    self.action_id = resource_names.event_action_id(self.event)
    globals.config_events = [self.event]
    deployment_state.last_applied_config_events = [self.event]
    deployment_state.last_applied_code_hashes = deployment_state.current_code_hashes()

  def tearDown(self) -> None:
    os.chdir(self.cwd)
    self.tmp.cleanup()

  def _write_code(self, body: str) -> None:
    Path("microgrid/battery/trigger/lambda_function.py").write_text(body, encoding="utf-8")

  def _actions(self) -> list[str]:
    return [a.get("action") for a in LambdaActionsDeployer().plan()]

  def test_unchanged_code_is_up_to_date(self) -> None:
    self.assertEqual(["NO_CHANGE"], self._actions())

  def test_changed_code_is_destroyed_and_redeployed(self) -> None:
    self._write_code("v2")
    self.assertEqual(["DESTROY", "DEPLOY"], self._actions())

  def test_zip_artifact_in_code_folder_is_ignored(self) -> None:
    Path("microgrid/battery/trigger/zipped.zip").write_bytes(b"archive")
    self.assertEqual(["NO_CHANGE"], self._actions())

  def test_state_without_code_hashes_counts_as_unchanged(self) -> None:
    deployment_state.last_applied_code_hashes = {}
    self._write_code("v2")
    self.assertEqual(["NO_CHANGE"], self._actions())


if __name__ == "__main__":
  unittest.main()
