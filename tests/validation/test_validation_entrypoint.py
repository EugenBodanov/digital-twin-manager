from __future__ import annotations

import unittest
import sys
from pathlib import Path

import src.validation as validation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import valid_config_set


class ValidationEntrypointTests(unittest.TestCase):
  def test_validate_all_configs_passes_for_valid_set(self) -> None:
    configs = valid_config_set()

    validation.validate_all_configs(
      configs["config"],
      configs["config_credentials"],
      configs["config_events"],
      configs["config_hierarchy"],
      configs["config_iot_devices"],
      configs["config_providers"],
    )

  def test_validate_all_configs_runs_cross_config_checks(self) -> None:
    configs = valid_config_set()
    configs["config_events"][0]["condition"] = (
      "room-1.temperatureSensor.missing > INTEGER(80)"
    )

    with self.assertRaisesRegex(ValueError, "unknown property"):
      validation.validate_all_configs(
        configs["config"],
        configs["config_credentials"],
        configs["config_events"],
        configs["config_hierarchy"],
        configs["config_iot_devices"],
        configs["config_providers"],
      )


if __name__ == "__main__":
  unittest.main()
