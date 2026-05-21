from deployers.aws.core.grafana_iam_role import GrafanaIamRoleDeployer
from deployers.aws.core.grafana_workspace import GrafanaWorkspaceDeployer
from deployers.aws.core.plan_actions import sort_actions_for_apply
from deployers.aws.apply_actions import pending_actions
from deployers.base import Deployer
import deployment_state
import globals

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

  def apply(self, layer_plan, action_name):
    layer_name = layer_plan["layer"]
    actions = pending_actions(layer_plan["actions"], action_name)

    if not actions:
      return

    actions = self.sort_actions_for_apply(actions)

    for action in actions:
      resource_type = action["resource_type"]
      resource = action["resource"]

      if (
        resource_type == "iam"
        and resource in [deployment_state.last_applied_grafana_iam_role_name(), globals.grafana_iam_role_name()]
      ):
        GrafanaIamRoleDeployer().apply(action, resource)
      elif (
        resource_type == "grafana_workspace"
        and resource in [deployment_state.last_applied_grafana_workspace_name(), globals.grafana_workspace_name()]
      ):
        GrafanaWorkspaceDeployer().apply(action, resource)
      else:
        raise ValueError(
          f"No core_l5 apply handler for {resource_type}/{resource}"
        )

      deployment_state.mark_plan_action_processed("core", layer_name, action)

  def deploy(self):
    GrafanaIamRoleDeployer().deploy()
    GrafanaWorkspaceDeployer().deploy()

  def destroy(self):
    GrafanaWorkspaceDeployer().destroy()
    GrafanaIamRoleDeployer().destroy()

  def info(self):
    GrafanaIamRoleDeployer().info()
    GrafanaWorkspaceDeployer().info()
