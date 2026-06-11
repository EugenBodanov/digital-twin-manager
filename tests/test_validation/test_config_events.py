from __future__ import annotations
import unittest
from src.validation import config_events
from validation_helpers import clone, valid_config_events


class ConfigEventsValidationTests(unittest.TestCase):
  def test_valid_config_events_passes(self) -> None:
    config_events.validate(valid_config_events())

  def test_condition_without_required_spaces_fails(self) -> None:
    value = valid_config_events()
    value[0]["condition"] = "room-1.temperatureSensor.temperature>INTEGER(80)"

    with self.assertRaisesRegex(ValueError, "must have format"):
      config_events.validate(value)

  def test_unsupported_action_type_fails(self) -> None:
    value = valid_config_events()
    value[0]["action"]["type"] = "sns"

    with self.assertRaisesRegex(ValueError, "must be one of"):
      config_events.validate(value)

  def test_path_to_code_with_external_action_fails(self) -> None:
    value = valid_config_events()
    value[0]["action"]["pathToCode"] = "lambda_functions/event_actions/alert"

    with self.assertRaisesRegex(ValueError, "only valid when external is false"):
      config_events.validate(value)

  def test_feedback_without_single_target_fails(self) -> None:
    value = valid_config_events()
    value[0]["action"]["feedback"]["topic"] = "alerts"

    with self.assertRaisesRegex(ValueError, "exactly one"):
      config_events.validate(value)

  def test_duplicate_internal_function_name_fails(self) -> None:
    value = [
      {
        "condition": "room-1.temperatureSensor.temperature > INTEGER(80)",
        "action": {
          "type": "lambda",
          "functionName": "alertAction",
          "external": False,
        },
      },
      {
        "condition": "room-1.temperatureSensor.temperature == INTEGER(80)",
        "action": {
          "type": "lambda",
          "functionName": "alertAction",
          "external": False,
        },
      },
    ]

    with self.assertRaisesRegex(ValueError, "duplicates another internal"):
      config_events.validate(value)

  def test_decimal_typed_constant_fails_current_runtime_parser(self) -> None:
    value = clone(valid_config_events())
    value[0]["condition"] = "room-1.temperatureSensor.temperature > DOUBLE(80.5)"

    with self.assertRaisesRegex(ValueError, "typed constant"):
      config_events.validate(value)


if __name__ == "__main__":
  unittest.main()
