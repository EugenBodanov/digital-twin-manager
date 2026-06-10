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


CONFIG_NAME = "config_iot_devices.json"

DEVICE_REQUIRED_KEYS = {
  "id",
  "properties",
}

DEVICE_OPTIONAL_KEYS = set()

PROPERTY_REQUIRED_KEYS = {
  "name",
  "dataType",
}

PROPERTY_OPTIONAL_KEYS = {
  "initValue",
}

SUPPORTED_DATA_TYPES = {
  "BOOLEAN",
  "DOUBLE",
  "INTEGER",
  "LONG",
  "STRING",
}

IOT_DEVICE_ID_PATTERN = r"[A-Za-z0-9_-]+"
PROPERTY_NAME_PATTERN = r"[A-Za-z0-9_-]+"
RESERVED_PROPERTY_NAMES = {
  "iotDeviceId",
  "time",
}


def validate(config):
  require_list(config, CONFIG_NAME)

  seen_device_ids = set()

  for index, iot_device in enumerate(config):
    _validate_iot_device(iot_device, index, seen_device_ids)


def _validate_iot_device(iot_device, index, seen_device_ids):
  field = f"{CONFIG_NAME}[{index}]"

  require_dict(iot_device, field)
  require_keys(iot_device, DEVICE_REQUIRED_KEYS, field)
  require_no_unknown_keys(
    iot_device,
    DEVICE_REQUIRED_KEYS | DEVICE_OPTIONAL_KEYS,
    field,
  )

  _validate_iot_device_id(iot_device["id"], f"{field}.id", seen_device_ids)
  _validate_properties(iot_device["properties"], f"{field}.properties")


def _validate_iot_device_id(value, field, seen_device_ids):
  require_string(value, field)

  if not re.fullmatch(IOT_DEVICE_ID_PATTERN, value):
    raise ValueError(f"{field} must match regex: {IOT_DEVICE_ID_PATTERN}")

  if value in seen_device_ids:
    raise ValueError(f"{field} is duplicated: {value}")

  seen_device_ids.add(value)


def _validate_properties(properties, field):
  require_list(properties, field)

  seen_property_names = set()

  for index, iot_property in enumerate(properties):
    _validate_property(iot_property, f"{field}[{index}]", seen_property_names)


def _validate_property(iot_property, field, seen_property_names):
  require_dict(iot_property, field)
  require_keys(iot_property, PROPERTY_REQUIRED_KEYS, field)
  require_no_unknown_keys(
    iot_property,
    PROPERTY_REQUIRED_KEYS | PROPERTY_OPTIONAL_KEYS,
    field,
  )

  _validate_property_name(
    iot_property["name"],
    f"{field}.name",
    seen_property_names,
  )
  _validate_data_type(iot_property["dataType"], f"{field}.dataType")

  if "initValue" in iot_property:
    _validate_init_value(
      iot_property["initValue"],
      iot_property["dataType"],
      f"{field}.initValue",
    )


def _validate_property_name(value, field, seen_property_names):
  require_string(value, field)

  if not re.fullmatch(PROPERTY_NAME_PATTERN, value):
    raise ValueError(f"{field} must match regex: {PROPERTY_NAME_PATTERN}")

  if value in RESERVED_PROPERTY_NAMES:
    raise ValueError(
      f"{field} must not use reserved property name: {value}"
    )

  if value in seen_property_names:
    raise ValueError(f"{field} is duplicated: {value}")

  seen_property_names.add(value)


def _validate_data_type(value, field):
  require_string(value, field)

  if value not in SUPPORTED_DATA_TYPES:
    raise ValueError(
      f"{field} must be one of: {keys_text(SUPPORTED_DATA_TYPES)}"
    )


def _validate_init_value(value, data_type, field):
  if data_type == "BOOLEAN":
    require_bool(value, field)
  elif data_type == "DOUBLE":
    _require_number(value, field)
  elif data_type in {"INTEGER", "LONG"}:
    _require_integer(value, field)
  elif data_type == "STRING":
    _require_string_value(value, field)

def _require_number(value, field):
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    raise ValueError(f"{field} must be a number.")


def _require_integer(value, field):
  if isinstance(value, bool) or not isinstance(value, int):
    raise ValueError(f"{field} must be an integer.")


def _require_string_value(value, field):
  if not isinstance(value, str):
    raise ValueError(f"{field} must be a string.")
