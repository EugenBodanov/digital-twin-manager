from pathlib import Path


SRC_DEPENDENCY_GRAPH = Path(__file__).resolve().parents[2] / "src" / "dependency_graph"

# Full test discovery imports this package before some deployers import
# dependency_graph.plan_graph_ids, so include the production package path too.
if str(SRC_DEPENDENCY_GRAPH) not in __path__:
  __path__.insert(0, str(SRC_DEPENDENCY_GRAPH))
