from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
if str(TESTS_ROOT) not in sys.path:
  sys.path.insert(0, str(TESTS_ROOT))

from dependency_graph.helpers import template_node

from src.dependency_graph.mermaid import render_template_graph_mermaid
from src.dependency_graph.models import TemplateGraph


class DependencyGraphMermaidTests(unittest.TestCase):
  def test_mermaid_output_is_deterministic_and_typed(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("core:l1:dispatcher_iam:iam"),
        template_node(
          "core:l1:dispatcher_lambda:lambda_function",
          "core:l1:dispatcher_iam:iam",
        ),
      ),
    )

    first_output = render_template_graph_mermaid(graph)
    second_output = render_template_graph_mermaid(graph)

    self.assertEqual(first_output, second_output)
    self.assertIn("flowchart LR", first_output)
    self.assertIn("core / l1", first_output)
    self.assertIn("core:l1:dispatcher_iam:iam", first_output)
    self.assertIn("owner: TestDeployer", first_output)
    self.assertIn("-->|create_after|", first_output)


if __name__ == "__main__":
  unittest.main()
