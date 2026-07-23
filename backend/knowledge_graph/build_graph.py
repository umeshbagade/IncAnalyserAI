"""
Knowledge Graph Builder
Parses all lineage.yml files from all 4 reporting domains
into a NetworkX directed graph for traversal and analysis.
"""

import os
import yaml
import networkx as nx

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "vector_db", "Data")


class KnowledgeGraph:
    """
    Directed graph representing data lineage across all reporting domains.
    Nodes are systems/artifacts, edges represent data flow with 'via' metadata.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.domain_edges = {}  # domain -> list of edge tuples

    def build_from_directory(self, data_dir: str = DATA_DIR):
        """Walk through Data/ directory and parse all lineage.yml files."""
        if not os.path.exists(data_dir):
            print(f"Warning: Data directory not found: {data_dir}")
            return

        for root, dirs, files in os.walk(data_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for fname in files:
                if fname == "lineage.yml" or fname == "lineage.yaml":
                    filepath = os.path.join(root, fname)
                    # Determine domain from path
                    rel_path = os.path.relpath(filepath, data_dir)
                    domain = rel_path.split(os.sep)[0].lower()
                    self._parse_lineage_file(filepath, domain)

        print(f"Knowledge Graph built: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges across "
              f"{len(self.domain_edges)} domains")

    def _parse_lineage_file(self, filepath: str, domain: str):
        """Parse a single lineage.yml file and add edges to the graph."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"  Error reading {filepath}: {e}")
            return

        if not data:
            return

        # Handle wrapper keys like "fsb_lineage:" or "edges:"
        edges_data = data
        for key in list(data.keys()):
            if key != "edges" and isinstance(data[key], list):
                edges_data = {key: data[key]}
            if key == "edges":
                edges_data = data
                break

        # Extract edges list
        edges_list = None
        if "edges" in edges_data:
            edges_list = edges_data["edges"]
        else:
            # Maybe the data itself is a list (like old FSB format)
            for val in edges_data.values():
                if isinstance(val, list):
                    edges_list = val
                    break

        if not edges_list:
            print(f"  Warning: No edges found in {filepath}")
            return

        domain_edge_list = []
        for edge in edges_list:
            from_node = edge.get("from", "").strip()
            to_node = edge.get("to", "").strip()
            via = edge.get("via", "").strip()

            if not from_node or not to_node:
                continue

            # Add nodes with domain metadata
            for node in [from_node, to_node]:
                if node not in self.graph:
                    self.graph.add_node(node, domains={domain})
                else:
                    # Add domain to existing node's domains
                    node_domains = self.graph.nodes[node].get("domains", set())
                    node_domains.add(domain)
                    self.graph.nodes[node]["domains"] = node_domains

            # Add edge with metadata
            self.graph.add_edge(
                from_node, to_node,
                via=via,
                domain=domain,
                source_file=os.path.basename(filepath),
            )
            domain_edge_list.append((from_node, to_node, via))

        self.domain_edges[domain] = domain_edge_list
        print(f"  [{domain}] {filepath}: {len(domain_edge_list)} edges")

    def get_node_info(self, node: str) -> dict:
        """Get information about a specific node."""
        if node not in self.graph:
            return {"exists": False, "node": node}

        successors = list(self.graph.successors(node))
        predecessors = list(self.graph.predecessors(node))

        edge_info = []
        for pred in predecessors:
            edge_data = self.graph.get_edge_data(pred, node)
            edge_info.append({
                "from": pred,
                "to": node,
                "via": edge_data.get("via", ""),
                "domain": edge_data.get("domain", ""),
            })
        for succ in successors:
            edge_data = self.graph.get_edge_data(node, succ)
            edge_info.append({
                "from": node,
                "to": succ,
                "via": edge_data.get("via", ""),
                "domain": edge_data.get("domain", ""),
            })

        return {
            "exists": True,
            "node": node,
            "domains": list(self.graph.nodes[node].get("domains", [])),
            "downstream": successors,
            "upstream": predecessors,
            "edges": edge_info,
            "degree": self.graph.degree(node),
        }

    def get_domain_summary(self, domain: str = None) -> dict:
        """Get summary of the graph, optionally filtered by domain."""
        if domain:
            edges = self.domain_edges.get(domain, [])
            nodes = set()
            for f, t, v in edges:
                nodes.add(f)
                nodes.add(t)
            return {
                "domain": domain,
                "nodes": len(nodes),
                "edges": len(edges),
            }
        else:
            domains = {}
            for d, edges in self.domain_edges.items():
                nodes = set()
                for f, t, v in edges:
                    nodes.add(f)
                    nodes.add(t)
                domains[d] = {"nodes": len(nodes), "edges": len(edges)}
            return {
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges(),
                "domains": domains,
            }

    def traverse_upstream(self, node: str, max_depth: int = 5) -> list:
        """
        Traverse upstream (predecessors) from a node up to max_depth.
        Returns list of paths, each path is a list of nodes from leaf to root.
        """
        if node not in self.graph:
            return []
        paths = []
        self._dfs_upstream(node, [], paths, max_depth, set())
        return paths

    def _dfs_upstream(self, node: str, current_path: list, paths: list, max_depth: int, visited: set):
        """DFS helper for upstream traversal."""
        if len(current_path) >= max_depth:
            paths.append(current_path + [node])
            return
        if node in visited:
            paths.append(current_path + [node])
            return

        visited.add(node)
        predecessors = list(self.graph.predecessors(node))
        if not predecessors:
            paths.append(current_path + [node])
        else:
            for pred in predecessors:
                self._dfs_upstream(pred, current_path + [node], paths, max_depth, visited.copy())

    def traverse_downstream(self, node: str, max_depth: int = 5) -> list:
        """
        Traverse downstream (successors) from a node up to max_depth.
        Returns list of paths, each path is a list of nodes from root to leaf.
        """
        if node not in self.graph:
            return []
        paths = []
        self._dfs_downstream(node, [], paths, max_depth, set())
        return paths

    def _dfs_downstream(self, node: str, current_path: list, paths: list, max_depth: int, visited: set):
        """DFS helper for downstream traversal."""
        if len(current_path) >= max_depth:
            paths.append(current_path + [node])
            return
        if node in visited:
            paths.append(current_path + [node])
            return

        visited.add(node)
        successors = list(self.graph.successors(node))
        if not successors:
            paths.append(current_path + [node])
        else:
            for succ in successors:
                self._dfs_downstream(succ, current_path + [node], paths, max_depth, visited.copy())

    def get_stats(self) -> dict:
        """Get statistics about the knowledge graph."""
        domain_counts = {}
        for d, edges in self.domain_edges.items():
            domain_counts[d] = len(edges)
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "domains": list(self.domain_edges.keys()),
            "edges_per_domain": domain_counts,
        }

    def get_domains(self) -> list:
        """Get all domain names in the graph."""
        return list(self.domain_edges.keys())

    def find_path(self, source: str, target: str) -> list:
        """Find the shortest path between two nodes."""
        try:
            path = nx.shortest_path(self.graph, source=source, target=target)
            path_edges = []
            for i in range(len(path) - 1):
                edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                path_edges.append({
                    "from": path[i],
                    "to": path[i + 1],
                    "via": edge_data.get("via", ""),
                    "domain": edge_data.get("domain", ""),
                })
            return path_edges
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_all_paths(self, source: str, target: str, max_paths: int = 5) -> list:
        """Find all simple paths between two nodes."""
        try:
            paths = list(nx.all_simple_paths(self.graph, source=source, target=target, cutoff=10))
            result = []
            for path in paths[:max_paths]:
                path_edges = []
                for i in range(len(path) - 1):
                    edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                    path_edges.append({
                        "from": path[i],
                        "to": path[i + 1],
                        "via": edge_data.get("via", ""),
                        "domain": edge_data.get("domain", ""),
                    })
                result.append(path_edges)
            return result
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []


# Command-line usage
if __name__ == "__main__":
    kg = KnowledgeGraph()
    kg.build_from_directory()
    print("\n" + "=" * 60)
    print("Graph Summary:")
    print(json.dumps(kg.get_domain_summary(), indent=2))
    print("=" * 60)
    import json

