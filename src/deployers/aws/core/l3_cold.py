from deployers.aws.core.cold_archive_mover_event_rule import ColdArchiveMoverEventRuleDeployer
from deployers.aws.core.cold_archive_mover_iam_role import ColdArchiveMoverIamRoleDeployer
from deployers.aws.core.cold_archive_mover_lambda_function import ColdArchiveMoverLambdaFunctionDeployer
from deployers.aws.core.cold_s3_bucket import ColdS3BucketDeployer
from deployers.aws.core.plan_actions import sort_actions_for_apply
from deployers.base import Deployer

class L3ColdDeployer(Deployer):
  def log(self, message):
    print(message)

  DESTROY_ORDER = {
    "event_rule": 0,
    "lambda_function": 1,
    "iam": 2,
    "s3_bucket": 3,
  }

  DEPLOY_ORDER = {
    "s3_bucket": 0,
    "iam": 1,
    "lambda_function": 2,
    "event_rule": 3,
  }

  def plan(self):
    actions = []
    actions.extend(ColdS3BucketDeployer().plan())
    actions.extend(ColdArchiveMoverIamRoleDeployer().plan())
    actions.extend(ColdArchiveMoverLambdaFunctionDeployer().plan())
    actions.extend(ColdArchiveMoverEventRuleDeployer().plan())
    return {
      "layer": "core_l3_cold",
      "actions": actions,
    }

  def sort_actions_for_apply(self, actions):
    return sort_actions_for_apply(
      actions,
      self.DESTROY_ORDER,
      self.DEPLOY_ORDER,
    )

  def deploy(self):
    ColdS3BucketDeployer().deploy()
    ColdArchiveMoverIamRoleDeployer().deploy()
    ColdArchiveMoverLambdaFunctionDeployer().deploy()
    ColdArchiveMoverEventRuleDeployer().deploy()

  def destroy(self):
    ColdArchiveMoverEventRuleDeployer().destroy()
    ColdArchiveMoverLambdaFunctionDeployer().destroy()
    ColdArchiveMoverIamRoleDeployer().destroy()
    ColdS3BucketDeployer().destroy()

  def info(self):
    ColdS3BucketDeployer().info()
    ColdArchiveMoverIamRoleDeployer().info()
    ColdArchiveMoverLambdaFunctionDeployer().info()
    ColdArchiveMoverEventRuleDeployer().info()
