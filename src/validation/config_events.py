import json
import re

from .common import (
  keys_text,
  require_bool,
  require_dict,
  require_keys,
  require_list,
  require_no_unknown_keys,
  require_string,
)


CONFIG_NAME = "config_events.json"

EVENT_REQUIRED_KEYS = {
  "condition",
  "action",
}

EVENT_OPTIONAL_KEYS = set()

ACTION_REQUIRED_KEYS = {
  "type",
  "functionName",
  "external",
}

ACTION_OPTIONAL_KEYS = {
  "pathToCode",
  "feedback",
}

FEEDBACK_REQUIRED_KEYS = {
  "type",
  "payload",
}

FEEDBACK_TARGET_KEYS = {
  "topic",
  "iotDeviceId",
}

FEEDBACK_OPTIONAL_KEYS = FEEDBACK_TARGET_KEYS

ACTION_TYPES = {
  "lambda",
}

FEEDBACK_TYPES = {
  "mqtt",
}

CONDITION_OPERATORS = {
  "<",
  ">",
  "==",
}

PATH_OPERAND_PATTERN = r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
DOUBLE_CONSTANT_PATTERN = r"DOUBLE\(-?\d+\)"
INTEGER_CONSTANT_PATTERN = r"INTEGER\(-?\d+\)"
STRING_CONSTANT_PATTERN = r"STRING\([^().\s]*\)"
FUNCTION_NAME_PATTERN = r"[A-Za-z0-9_-]+"
IOT_DEVICE_ID_PATTERN = r"[A-Za-z0-9_-]+"


def validate(config):
  require_list(config, CONFIG_NAME)

  seen_events = set()
  seen_internal_function_names = set()

  for index, event in enumerate(config):
    _validate_event(
      event,
      f"{CONFIG_NAME}[{index}]",
      seen_events,
      seen_internal_function_names,
    )


def _validate_event(event, field, seen_events, seen_internal_function_names):
  require_dict(event, field)
  require_keys(event, EVENT_REQUIRED_KEYS, field)
  require_no_unknown_keys(event, EVENT_REQUIRED_KEYS | EVENT_OPTIONAL_KEYS, field)

  _validate_unique_event(event, field, seen_events)
  _validate_condition(event["condition"], f"{field}.condition")
  _validate_action(
    event["action"],
    f"{field}.action",
    seen_internal_function_names,
  )


def _validate_condition(value, field):
  require_string(value, field)

  parts = value.split()

  if len(parts) != 3:
    raise ValueError(
      f"{field} must have format: '<left> <operator> <right>'"
    )

  left_operand, operator, right_operand = parts

  if operator not in CONDITION_OPERATORS:
    raise ValueError(
      f"{field} operator must be one of: {keys_text(CONDITION_OPERATORS)}"
    )

  _validate_condition_operand(left_operand, f"{field}.left")
  _validate_condition_operand(right_operand, f"{field}.right")


def _validate_condition_operand(value, field):
  if re.fullmatch(PATH_OPERAND_PATTERN, value):
    return

  if _is_typed_constant(value):
    return

  raise ValueError(
    f"{field} must be a path 'entity.component.property' or a typed constant."
  )


def _validate_action(action, field, seen_internal_function_names):
  require_dict(action, field)
  require_keys(action, ACTION_REQUIRED_KEYS, field)
  require_no_unknown_keys(
    action,
    ACTION_REQUIRED_KEYS | ACTION_OPTIONAL_KEYS,
    field,
  )

  _validate_action_type(action["type"], f"{field}.type")
  _validate_function_name(action["functionName"], f"{field}.functionName")
  require_bool(action["external"], f"{field}.external")

  if action["external"] and "pathToCode" in action:
    raise ValueError(f"{field}.pathToCode is only valid when external is false.")

  if not action["external"]:
    _validate_internal_function_name(
      action["functionName"],
      f"{field}.functionName",
      seen_internal_function_names,
    )

  if "pathToCode" in action:
    require_string(action["pathToCode"], f"{field}.pathToCode")

  if "feedback" in action:
    _validate_feedback(action["feedback"], f"{field}.feedback")


def _validate_feedback(feedback, field):
  require_dict(feedback, field)
  require_keys(feedback, FEEDBACK_REQUIRED_KEYS, field)
  require_no_unknown_keys(
    feedback,
    FEEDBACK_REQUIRED_KEYS | FEEDBACK_OPTIONAL_KEYS,
    field,
  )

  _validate_feedback_type(feedback["type"], f"{field}.type")
  _validate_feedback_target(feedback, field)
  _validate_feedback_payload(feedback["payload"], f"{field}.payload")


def _validate_unique_event(event, field, seen_events):
  event_payload = json.dumps(
    event,
    sort_keys=True,
    separators=(",", ":"),
  )

  if event_payload in seen_events:
    raise ValueError(f"{field} duplicates another event rule.")

  seen_events.add(event_payload)


def _validate_action_type(value, field):
  require_string(value, field)

  if value not in ACTION_TYPES:
    raise ValueError(f"{field} must be one of: {keys_text(ACTION_TYPES)}")


def _validate_function_name(value, field):
  require_string(value, field)

  if not re.fullmatch(FUNCTION_NAME_PATTERN, value):
    raise ValueError(f"{field} must match regex: {FUNCTION_NAME_PATTERN}")


def _validate_internal_function_name(value, field, seen_internal_function_names):
  if value in seen_internal_function_names:
    raise ValueError(
      f"{field} duplicates another internal event action function: {value}"
    )

  seen_internal_function_names.add(value)


def _validate_feedback_type(value, field):
  require_string(value, field)

  if value not in FEEDBACK_TYPES:
    raise ValueError(f"{field} must be one of: {keys_text(FEEDBACK_TYPES)}")


def _validate_feedback_target(feedback, field):
  target_keys = FEEDBACK_TARGET_KEYS & feedback.keys()

  if len(target_keys) != 1:
    raise ValueError(
      f"{field} must contain exactly one of: {keys_text(FEEDBACK_TARGET_KEYS)}"
    )

  if "topic" in feedback:
    _validate_topic(feedback["topic"], f"{field}.topic")
  else:
    _validate_iot_device_id(feedback["iotDeviceId"], f"{field}.iotDeviceId")


def _validate_feedback_payload(value, field):
  try:
    json.dumps(value)
  except (TypeError, ValueError) as error:
    raise ValueError(f"{field} must be JSON serializable.") from error


def _validate_topic(value, field):
  require_string(value, field)

  if any(char.isspace() for char in value):
    raise ValueError(f"{field} must not contain whitespace.")


def _validate_iot_device_id(value, field):
  require_string(value, field)

  if not re.fullmatch(IOT_DEVICE_ID_PATTERN, value):
    raise ValueError(f"{field} must match regex: {IOT_DEVICE_ID_PATTERN}")


def _is_typed_constant(value):
  return (
    re.fullmatch(DOUBLE_CONSTANT_PATTERN, value)
    or re.fullmatch(INTEGER_CONSTANT_PATTERN, value)
    or re.fullmatch(STRING_CONSTANT_PATTERN, value)
  )
