import json
import os
import shutil
from datetime import datetime, timezone

import globals


STATE_VERSION = 1
STATE_DIR_NAME = ".digital-twin-manager-state"
STATE_CONFIG_DIR_NAME = "configs"
STATE_METADATA_FILE_NAME = "metadata.json"
STATE_PLAN_FILE_NAME = "plan.json"

STATE_CONFIG_FILE_NAMES = [
  "config.json",
  "config_iot_devices.json",
  "config_events.json",
  "config_hierarchy.json",
]

last_applied_config = {}
last_applied_config_iot_devices = []
last_applied_config_events = []
last_applied_config_hierarchy = {}
last_applied_state_metadata = {}


def state_dir_path():
  return os.path.join(globals.project_path(), STATE_DIR_NAME)


def state_config_dir_path():
  return os.path.join(state_dir_path(), STATE_CONFIG_DIR_NAME)


def state_metadata_file_path():
  return os.path.join(state_dir_path(), STATE_METADATA_FILE_NAME)


def state_plan_file_path():
  return os.path.join(state_dir_path(), STATE_PLAN_FILE_NAME)


def state_config_file_path(file_name):
  return os.path.join(state_config_dir_path(), file_name)


def last_applied_digital_twin_name():
  if not last_applied_config:
    initialize_last_applied_config_state()

  return last_applied_config["digital_twin_name"]


def last_applied_digital_twin_info():
  if not last_applied_config:
    initialize_last_applied_config_state()

  return {
    "config": last_applied_config,
    "config_iot_devices": last_applied_config_iot_devices,
    "config_events": last_applied_config_events
  }


def last_applied_aws_region():
  if not last_applied_state_metadata:
    initialize_last_applied_config_state()

  return last_applied_state_metadata["awsRegion"]


def last_applied_dispatcher_iam_role_name():
  return last_applied_digital_twin_name() + "-dispatcher"


def last_applied_dispatcher_lambda_function_name():
  return last_applied_digital_twin_name() + "-dispatcher"


def last_applied_dispatcher_iot_rule_name():
  rule_name = last_applied_digital_twin_name() + "-trigger-dispatcher"
  return rule_name.replace("-", "_")


def last_applied_dispatcher_iot_rule_topic():
  return last_applied_digital_twin_name() + "/iot-data"

def last_applied_persister_iam_role_name():
  return last_applied_digital_twin_name() + "-persister"

def last_applied_persister_lambda_function_name():
  return last_applied_digital_twin_name() + "-persister"

def last_applied_hot_dynamodb_table_name():
  return last_applied_digital_twin_name() + "-hot-iot-data"

def last_applied_event_feedback_iam_role_name():
  return last_applied_digital_twin_name() + "-event-feedback"


def last_applied_event_feedback_lambda_function_name():
  return last_applied_digital_twin_name() + "-event-feedback"


def last_applied_event_checker_iam_role_name():
  return last_applied_digital_twin_name() + "-event-checker"


def last_applied_event_checker_lambda_function_name():
  return last_applied_digital_twin_name() + "-event-checker"


def last_applied_lambda_chain_iam_role_name():
  return last_applied_digital_twin_name() + "-lambda-chain"


def last_applied_lambda_chain_step_function_name():
  return last_applied_digital_twin_name() + "-lambda-chain"


def last_applied_event_registry_register_iam_role_name():
  return last_applied_digital_twin_name() + "-event-registry-register"


def last_applied_event_registry_register_lambda_function_name():
  return last_applied_digital_twin_name() + "-event-registry-register"

def last_applied_hot_cold_mover_iam_role_name():
  return last_applied_digital_twin_name() + "-hot-to-cold-mover"

def last_applied_hot_cold_mover_lambda_function_name():
  return last_applied_digital_twin_name() + "-hot-to-cold-mover"

def last_applied_hot_cold_mover_event_rule_name():
  return last_applied_digital_twin_name() + "-hot-to-cold-mover"

def last_applied_hot_reader_iam_role_name():
  return last_applied_digital_twin_name() + "-hot-reader"

def last_applied_hot_reader_lambda_function_name():
    return last_applied_digital_twin_name() + "-hot-reader"

def last_applied_cold_s3_bucket_name():
    return (last_applied_digital_twin_name() + "-cold-iot-data").lower()

def last_applied_cold_archive_mover_iam_role_name():
  return last_applied_digital_twin_name() + "-cold-to-archive-mover"

