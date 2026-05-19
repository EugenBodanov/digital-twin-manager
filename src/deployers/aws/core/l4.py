from deployers.aws.core.twinmaker_iam_role import TwinmakerIamRoleDeployer
from deployers.aws.core.twinmaker_s3_bucket import TwinmakerS3BucketDeployer
from deployers.aws.core.twinmaker_workspace import TwinmakerWorkspaceDeployer
from deployers.aws.core.plan_actions import sort_actions_for_apply
from deployers.base import Deployer

class L4Deployer(Deployer):
  DESTROY_ORDER = {
    "twinmaker_workspace": 0,
    "iam": 1,
    "s3_bucket": 2,
  }

  DEPLOY_ORDER = {
    "s3_bucket": 0,
    "iam": 1,
    "twinmaker_workspace": 2,
  }

  def log(self, message):
    print(message)

  def plan(self):
    actions = []
    actions.extend(TwinmakerS3BucketDeployer().plan())
    actions.extend(TwinmakerIamRoleDeployer().plan())
    actions.extend(TwinmakerWorkspaceDeployer().plan())
    return {
      "layer": "core_l4",
      "actions": actions,
    }

  def sort_actions_for_apply(self, actions):
    return sort_actions_for_apply(
      actions,
      self.DESTROY_ORDER,
      self.DEPLOY_ORDER,
    )

  def deploy(self):
    TwinmakerS3BucketDeployer().deploy()
    TwinmakerIamRoleDeployer().deploy()
    TwinmakerWorkspaceDeployer().deploy()

  def destroy(self):
    TwinmakerWorkspaceDeployer().destroy()
    TwinmakerIamRoleDeployer().destroy()
    TwinmakerS3BucketDeployer().destroy()

  def info(self):
    TwinmakerS3BucketDeployer().info()
    TwinmakerIamRoleDeployer().info()
    TwinmakerWorkspaceDeployer().info()
