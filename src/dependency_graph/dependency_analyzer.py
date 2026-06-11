from __future__ import annotations

from dataclasses import dataclass
from typing import Any, MutableMapping, Sequence

from .models import DependencyType, RuntimeDependency, RuntimeGraph, RuntimeNode


PlanAction = MutableMapping[str, Any]
PlanGroup = MutableMapping[str, Any]

DEPLOY_DEPENDENCY_TYPES = {
  DependencyType.CREATE_AFTER,
  DependencyType.RUNTIME_USES,
}


@dataclass(frozen=True)
class _ReverseDependency:
  dependent: RuntimeNode
  dependency: RuntimeDependency


@dataclass(frozen=True)
class _AnalysisIndexes:
  previous_nodes: dict[str, RuntimeNode]
  desired_nodes: dict[str, RuntimeNode]
  previous_reverse_dependencies: dict[str, list[_ReverseDependency]]
  actions_by_graph_id: dict[str, list[PlanAction]]


def analyze_plan_dependencies(
  previous_graph: RuntimeGraph,
  desired_graph: RuntimeGraph,
  plan_groups: list[PlanGroup],
) -> list[PlanGroup]:
  indexes = _build_indexes(previous_graph, desired_graph, plan_groups)
  actions = list(_iter_plan_actions(plan_groups))

  while True:
    changed = False

    for action in actions:
      action_name = action.get("action")

      if action_name == "DEPLOY":
        changed = _analyze_deploy_action(action, indexes) or changed
      elif action_name == "DESTROY":
        changed = _analyze_destroy_action(action, indexes) or changed

    if not changed:
      break

  return plan_groups


def _build_indexes(
  previous_graph: RuntimeGraph,
  desired_graph: RuntimeGraph,
  plan_groups: list[PlanGroup],
) -> _AnalysisIndexes:
  return _AnalysisIndexes(
    previous_nodes=_nodes_by_id(previous_graph),
    desired_nodes=_nodes_by_id(desired_graph),
    previous_reverse_dependencies=_reverse_dependencies(previous_graph),
    actions_by_graph_id=_actions_by_graph_id(plan_groups),
  )


def _iter_plan_actions(plan_groups: Sequence[PlanGroup]):
  for group in plan_groups:
    for layer in group.get("layers", []):
      for action in layer.get("actions", []):
        yield action


def _nodes_by_id(graph: RuntimeGraph) -> dict[str, RuntimeNode]:
  return {node.id: node for node in graph.nodes}


def _reverse_dependencies(
  graph: RuntimeGraph,
) -> dict[str, list[_ReverseDependency]]:
  reverse_dependencies: dict[str, list[_ReverseDependency]] = {}

  for node in graph.nodes:
    for dependency in node.depends_on:
      reverse_dependencies.setdefault(dependency.id, []).append(
        _ReverseDependency(dependent=node, dependency=dependency)
      )

  return reverse_dependencies


def _actions_by_graph_id(plan_groups: Sequence[PlanGroup]) -> dict[str, list[PlanAction]]:
  actions_by_graph_id: dict[str, list[PlanAction]] = {}

  for action in _iter_plan_actions(plan_groups):
    graph_id = action.get("graph_id")

    if graph_id:
      actions_by_graph_id.setdefault(graph_id, []).append(action)

  return actions_by_graph_id


def _analyze_deploy_action(
  action: PlanAction,
  indexes: _AnalysisIndexes,
) -> bool:
  graph_id: str | None = action.get("graph_id")

  if not graph_id:
    return _add_blocker(
      action,
      "Cannot analyze DEPLOY dependencies because graph_id is missing.",
    )

  node = indexes.desired_nodes.get(graph_id)
  if node is None:
    return _add_blocker(
      action,
      f"Cannot deploy {graph_id} because it is missing from desired graph.",
    )

  changed = False

  for dependency in node.depends_on:
    if dependency.type not in DEPLOY_DEPENDENCY_TYPES:
      continue

    if dependency.id not in indexes.desired_nodes:
      changed = _add_blocker(
        action,
        (
          f"Cannot deploy {graph_id} because prerequisite {dependency.id} "
          f"({dependency.type.value}) is missing from desired graph."
        ),
      ) or changed
      continue

    blocked_prerequisites = _blocked_actions(
      indexes.actions_by_graph_id,
      dependency.id,
      "DEPLOY",
    )
    for blocked_action in blocked_prerequisites:
      changed = _add_blocker(
        action,
        (
          f"Cannot deploy {graph_id} because prerequisite deployment "
          f"{dependency.id} is blocked: {_blocker_summary(blocked_action)}"
        ),
      ) or changed

  return changed


