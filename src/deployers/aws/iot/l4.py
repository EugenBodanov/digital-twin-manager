from deployers.aws.iot.device_reconciliation import reconciled_iot_devices
from deployers.aws.iot.twinmaker_component_type import TwinmakerComponentTypeDeployer
from deployers.base import Deployer
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

  def deploy(self):
    for iot_device in globals.config_iot_devices:
      TwinmakerComponentTypeDeployer().deploy(iot_device)

  def destroy(self):
    for iot_device in globals.config_iot_devices:
      TwinmakerComponentTypeDeployer().destroy(iot_device)

  def info(self):
    for iot_device in globals.config_iot_devices:
      TwinmakerComponentTypeDeployer().info(iot_device)
