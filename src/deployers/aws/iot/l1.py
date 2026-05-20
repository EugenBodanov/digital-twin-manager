from deployers.aws.iot.iot_thing import IotThingDeployer
from deployers.aws.iot.device_reconciliation import reconciled_iot_devices
from deployers.base import Deployer
import globals

class L1Deployer(Deployer):
  def log(self, message):
    print(f"IoT: {message}")

  def plan(self):
    actions = []
    for previous_iot_device, desired_iot_device in reconciled_iot_devices():
      actions.extend(IotThingDeployer().plan(previous_iot_device, desired_iot_device))
    return {
      "layer": "iot_l1",
      "actions": actions
    }

  def deploy(self):
    for iot_device in globals.config_iot_devices:
      IotThingDeployer().deploy(iot_device)

  def destroy(self):
    for iot_device in globals.config_iot_devices:
      IotThingDeployer().destroy(iot_device)

  def info(self):
    for iot_device in globals.config_iot_devices:
      IotThingDeployer().info(iot_device)
