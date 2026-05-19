from typing import Any, Literal, TypedDict, Unpack


PlanActionName = Literal[
    # Resource is the same in both desired config and last-applied state.
    # Apply should do nothing for this resource.
    "NO_CHANGE",

    # Resource id exists in desired config, but does not exist in last-applied state.
    # Apply should create/deploy resources for this id.
    "DEPLOY",

    # Resource id exists in last-applied state, but does not exist in desired config.
    # Apply should destroy resources for this id using last-applied state.
    "DESTROY",
]


class PlannedAction(TypedDict):
    resource: Any
    resource_type: str
    action: PlanActionName
    blocked: bool
    required_flags: list[str]
    blockers: list[str]
    state_sync_required: bool


class PlannedActionValues(TypedDict, total=False):
    action: PlanActionName
    blocked: bool
    required_flags: list[str]
    blockers: list[str]
    state_sync_required: bool
    region: str


def plan_action(
    resource: Any,
    resource_type: str,
    **values: Unpack[PlannedActionValues],
) -> PlannedAction:
    action: PlannedAction = {
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

def sort_actions_for_apply(
    actions: list[PlannedAction],
    destroy_order: dict[str, int],
    deploy_order: dict[str, int],
) -> list[PlannedAction]:
    destroy_actions = [
        action for action in actions
        if action["action"] == "DESTROY"
    ]
    deploy_actions = [
        action for action in actions
        if action["action"] == "DEPLOY"
    ]

    destroy_actions.sort(
        key=lambda action: destroy_order[action["resource_type"]]
    )
    deploy_actions.sort(
        key=lambda action: deploy_order[action["resource_type"]]
    )

    return destroy_actions + deploy_actions
