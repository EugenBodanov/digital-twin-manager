from deployers.aws.core.hot_cold_mover_event_rule import HotColdMoverEventRuleDeployer
from deployers.aws.core.hot_cold_mover_iam_role import HotColdMoverIamRoleDeployer
from deployers.aws.core.hot_cold_mover_lambda_function import HotColdMoverLambdaFunctionDeployer
from deployers.aws.core.hot_dynamodb_table import HotDynamodbTableDeployer
from deployers.aws.core.hot_reader_iam_role import HotReaderIamRoleDeployer
from deployers.aws.core.hot_reader_lambda_function import HotReaderLambdaFunctionDeployer
from deployers.aws.core.plan_actions import sort_actions_for_apply
from deployers.base import Deployer

class L3HotDeployer(Deployer):
  def log(self, message):
    print(message)

  DESTROY_ORDER = {
    "eventbridge_rule": 0,
    "lambda_function": 1,
    "iam": 2,
    "dynamodb_table": 3,
  }

  DEPLOY_ORDER = {
    "dynamodb_table": 0,
    "iam": 1,
    "lambda_function": 2,
    "eventbridge_rule": 3,
  }

  def plan(self):
    actions = []
    actions.extend(HotDynamodbTableDeployer().plan())
    actions.extend(HotColdMoverIamRoleDeployer().plan())
    actions.extend(HotColdMoverLambdaFunctionDeployer().plan())
    actions.extend(HotColdMoverEventRuleDeployer().plan())
    actions.extend(HotReaderIamRoleDeployer().plan())
    actions.extend(HotReaderLambdaFunctionDeployer().plan())
    return {
      "layer": "core_l3_hot",
      "actions": actions,
    }

  def sort_actions_for_apply(self, actions):
    return sort_actions_for_apply(
      actions,
      self.DESTROY_ORDER,
      self.DEPLOY_ORDER,
    )

  def deploy(self):
    HotDynamodbTableDeployer().deploy()
    HotColdMoverIamRoleDeployer().deploy()
    HotColdMoverLambdaFunctionDeployer().deploy()
    HotColdMoverEventRuleDeployer().deploy()
    HotReaderIamRoleDeployer().deploy()
    HotReaderLambdaFunctionDeployer().deploy()

  def destroy(self):
    HotReaderLambdaFunctionDeployer().destroy()
    HotReaderIamRoleDeployer().destroy()
    HotColdMoverEventRuleDeployer().destroy()
    HotColdMoverLambdaFunctionDeployer().destroy()
    HotColdMoverIamRoleDeployer().destroy()
    HotDynamodbTableDeployer().destroy()

  def info(self):
    HotDynamodbTableDeployer().info()
    HotColdMoverIamRoleDeployer().info()
    HotColdMoverLambdaFunctionDeployer().info()
    HotColdMoverEventRuleDeployer().info()
    HotReaderIamRoleDeployer().info()
    HotReaderLambdaFunctionDeployer().info()
