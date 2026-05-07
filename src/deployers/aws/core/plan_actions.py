def plan_action(resource, resource_type, **values):
  action = {
    "resource": resource,
    "resource_type": resource_type,
    "action": "NO_CHANGE",
    "blocked": False,
    "required_flags": [],
    "blockers": [],
    "state_sync_required": False,
  }

  action.update(values)
  return action
