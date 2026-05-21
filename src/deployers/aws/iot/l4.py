from deployers.aws.iot.device_reconciliation import reconciled_iot_devices
from deployers.aws.iot.twinmaker_component_type import TwinmakerComponentTypeDeployer
from deployers.aws.apply_actions import pending_actions
from deployers.base import Deployer
import deployment_state
import globals

class L4Deployer(Deployer):
  def log(self, message):
    print(f"IoT: {message}")

  def plan(self):
    actions = []
    for previous_iot_device, desired_iot_device in reconciled_iot_devices():
      actions.extend(TwinmakerComponentTypeDeployer().plan(previous_iot_device, desired_iot_device))
    return {
      "layer": "iot_l4",
      "actions": actions
    }

  def _iot_device_for_action(self, action):
    resource = action["resource"]

    if action["action"] == "DESTROY":
      for iot_device in deployment_state.last_applied_config_iot_devices:
        if deployment_state.last_applied_twinmaker_component_type_id(iot_device) == resource:
          return iot_device

    if action["action"] == "DEPLOY":
      for iot_device in globals.config_iot_devices:
        if globals.twinmaker_component_type_id(iot_device) == resource:
          return iot_device

    return None

  def apply(self, layer_plan, action_name):
    layer_name = layer_plan["layer"]
    actions = pending_actions(layer_plan["actions"], action_name)

    if not actions:
      return

    for action in actions:
      resource_type = action["resource_type"]
      resource = action["resource"]

      if resource_type != "twinmaker_component_type":
        raise ValueError(
          f"No iot_l4 apply handler for {resource_type}/{resource}"
        )

      iot_device = self._iot_device_for_action(action)

      if iot_device is None:
        raise ValueError(
          f"No IoT device config found for planned TwinMaker component type: {resource}"
        )

      TwinmakerComponentTypeDeployer().apply(action, iot_device, resource)
      deployment_state.mark_plan_action_processed("iot", layer_name, action)

  def deploy(self):
    for iot_device in globals.config_iot_devices:
      TwinmakerComponentTypeDeployer().deploy(iot_device)

  def destroy(self):
    for iot_device in globals.config_iot_devices:
      TwinmakerComponentTypeDeployer().destroy(iot_device)

  def info(self):
    for iot_device in globals.config_iot_devices:
      TwinmakerComponentTypeDeployer().info(iot_device)
