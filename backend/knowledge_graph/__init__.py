"""Knowledge Graph module for IncAnalyserAI.
Parses lineage.yml files from all reporting domains into a directed graph
for upstream/downstream traversal, path finding, and impact analysis.
"""

from .build_graph import KnowledgeGraph
from .graph_query import GraphQuery

__all__ = ["KnowledgeGraph", "GraphQuery"]

