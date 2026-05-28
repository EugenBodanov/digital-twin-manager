from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.dependency_graph.loader import load_template_graph, parse_template_graph
from src.dependency_graph.mermaid import render_template_graph_mermaid
from src.dependency_graph.models import (
  DependencyType,
  TemplateDependency,
  TemplateGraph,
  TemplateNode,
)
from src.dependency_graph.template_to_mermaid import main as cli_main
from src.dependency_graph.validation import validate_template_graph


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "dependency" / "template.json"


class DependencyGraphTests(unittest.TestCase):
  def test_current_template_json_validates(self) -> None:
    graph = load_template_graph(TEMPLATE_PATH)

    validate_template_graph(graph)

    self.assertEqual(1, graph.version)
    self.assertGreater(len(graph.templates), 0)

  def test_missing_dependency_reference_fails_validation(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node(
          "core:l1:dispatcher_lambda:lambda_function",
          "core:l1:missing_iam:iam",
        ),
      ),
    )

    with self.assertRaisesRegex(ValueError, "depends on unknown template"):
      validate_template_graph(graph)

  def test_duplicate_template_id_fails_validation(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("core:l1:dispatcher_iam:iam"),
        template_node("core:l1:dispatcher_iam:iam"),
      ),
    )

    with self.assertRaisesRegex(ValueError, "Duplicate template id"):
      validate_template_graph(graph)

  def test_malformed_template_id_fails_validation(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(template_node("core:l1:dispatcher_iam"),),
    )

    with self.assertRaisesRegex(ValueError, "Template id must have format"):
      validate_template_graph(graph)

  def test_malformed_dependency_id_fails_validation(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node(
          "core:l1:dispatcher_lambda:lambda_function",
          "core:l1:dispatcher_iam",
        ),
      ),
    )

    with self.assertRaisesRegex(ValueError, "Template id must have format"):
      validate_template_graph(graph)

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

  def test_create_after_cycle_fails_validation(self) -> None:
    graph = TemplateGraph(
      version=1,
      templates=(
        template_node("core:l1:a:lambda_function", "core:l1:b:iam"),
        template_node("core:l1:b:iam", "core:l1:a:lambda_function"),
      ),
    )

    with self.assertRaisesRegex(ValueError, "create_after dependency cycle detected"):
      validate_template_graph(graph)

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

  def test_cli_writes_output_file(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
      output_path = Path(directory) / "template_dependency_graph.mmd"

      exit_code = cli_main(
        [
          "--input",
          str(TEMPLATE_PATH),
          "--output",
          str(output_path),
        ]
      )

      self.assertEqual(0, exit_code)
      self.assertTrue(output_path.is_file())
      self.assertIn("flowchart LR", output_path.read_text(encoding="utf-8"))


def template_node(template_id: str, dependency_id: str | None = None) -> TemplateNode:
  dependencies: tuple[TemplateDependency, ...] = ()

  if dependency_id is not None:
    dependencies = (
      TemplateDependency(
        id=dependency_id,
        type=DependencyType.CREATE_AFTER,
      ),
    )

  return TemplateNode(
    id=template_id,
    owner_deployer="TestDeployer",
    depends_on=dependencies,
  )


if __name__ == "__main__":
  unittest.main()
