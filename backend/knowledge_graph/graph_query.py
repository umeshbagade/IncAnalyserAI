"""
Graph Query Interface
Provides high-level queries on the Knowledge Graph for the analysis pipeline.
Used by the API to: find impacted systems, trace root cause paths,
and understand data flow context from a user's incident description.
"""

from .build_graph import KnowledgeGraph


class GraphQuery:
    """
    High-level query interface over the KnowledgeGraph.
    Maps incident description keywords to graph nodes and traverses relationships.
    """

    SYSTEM_ALIASES = {
        "saturn": ["saturn", "saturn_v1", "reporting", "report"],
        "datahub": ["data_hub", "datahub", "treasury_data_hub", "dh", "data hub"],
        "ingestion": ["upload_ingestion", "ingestion", "pe_ingestion", "upload", "sftp", "feed"],
    }

    def __init__(self, graph: KnowledgeGraph = None):
        self.graph = graph or KnowledgeGraph()
        self._is_built = False

    def ensure_built(self):
        """Build the graph if not already built."""
        if not self._is_built:
            self.graph.build_from_directory()
            self._is_built = True

    def find_matching_nodes(self, description: str) -> list:
        """
        Given a user incident description, find relevant graph nodes.
        Matches by system name aliases and keyword overlap.
        """
        self.ensure_built()
        desc_lower = description.lower()
        matched_nodes = set()

        # Match by system aliases
        for category, aliases in self.SYSTEM_ALIASES.items():
            for alias in aliases:
                if alias in desc_lower:
                    for node in self.graph.graph.nodes():
                        if category in node.lower() or alias in node.lower():
                            matched_nodes.add(node)

        # Match by direct node name overlap
        for node in self.graph.graph.nodes():
            node_lower = node.lower()
            words = desc_lower.split()
            for word in words:
                if len(word) > 3 and word in node_lower:
                    matched_nodes.add(node)

        return list(matched_nodes)

    def get_upstream_chain(self, node: str, max_depth: int = 5) -> list:
        """
        Traverse upstream from a node to find root causes / source feeds.
        Returns list of paths (each path is a list of nodes).
        """
        self.ensure_built()
        return self.graph.traverse_upstream(node, max_depth)

    def get_downstream_chain(self, node: str, max_depth: int = 5) -> list:
        """
        Traverse downstream from a node to find impacted systems / reports.
        Returns list of paths (each path is a list of nodes).
        """
        self.ensure_built()
        return self.graph.traverse_downstream(node, max_depth)

    def get_impact_analysis(self, node: str) -> dict:
        """
        Full impact analysis for a given node:
        - upstream sources
        - downstream impacts
        - all paths
        """
        self.ensure_built()
        upstream = self.get_upstream_chain(node)
        downstream = self.get_downstream_chain(node)

        all_upstream_nodes = set()
        for path in upstream:
            all_upstream_nodes.update(path)
        all_downstream_nodes = set()
        for path in downstream:
            all_downstream_nodes.update(path)

        return {
            "node": node,
            "upstream_sources": list(all_upstream_nodes - {node}),
            "downstream_impacts": list(all_downstream_nodes - {node}),
            "upstream_paths": upstream,
            "downstream_paths": downstream,
            "total_upstream_nodes": len(all_upstream_nodes) - 1,
            "total_downstream_nodes": len(all_downstream_nodes) - 1,
        }

    def analyze_description(self, description: str) -> dict:
        """
        Full analysis pipeline from a user incident description:
        1. Find matching nodes
        2. For each matched node, get impact analysis
        3. Aggregate results
        """
        self.ensure_built()
        matched_nodes = self.find_matching_nodes(description)

        if not matched_nodes:
            return {
                "matched_nodes": [],
                "summary": "No matching systems found in the knowledge graph for this description.",
                "impact_analyses": [],
                "all_upstream_sources": [],
                "all_downstream_impacts": [],
            }

        analyses = []
        all_upstream = set()
        all_downstream = set()

        for node in matched_nodes:
            analysis = self.get_impact_analysis(node)
            analyses.append(analysis)
            all_upstream.update(analysis["upstream_sources"])
            all_downstream.update(analysis["downstream_impacts"])

        return {
            "matched_nodes": matched_nodes,
            "summary": (
                f"Found {len(matched_nodes)} matching system(s) in the knowledge graph. "
                f"Identified {len(all_upstream)} upstream source(s) and "
                f"{len(all_downstream)} downstream impact(s)."
            ),
            "impact_analyses": analyses,
            "all_upstream_sources": list(all_upstream),
            "all_downstream_impacts": list(all_downstream),
        }

    def get_graph_stats(self) -> dict:
        """Get statistics about the knowledge graph."""
        self.ensure_built()
        return self.graph.get_stats()

    def get_all_domains(self) -> list:
        """Get all domains present in the graph."""
        self.ensure_built()
        return self.graph.get_domains()

    def get_all_edges(self) -> list:
        """Get all edges in the graph with metadata."""
        self.ensure_built()
        edges = []
        for u, v, data in self.graph.graph.edges(data=True):
            edges.append({
                "from": u,
                "to": v,
                "via": data.get("via", "unknown"),
                "domain": data.get("domain", "unknown"),
            })
        return edges

