from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
if str(TESTS_ROOT) not in sys.path:
  sys.path.insert(0, str(TESTS_ROOT))

from dependency_graph.helpers import TEMPLATE_PATH, template_node

import resource_names
from src.dependency_graph.loader import load_template_graph
from src.dependency_graph.models import (
  DependencyType,
  TemplateDependency,
  TemplateGraph,
  TemplateNode,
)
from src.dependency_graph.runtime_graph_builder import build_runtime_graph


class RuntimeGraphBuilderTests(unittest.TestCase):
  def test_runtime_graph_builds_shared_core_nodes(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("core:l3_hot:hot_dynamodb_table:dynamodb_table"),
        TemplateNode(
          id="core:l3_hot:hot_dynamodb_backup:dynamodb_backup",
          owner_deployer="HotDynamodbTableDeployer",
          depends_on=(
            TemplateDependency(
              id="core:l3_hot:hot_dynamodb_table:dynamodb_table",
              type=DependencyType.CREATE_AFTER,
            ),
          ),
          lifecycle_artifact=True,
        ),
      ),
    )

    runtime_graph = build_runtime_graph(graph, config(), [], [], [])
    nodes_by_id = runtime_nodes_by_id(runtime_graph)
    table_node = nodes_by_id[
      "core:l3_hot:hot_dynamodb_table:dynamodb_table:hot-iot-data"
    ]
    backup_node = nodes_by_id[
      "core:l3_hot:hot_dynamodb_backup:dynamodb_backup:hot-iot-data-backup"
    ]

    self.assertEqual("hot-iot-data", table_node.logical_name)
    self.assertEqual("dt-hot-iot-data", table_node.physical_name)
    self.assertEqual("TestDeployer", table_node.owner_deployer)
    self.assertFalse(table_node.lifecycle_artifact)
    self.assertTrue(backup_node.lifecycle_artifact)
    self.assertEqual(
      ["core:l3_hot:hot_dynamodb_table:dynamodb_table:hot-iot-data"],
      dependency_ids(backup_node),
    )

  def test_runtime_graph_builds_iot_l1_device_resources(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("iot:l1:iot_thing:iot_thing"),
        template_node(
          "iot:l1:iot_certificate:iot_certificate",
          "iot:l1:iot_thing:iot_thing",
        ),
        template_node(
          "iot:l1:iot_auth_files:local_auth_files",
          "iot:l1:iot_certificate:iot_certificate",
        ),
      ),
    )

    runtime_graph = build_runtime_graph(
      graph,
      config(),
      [{"id": "sensor-1", "properties": []}],
      [],
      [],
    )
    nodes_by_id = runtime_nodes_by_id(runtime_graph)
    thing_node = nodes_by_id["iot:l1:iot_thing:iot_thing:sensor-1"]
    certificate_node = nodes_by_id["iot:l1:iot_certificate:iot_certificate:sensor-1"]
    auth_files_node = nodes_by_id["iot:l1:iot_auth_files:local_auth_files:sensor-1"]

    self.assertEqual("dt-sensor-1", thing_node.physical_name)
    self.assertIsNone(certificate_node.physical_name)
    self.assertEqual("iot_devices_auth/sensor-1", auth_files_node.physical_name)
    self.assertEqual(
      ["iot:l1:iot_thing:iot_thing:sensor-1"],
      dependency_ids(certificate_node),
    )
    self.assertEqual(
      ["iot:l1:iot_certificate:iot_certificate:sensor-1"],
      dependency_ids(auth_files_node),
    )

  def test_runtime_graph_builds_iot_l2_processor_dependencies(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("iot:l2:processor_iam:iam"),
        template_node(
          "iot:l2:processor_lambda:lambda_function",
          "iot:l2:processor_iam:iam",
        ),
      ),
    )

    runtime_graph = build_runtime_graph(
      graph,
      config(),
      [{"id": "sensor-1", "properties": []}],
      [],
      [],
    )
    nodes_by_id = runtime_nodes_by_id(runtime_graph)
    lambda_node = nodes_by_id[
      "iot:l2:processor_lambda:lambda_function:sensor-1-processor"
    ]

    self.assertEqual("sensor-1-processor", lambda_node.logical_name)
    self.assertEqual("dt-sensor-1-processor", lambda_node.physical_name)
    self.assertEqual(
      ["iot:l2:processor_iam:iam:sensor-1-processor"],
      dependency_ids(lambda_node),
    )

  def test_runtime_graph_builds_hierarchy_to_component_type_dependencies(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("core:l4:twinmaker_workspace:twinmaker_workspace"),
        template_node(
          "iot:l4:device_component_type:twinmaker_component_type",
          "core:l4:twinmaker_workspace:twinmaker_workspace",
        ),
        TemplateNode(
          id="hierarchy:hierarchy:twinmaker_hierarchy:twinmaker_hierarchy",
          owner_deployer="TwinmakerHierarchyDeployer",
          depends_on=(
            TemplateDependency(
              id="iot:l4:device_component_type:twinmaker_component_type",
              type=DependencyType.RUNTIME_USES,
            ),
          ),
        ),
        template_node(
          "hierarchy:hierarchy:twinmaker_entity:twinmaker_entity",
          "hierarchy:hierarchy:twinmaker_hierarchy:twinmaker_hierarchy",
        ),
        template_node(
          "hierarchy:hierarchy:twinmaker_component:twinmaker_component",
          "hierarchy:hierarchy:twinmaker_entity:twinmaker_entity",
          "iot:l4:device_component_type:twinmaker_component_type",
        ),
      ),
    )

    runtime_graph = build_runtime_graph(
      graph,
      {"digital_twin_name": "dt"},
      [{"id": "sensor-1", "properties": []}],
      [],
      [
        {
          "id": "root-1",
          "type": "entity",
          "children": [
            {
              "id": "room-1",
              "type": "entity",
              "children": [
                {
                  "type": "component",
                  "name": "temperature",
                  "iotDeviceId": "sensor-1",
                },
              ],
            },
          ],
        },
      ],
    )
    nodes_by_id = {node.id: node for node in runtime_graph.nodes}

    root_node = nodes_by_id[
      "hierarchy:hierarchy:twinmaker_hierarchy:twinmaker_hierarchy:root-1"
    ]
    component_node = nodes_by_id[
      "hierarchy:hierarchy:twinmaker_component:twinmaker_component:room-1.temperature"
    ]

    self.assertIn(
      "iot:l4:device_component_type:twinmaker_component_type:sensor-1",
      [dependency.id for dependency in root_node.depends_on],
    )
    self.assertEqual(
      {
        "hierarchy:hierarchy:twinmaker_entity:twinmaker_entity:room-1",
        "iot:l4:device_component_type:twinmaker_component_type:sensor-1",
      },
      {dependency.id for dependency in component_node.depends_on},
    )

  def test_runtime_graph_builds_init_value_publish_dependencies(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("iot:l2:processor_lambda:lambda_function"),
        template_node("init_values:init_values:init_value:init_value"),
        template_node(
          "init_values:init_values:init_value_mqtt_publish:iot_message",
          "init_values:init_values:init_value:init_value",
          "iot:l2:processor_lambda:lambda_function",
        ),
      ),
    )

    runtime_graph = build_runtime_graph(
      graph,
      {"digital_twin_name": "dt"},
      [
        {
          "id": "sensor-1",
          "properties": [
            {
              "name": "temperature",
              "dataType": "DOUBLE",
              "initValue": 20,
            },
          ],
        },
      ],
      [],
      [],
    )
    nodes_by_id = {node.id: node for node in runtime_graph.nodes}
    publish_node = nodes_by_id[
      "init_values:init_values:init_value_mqtt_publish:iot_message:sensor-1"
    ]

    self.assertEqual(
      {
        "init_values:init_values:init_value:init_value:sensor-1",
        "iot:l2:processor_lambda:lambda_function:sensor-1-processor",
      },
      {dependency.id for dependency in publish_node.depends_on},
    )

  def test_runtime_graph_builds_only_local_event_action_resources(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("event_actions:event_actions:event_action:event_action"),
        template_node(
          "event_actions:event_actions:event_action_iam:iam",
          "event_actions:event_actions:event_action:event_action",
        ),
        template_node(
          "event_actions:event_actions:event_action_lambda:lambda_function",
          "event_actions:event_actions:event_action_iam:iam",
        ),
      ),
    )
    external_event = event("externalAlert", external=True)
    local_event = event("localAlert", external=False)
    local_event_id = resource_names.event_action_id(local_event)

    runtime_graph = build_runtime_graph(
      graph,
      config(),
      [],
      [external_event, local_event],
      [],
    )
    nodes_by_id = runtime_nodes_by_id(runtime_graph)

    self.assertIn(
      f"event_actions:event_actions:event_action:event_action:"
      f"{resource_names.event_action_id(external_event)}",
      nodes_by_id,
    )
    self.assertIn(
      f"event_actions:event_actions:event_action:event_action:{local_event_id}",
      nodes_by_id,
    )
    self.assertIn(
      f"event_actions:event_actions:event_action_iam:iam:{local_event_id}",
      nodes_by_id,
    )
    self.assertIn(
      f"event_actions:event_actions:event_action_lambda:lambda_function:{local_event_id}",
      nodes_by_id,
    )
    self.assertNotIn(
      f"event_actions:event_actions:event_action_iam:iam:"
      f"{resource_names.event_action_id(external_event)}",
      nodes_by_id,
    )
    self.assertEqual(
      "dt-localAlert",
      nodes_by_id[
        f"event_actions:event_actions:event_action_lambda:lambda_function:"
        f"{local_event_id}"
      ].physical_name,
    )

  def test_runtime_graph_rejects_duplicate_runtime_ids(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("hierarchy:hierarchy:twinmaker_hierarchy:twinmaker_hierarchy"),
      ),
    )

    with self.assertRaisesRegex(ValueError, "Duplicate runtime dependency node id"):
      build_runtime_graph(
        graph,
        config(),
        [],
        [],
        [
          {"id": "root-1", "type": "entity", "children": []},
          {"id": "root-1", "type": "entity", "children": []},
        ],
      )

  def test_current_template_json_builds_runtime_graph_for_current_configs(self) -> None:
    graph = load_template_graph(TEMPLATE_PATH)

    runtime_graph = build_runtime_graph(
      graph,
      config(),
      [{"id": "sensor-1", "properties": []}],
      [event("localAlert", external=False)],
      [
        {
          "id": "root-1",
          "type": "entity",
          "children": [
            {
              "type": "component",
              "name": "temperature",
              "iotDeviceId": "sensor-1",
            },
          ],
        },
      ],
    )

    self.assertEqual(graph.version, runtime_graph.version)
    self.assertGreater(len(runtime_graph.nodes), 0)
    self.assertIn(
      "iot:l2:processor_lambda:lambda_function:sensor-1-processor",
      runtime_nodes_by_id(runtime_graph),
    )


def config() -> dict:
  return {"digital_twin_name": "dt"}


def event(function_name: str, external: bool) -> dict:
  return {
    "condition": "root.component.value > 10",
    "action": {
      "type": "lambda",
      "functionName": function_name,
      "external": external,
    },
  }


def runtime_nodes_by_id(runtime_graph):
  return {node.id: node for node in runtime_graph.nodes}


def dependency_ids(runtime_node):
  return [dependency.id for dependency in runtime_node.depends_on]


if __name__ == "__main__":
  unittest.main()
