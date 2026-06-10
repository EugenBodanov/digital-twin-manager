from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
if str(TESTS_ROOT) not in sys.path:
  sys.path.insert(0, str(TESTS_ROOT))

from dependency_graph.helpers import TEMPLATE_PATH

from src.dependency_graph.loader import load_template_graph, parse_template_graph


class DependencyGraphLoaderTests(unittest.TestCase):
  def test_current_template_json_loads(self) -> None:
    graph = load_template_graph(TEMPLATE_PATH)

    self.assertEqual(1, graph.version)
    self.assertGreater(len(graph.templates), 0)

  def test_unsupported_dependency_type_fails_parsing(self) -> None:
    value = {
      "version": 1,
      "templates": [
        {
          "id": "core:l1:dispatcher_lambda:lambda_function",
          "owner_deployer": "DispatcherLambdaFunctionDeployer",
          "depends_on": [
            {
              "id": "core:l1:dispatcher_iam:iam",
              "type": "unknown_type",
            }
          ],
        }
      ],
    }

    with self.assertRaisesRegex(ValueError, "Unsupported dependency type"):
      parse_template_graph(value)


if __name__ == "__main__":
  unittest.main()
