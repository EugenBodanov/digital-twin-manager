ACTION_DEPLOY = "DEPLOY"
ACTION_DESTROY = "DESTROY"
ACTION_NO_CHANGE = "NO_CHANGE"

ACTIONABLE_ACTIONS = (ACTION_DESTROY, ACTION_DEPLOY)


def pending_actions(actions, action_name):
  return [
    action for action in actions
    if action["action"] == action_name
    and not action.get("processed", False)
    and not action.get("blocked", False)
  ]


def deploy_groups(plan):
  return plan


def destroy_groups(plan):
  return reversed(plan)