def last_applied_cold_archive_mover_lambda_function_name():
  return last_applied_digital_twin_name() + "-cold-to-archive-mover"

def last_applied_cold_archive_mover_event_rule_name():
  return last_applied_digital_twin_name() + "-cold-to-archive-mover"

def last_applied_archive_s3_bucket_name():
  return (last_applied_digital_twin_name() + "-archive-iot-data").lower()


def last_applied_twinmaker_s3_bucket_name():
  return (last_applied_digital_twin_name() + "-twinmaker").lower()


def last_applied_twinmaker_iam_role_name():
  return last_applied_digital_twin_name() + "-twinmaker"


def last_applied_twinmaker_workspace_name():
  return last_applied_digital_twin_name() + "-twinmaker"


def last_applied_grafana_workspace_name():
  return last_applied_digital_twin_name() + "-grafana"


def last_applied_grafana_iam_role_name():
  return last_applied_digital_twin_name() + "-grafana"

def last_applied_iot_thing_name(iot_device):
  return last_applied_digital_twin_name() + "-" + iot_device["id"]

def last_applied_iot_thing_policy_name(iot_device):
  return last_applied_digital_twin_name() + "-" + iot_device["id"]

def _read_json(path):
  with open(path, "r") as file:
    return json.load(file)


def _write_json(path, value):
  with open(path, "w") as file:
    json.dump(value, file, indent=2)
    file.write("\n")


def _copy_config_file(file_name):
  source_path = os.path.join(globals.project_path(), file_name)

  if not os.path.isfile(source_path):
    raise FileNotFoundError(f"Config file does not exist: {source_path}")

  target_path = state_config_file_path(file_name)
  shutil.copyfile(source_path, target_path)
  return target_path


def _state_file_paths():
  paths = [state_metadata_file_path()]

  for file_name in STATE_CONFIG_FILE_NAMES:
    paths.append(state_config_file_path(file_name))

  return paths


def _missing_state_file_paths():
  missing_paths = []

  for path in _state_file_paths():
    if not os.path.isfile(path):
      missing_paths.append(path)

  return missing_paths


def _build_metadata():
  return {
    "stateVersion": STATE_VERSION,
    "digitalTwinName": globals.config.get("digital_twin_name"),
    "awsRegion": globals.config_credentials.get("aws_region"),
    "configFiles": STATE_CONFIG_FILE_NAMES,
    "updatedAt": datetime.now(timezone.utc).isoformat(),
  }


def initialize_last_applied_config_state():
  global last_applied_config
  global last_applied_config_iot_devices
  global last_applied_config_events
  global last_applied_config_hierarchy
  global last_applied_state_metadata

  missing_paths = _missing_state_file_paths()

  if missing_paths:
    missing_paths_text = ", ".join(missing_paths)
    raise FileNotFoundError(
      "Redeployment state is not initialized. "
      f"Missing state file(s): {missing_paths_text}. "
      "Run 'init-state' or complete 'deploy' first."
    )

  last_applied_config = _read_json(state_config_file_path("config.json"))
  last_applied_config_iot_devices = _read_json(
    state_config_file_path("config_iot_devices.json")
  )
  last_applied_config_events = _read_json(state_config_file_path("config_events.json"))
  last_applied_config_hierarchy = _read_json(
    state_config_file_path("config_hierarchy.json")
  )
  last_applied_state_metadata = _read_json(state_metadata_file_path())


def save_last_applied_config_state():
  os.makedirs(state_config_dir_path(), exist_ok=True)

  copied_paths = []
  for file_name in STATE_CONFIG_FILE_NAMES:
    copied_paths.append(_copy_config_file(file_name))

  _write_json(state_metadata_file_path(), _build_metadata())
  initialize_last_applied_config_state()
  return copied_paths


def save_plan_actions(actions):
  os.makedirs(state_dir_path(), exist_ok=True)
  _write_json(state_plan_file_path(), actions)
  return state_plan_file_path()


def last_applied_processor_iam_role_name(iot_device):
    return last_applied_digital_twin_name() + "-" + iot_device["id"] + "-processor"

def last_applied_processor_lambda_function_name_local(iot_device):
  return iot_device["id"]

def last_applied_processor_lambda_function_name(iot_device):
  return last_applied_digital_twin_name() + "-" + last_applied_processor_lambda_function_name_local(iot_device) + "-processor"


def last_applied_twinmaker_component_type_id(iot_device):
  return last_applied_digital_twin_name() + "-" + iot_device["id"]
