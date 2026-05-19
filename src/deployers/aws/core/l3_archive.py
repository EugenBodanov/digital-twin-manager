from deployers.aws.core.archive_s3_bucket import ArchiveS3BucketDeployer
from deployers.aws.core.plan_actions import sort_actions_for_apply
from deployers.base import Deployer

class L3ArchiveDeployer(Deployer):
  def log(self, message):
    print(message)

  DESTROY_ORDER = {
    "s3_bucket": 0,
  }

  DEPLOY_ORDER = {
    "s3_bucket": 0,
  }

  def plan(self):
    return {
      "layer": "core_l3_archive",
      "actions": ArchiveS3BucketDeployer().plan(),
    }

  def deploy(self):
    ArchiveS3BucketDeployer().deploy()

  def sort_actions_for_apply(self, actions):
    return sort_actions_for_apply(actions, self.DESTROY_ORDER, self.DEPLOY_ORDER)

  def destroy(self):
    ArchiveS3BucketDeployer().destroy()

  def info(self):
    ArchiveS3BucketDeployer().info()
