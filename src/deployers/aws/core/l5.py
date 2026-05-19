from deployers.aws.core.grafana_iam_role import GrafanaIamRoleDeployer
from deployers.aws.core.grafana_workspace import GrafanaWorkspaceDeployer
from deployers.aws.core.plan_actions import sort_actions_for_apply
from deployers.base import Deployer

class L5Deployer(Deployer):
  DESTROY_ORDER = {
    "grafana_workspace": 0,
    "iam": 1,
  }

  DEPLOY_ORDER = {
    "iam": 0,
    "grafana_workspace": 1,
  }

  def log(self, message):
    print(message)

  def plan(self):
    actions = []
    actions.extend(GrafanaIamRoleDeployer().plan())
    actions.extend(GrafanaWorkspaceDeployer().plan())
    return {
      "layer": "core_l5",
      "actions": actions,
    }

  def sort_actions_for_apply(self, actions):
    return sort_actions_for_apply(
      actions,
      self.DESTROY_ORDER,
      self.DEPLOY_ORDER,
    )

  def deploy(self):
    GrafanaIamRoleDeployer().deploy()
    GrafanaWorkspaceDeployer().deploy()

  def destroy(self):
    GrafanaWorkspaceDeployer().destroy()
    GrafanaIamRoleDeployer().destroy()

  def info(self):
    GrafanaIamRoleDeployer().info()
    GrafanaWorkspaceDeployer().info()