def _analyze_destroy_action(
  action: PlanAction,
  indexes: _AnalysisIndexes,
) -> bool:
  graph_id: str | None = action.get("graph_id")

  if not graph_id:
    return _add_blocker(
      action,
      "Cannot analyze DESTROY dependencies because graph_id is missing.",
    )

  if graph_id not in indexes.previous_nodes:
    return _add_blocker(
      action,
      f"Cannot destroy {graph_id} because it is missing from previous graph.",
    )

  node = indexes.previous_nodes[graph_id]
  changed = False

  for reverse_dependency in indexes.previous_reverse_dependencies.get(graph_id, []):
    dependent = reverse_dependency.dependent
    remaining_dependent = indexes.desired_nodes.get(dependent.id)

    if remaining_dependent is None:
      continue

    if not _node_depends_on(remaining_dependent, graph_id):
      continue

    dependent_destroy_actions = _actions_with_name(
      indexes.actions_by_graph_id,
      dependent.id,
      "DESTROY",
    )

    if _has_unblocked_action(dependent_destroy_actions):
      continue

    if dependent_destroy_actions:
      changed = _add_blocker(
        action,
        (
          f"Cannot destroy {graph_id} because dependent destroy "
          f"{dependent.id} is blocked: "
          f"{_blocker_summary(dependent_destroy_actions[0])}"
        ),
      ) or changed
      continue

    if dependent.id not in indexes.actions_by_graph_id:
      if _should_ignore_dependent_without_plan_action(node, remaining_dependent):
        continue

      changed = _add_blocker(
        action,
        (
          f"Cannot destroy {graph_id} because {dependent.id} still depends on it "
          "in desired graph and has no plan action that would remove it."
        ),
      ) or changed
      continue

    changed = _add_blocker(
      action,
      (
        f"Cannot destroy {graph_id} because {dependent.id} still depends on it "
        "in desired graph."
      ),
    ) or changed

  return changed


def _should_ignore_dependent_without_plan_action(
  node: RuntimeNode,
  dependent: RuntimeNode,
) -> bool:
  if dependent.lifecycle_artifact:
    return True

  return dependent.owner_deployer == node.owner_deployer


def _node_depends_on(node: RuntimeNode, dependency_id: str) -> bool:
  return any(dependency.id == dependency_id for dependency in node.depends_on)


def _actions_with_name(
  actions_by_graph_id: dict[str, list[PlanAction]],
  graph_id: str,
  action_name: str,
) -> list[PlanAction]:
  return [
    action for action in actions_by_graph_id.get(graph_id, [])
    if action.get("action") == action_name
  ]


def _blocked_actions(
  actions_by_graph_id: dict[str, list[PlanAction]],
  graph_id: str,
  action_name: str,
) -> list[PlanAction]:
  return [
    action for action in _actions_with_name(
      actions_by_graph_id,
      graph_id,
      action_name,
    )
    if action.get("blocked", False)
  ]


def _has_unblocked_action(actions: Sequence[PlanAction]) -> bool:
  return any(not action.get("blocked", False) for action in actions)


def _add_blocker(action: PlanAction, message: str) -> bool:
  changed = False

  if not action.get("blocked", False):
    action["blocked"] = True
    changed = True

  blockers = action.setdefault("blockers", [])
  if message not in blockers:
    blockers.append(message)
    changed = True

  return changed


def _blocker_summary(action: PlanAction) -> str:
  blockers = action.get("blockers", [])

  if blockers:
    return "; ".join(str(blocker) for blocker in blockers)

  return "blocked by dependency analysis"
