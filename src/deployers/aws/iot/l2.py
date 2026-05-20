from deployers.aws.core.plan_actions import PlanResourceType, sort_actions_for_apply
from deployers.aws.iot.device_reconciliation import reconciled_iot_devices
from deployers.aws.iot.processor_iam_role import ProcessorIamRoleDeployer
from deployers.aws.iot.processor_lambda_function import ProcessorLambdaFunctionDeployer
from deployers.base import Deployer
import globals

class L2Deployer(Deployer):
  def log(self, message):
    print(f"IoT: {message}")

  DESTROY_ORDER:dict[PlanResourceType, int] = {
    "lambda_function": 0,
    "iam": 1,
  }

  DEPLOY_ORDER:dict[PlanResourceType, int] = {
    "iam": 0,
    "lambda_function": 1,
  }

  def plan(self):
    actions = []
    for previous_iot_device, desired_iot_device in reconciled_iot_devices():
      actions.extend(ProcessorIamRoleDeployer().plan(previous_iot_device, desired_iot_device))
      actions.extend(ProcessorLambdaFunctionDeployer().plan(previous_iot_device, desired_iot_device))
    return {
      "layer": "iot_l2",
      "actions": actions
    }

  def sort_actions_for_apply(self, actions):
    return sort_actions_for_apply(
      actions,
      self.DESTROY_ORDER,
      self.DEPLOY_ORDER,
    )

  def deploy(self):
    for iot_device in globals.config_iot_devices:
      ProcessorIamRoleDeployer().deploy(iot_device)
      ProcessorLambdaFunctionDeployer().deploy(iot_device)

  def destroy(self):
    for iot_device in globals.config_iot_devices:
      ProcessorLambdaFunctionDeployer().destroy(iot_device)
      ProcessorIamRoleDeployer().destroy(iot_device)

  def info(self):
    for iot_device in globals.config_iot_devices:
      ProcessorIamRoleDeployer().info(iot_device)
      ProcessorLambdaFunctionDeployer().info(iot_device)
