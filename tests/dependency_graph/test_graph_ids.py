from __future__ import annotations

import unittest
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
if str(TESTS_ROOT) not in sys.path:
  sys.path.insert(0, str(TESTS_ROOT))

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
  sys.path.append(str(SRC_PATH))

from src.dependency_graph import plan_graph_ids
from src.dependency_graph.graph_ids import runtime_node_id


class GraphIdTests(unittest.TestCase):
  def test_runtime_node_id_uses_template_id_and_logical_name(self) -> None:
    self.assertEqual(
      "core:l1:dispatcher_iam:iam:dispatcher",
      runtime_node_id("core:l1:dispatcher_iam:iam", "dispatcher"),
    )

  def test_plan_graph_ids_match_runtime_graph_format(self) -> None:
    self.assertEqual(
      "iot:l2:processor_lambda:lambda_function:sensor-1-processor",
      plan_graph_ids.processor_lambda({"id": "sensor-1"}),
    )
    self.assertEqual(
      "hierarchy:hierarchy:twinmaker_hierarchy:twinmaker_hierarchy:root-1",
      plan_graph_ids.twinmaker_hierarchy("root-1"),
    )


if __name__ == "__main__":
  unittest.main()
