from deployers.aws.core.dispatcher_iam_role import DispatcherIamRoleDeployer
from deployers.aws.core.dispatcher_iot_rule import DispatcherIotRuleDeployer
from deployers.aws.core.dispatcher_lambda_function import DispatcherLambdaFunctionDeployer
from deployers.aws.core.plan_actions import sort_actions_for_apply
from deployers.base import Deployer

class L1Deployer(Deployer):
  DESTROY_ORDER = {
    "iot_rule": 0,
    "lambda_function": 1,
    "iam": 2,
  }

  DEPLOY_ORDER = {
    "iam": 0,
    "lambda_function": 1,
    "iot_rule": 2,
  }

  def log(self, message):
    print(message)

  def plan(self):
    actions = []
    actions.extend(DispatcherIamRoleDeployer().plan())
    actions.extend(DispatcherLambdaFunctionDeployer().plan())
    actions.extend(DispatcherIotRuleDeployer().plan())
    return {
      "layer": "core_l1",
      "actions": actions,
    }

  def sort_actions_for_apply(self, actions):
    return sort_actions_for_apply(
      actions,
      self.DESTROY_ORDER,
      self.DEPLOY_ORDER,
    )

  def deploy(self):
    DispatcherIamRoleDeployer().deploy()
    DispatcherLambdaFunctionDeployer().deploy()
    DispatcherIotRuleDeployer().deploy()

  def destroy(self):
    DispatcherIotRuleDeployer().destroy()
    DispatcherLambdaFunctionDeployer().destroy()
    DispatcherIamRoleDeployer().destroy()

  def info(self):
    DispatcherIamRoleDeployer().info()
    DispatcherLambdaFunctionDeployer().info()
    DispatcherIotRuleDeployer().info()
