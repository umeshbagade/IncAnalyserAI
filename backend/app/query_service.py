"""
Query Service — Unified Orchestration Layer
=============================================
Takes a user's incident description and queries both:
  1. Vector DB (ChromaDB) — retrieves relevant runbook entries
  2. Knowledge Graph (NetworkX) — for topological/lineage context

Response is structured by investigation flow layer:
  Saturn (Report Layer) -> Data Hub (Data Layer) -> Ingestion (Pipeline Layer)

Each layer contains:
  - symptoms:     The incident symptoms matched to this layer
  - checks:       What to investigate at this layer  
  - common_causes: Likely root causes at this layer
  - next_actions:  Remediation steps to take
"""

import sys
import os
import re
from typing import Optional

# ─── Ensure backend root is on sys.path for knowledge_graph imports ────────
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

# ─── Knowledge Graph imports ────────────────────────────────────────────────
from knowledge_graph.graph_query import GraphQuery  # noqa: E402

# ─── Vector DB imports ──────────────────────────────────────────────────────
_VEC_DB_DIR = os.path.join(_BACKEND_ROOT, "vector_db")
if _VEC_DB_DIR not in sys.path:
    sys.path.insert(0, _VEC_DB_DIR)

import importlib.util
vec_spec = importlib.util.spec_from_file_location(
    "vector_db_query",
    os.path.join(_VEC_DB_DIR, "query_vector_db.py")
)
vec_mod = importlib.util.module_from_spec(vec_spec)
vec_spec.loader.exec_module(vec_mod)
query_vector_db = vec_mod.query_vector_db
query_vector_db_hybrid = vec_mod.query_vector_db_hybrid


# ─── Singleton instances (lazy-loaded) ─────────────────────────────────────

_graph_query: Optional[GraphQuery] = None


def get_graph_query() -> GraphQuery:
    """Get or create the singleton GraphQuery instance."""
    global _graph_query
    if _graph_query is None:
        _graph_query = GraphQuery()
    return _graph_query


# ─── System Mapping ─────────────────────────────────────────────────────────
# Maps the various system names found in vector DB metadata to standard layers

SYSTEM_LAYER_MAP = {
    # Saturn / Report layer
    "saturn": "saturn",
    # Data Hub layer
    "data_hub": "datahub",
    "datahub": "datahub",
    # Ingestion layer
    "upload_ingestion": "ingestion",
    "pe_ingestion": "ingestion",
    "ingestion": "ingestion",
}

LAYER_DISPLAY = {
    "saturn": "Saturn (Report Layer)",
    "datahub": "Data Hub (Data Layer)",
    "ingestion": "Ingestion (Pipeline Layer)",
}

LAYER_ORDER = ["saturn", "datahub", "ingestion"]

# ─── Section Extraction from Raw Chunk Text ────────────────────────────────

SECTION_HEADINGS = [
    r"##?\s*checks?\s*",
    r"##?\s*common\s+causes?\s*",
    r"##?\s*common\s+cause\s*",
    r"##?\s*next\s+actions?\s*",
    r"##?\s*next\s+action\s*",
]


def _strip_metadata_prefix(content: str) -> str:
    """Remove metadata lines like 'Domain: ...', 'System: ...', 'Section: ...' from chunk text."""
    lines = content.split("\n")
    clean_lines = []
    in_metadata = True
    for line in lines:
        # Metadata lines at the start of the chunk
        if in_metadata and re.match(r"^(Domain|System|Section|Symptom|Severity|Incident|id):\s", line):
            continue
        in_metadata = False
        clean_lines.append(line)
    return "\n".join(clean_lines)


def _extract_sections_from_text(text: str) -> dict[str, list[str]]:
    """
    Extract Checks, Common Causes, and Next Actions from raw markdown text.
    Works with both # and ## headings, including front matter.
    Handles the format:
      # H1 Title
      ## Checks
      - item 1
      - item 2
      ## Common Causes
      - cause 1
      - cause 2
    """
    # Remove YAML front matter
    body = text
    if text.strip().startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]

    # Remove metadata prefix lines
    body = _strip_metadata_prefix(body)

    sections = {
        "checks": [],
        "common_causes": [],
        "next_actions": [],
    }

    # Find section boundaries by heading
    heading_pattern = r"^#{1,3}\s+(.+)$"
    lines = body.split("\n")

    current_section = None
    current_content = []

    for line in lines:
        heading_match = re.match(heading_pattern, line.strip())
        if heading_match:
            # Save previous section content
            if current_section and current_content:
                items = _parse_actionable_items("\n".join(current_content))
                if current_section in sections:
                    sections[current_section].extend(items)
                current_content = []

            # Determine new section
            heading_text = heading_match.group(1).strip().lower()
            if heading_text in ("checks", "check"):
                current_section = "checks"
            elif heading_text in ("common causes", "common cause"):
                current_section = "common_causes"
            elif heading_text in ("next actions", "next action"):
                current_section = "next_actions"
            else:
                current_section = None
        else:
            if current_section:
                current_content.append(line)

    # Don't forget the last section
    if current_section and current_content:
        items = _parse_actionable_items("\n".join(current_content))
        if current_section in sections:
            sections[current_section].extend(items)

    return sections


def _parse_actionable_items(text: str) -> list[str]:
    """
    Extract actionable items from section text.
    Captures: bullet points (-), numbered items (1.), cause/action lines.
    """
    items = []
    lines = text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip code blocks and separators
        if stripped.startswith("```") or stripped.startswith("---") or stripped.startswith("___"):
            continue

        # Skip links-only lines
        if re.match(r"^\[.*\]\(.*\)$", stripped):
            continue

        # Bullet points
        if stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:].strip()
            if content and not content.startswith("["):
                items.append(content)
        # Numbered: 1. text or 1) text
        elif re.match(r"^\d+[\.\)]\s", stripped):
            content = re.sub(r"^\d+[\.\)]\s", "", stripped).strip()
            if content:
                items.append(content)
        # "If cause=..." or "If ..." action lines
        elif re.match(r"^If\s+cause=", stripped, re.IGNORECASE):
            items.append(stripped)
        elif re.match(r"^If\s+(resolved|cause)", stripped, re.IGNORECASE):
            items.append(stripped)
        # Lines that start with "**Step" or "**Draft" or similar (markdown bold headings in lists)
        elif stripped.startswith("**") and "**" in stripped[2:]:
            # These are descriptions embedded in the content, skip them for now
            pass
        # Context lines that are direct instructions (not metadata descriptions)
        elif len(stripped) > 15 and not stripped.startswith("#") and not stripped.startswith("`"):
            # Check if it looks like an instruction/statement rather than a description
            skip_patterns = [
                r"^Previous\s+(Step|Step)", r"^Next\s+(Step|Step)", r"^End\s+Point",
                r"^Investigation\s+Order", r"^Root\s+Cause\s+Analysis\s+Path",
                r"^Stage\s+\d", r"^Related\s+Checks", r"^COB\s+Context",
                r"^Saturn\s+Pipeline", r"^Data\s+Quality", r"^Snapshot\s+Approval",
                r"^Common\s+Calculation", r"^Report\s+Status", r"^Common\s+Errors"
            ]
            is_header = any(re.match(p, stripped, re.IGNORECASE) for p in skip_patterns)
            if not is_header:
                items.append(stripped)

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for item in items:
        if item.lower() not in seen:
            seen.add(item.lower())
            deduped.append(item)
    return deduped


def _extract_system_sections(documents: list[str], metadatas: list[dict]) -> dict:
    """
    Aggregate all vector DB results into per-layer (saturn/datahub/ingestion) structure.
    Extracts checks, common causes, and next actions from each document's raw text.
    """
    layers: dict = {}

    for i in range(len(documents)):
        doc = documents[i]
        meta = metadatas[i] if i < len(metadatas) else {}
        raw_system = meta.get("system", "").lower().strip()
        symptom = meta.get("symptom", "")
        domain = meta.get("domain", "")
        source_file = meta.get("source_file", "")

        # Map to standard layer
        layer = SYSTEM_LAYER_MAP.get(raw_system)
        if not layer:
            continue

        if layer not in layers:
            layers[layer] = {
                "symptoms": set(),
                "domains": set(),
                "sources": set(),
                "checks": [],
                "common_causes": [],
                "next_actions": [],
            }

        if symptom:
            layers[layer]["symptoms"].add(symptom)
        if domain:
            layers[layer]["domains"].add(domain)
        if source_file:
            layers[layer]["sources"].add(source_file)

        # Parse the raw document text for structured sections
        parsed = _extract_sections_from_text(doc)
        layers[layer]["checks"].extend(parsed["checks"])
        layers[layer]["common_causes"].extend(parsed["common_causes"])
        layers[layer]["next_actions"].extend(parsed["next_actions"])

    # Deduplicate items per layer
    for layer_name, data in layers.items():
        data["checks"] = list(dict.fromkeys(data["checks"]))
        data["common_causes"] = list(dict.fromkeys(data["common_causes"]))
        data["next_actions"] = list(dict.fromkeys(data["next_actions"]))
        data["symptoms"] = list(data["symptoms"])
        data["domains"] = list(data["domains"])
        data["sources"] = list(data["sources"])

    return layers


def _extract_flow_topo(metadatas: list[dict], documents: list[str]) -> list[dict]:
    """Extract data flow topology from YAML config documents in results."""
    flows = []
    seen_flows = set()

    for i, meta in enumerate(metadatas):
        section = meta.get("section", "")
        if section == "data_flow":
            doc = documents[i] if i < len(documents) else ""
            domain = meta.get("domain", "unknown")
            edges = [l.strip() for l in doc.split("\n") if l.strip().startswith("- Data flows")]
            if edges:
                flow_key = f"lineage_{domain}"
                if flow_key not in seen_flows:
                    seen_flows.add(flow_key)
                    flows.append({"domain": domain, "data_flow_edges": edges})
        elif section == "reporting_flow":
            doc = documents[i] if i < len(documents) else ""
            domain = meta.get("domain", "unknown")
            flow_key = f"flow_{domain}"
            if flow_key not in seen_flows:
                seen_flows.add(flow_key)
                steps = [l.strip() for l in doc.split("\n") if l.strip().startswith("Step ")]
                flows.append({"domain": domain, "pipeline_steps": steps})

    return flows


# ─── Graph Topology ─────────────────────────────────────────────────────────

def _build_graph_topology(graph_result: dict) -> list[dict]:
    """Extract per-node topology from knowledge graph results."""
    topology = []
    for analysis in graph_result.get("impact_analyses", []):
        node = analysis.get("node", "")
        # Extract short system name
        short_name = node.split(".")[-1] if "." in node else node
        topology.append({
            "system": short_name,
            "full_name": node,
            "upstream": analysis.get("upstream_sources", []),
            "downstream": analysis.get("downstream_impacts", []),
        })
    return topology


# ─── Main Analysis Function ─────────────────────────────────────────────────

def analyze_description(description: str, top_k: int = 5) -> dict:
    """
    Full analysis pipeline:
    1. Query Vector DB for relevant runbook entries across all domains
    2. Parse and structure results by investigation layer (saturn -> datahub -> ingestion)
    3. Query Knowledge Graph for system topology context
    4. Return clean, structured response with checks, causes, and actions per layer

    Args:
        description: User-provided incident description
        top_k: Number of vector DB results to retrieve

    Returns:
        dict: Structured response organized by investigation flow layer
    """
    if not description or not description.strip():
        return {
            "description": description or "",
            "analysis_timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "summary": {
                "matched_systems": [],
                "message": "No description provided.",
            },
            "investigation_flow": [],
            "system_topology": [],
        }

    # ── 1. Query Vector DB ──
    try:
        vec_results = query_vector_db_hybrid(description, n_results=max(top_k, 12))
        ids = vec_results.get("ids", [[]])[0]
        distances = vec_results.get("distances", [[]])[0] if vec_results.get("distances") else []
        metadatas = vec_results.get("metadatas", [[]])[0]
        documents = vec_results.get("documents", [[]])[0]

        if not ids:
            vec_results = query_vector_db(description, n_results=max(top_k, 12))
            ids = vec_results.get("ids", [[]])[0]
            distances = vec_results.get("distances", [[]])[0] if vec_results.get("distances") else []
            metadatas = vec_results.get("metadatas", [[]])[0]
            documents = vec_results.get("documents", [[]])[0]
    except Exception as e:
        ids, metadatas, documents = [], [], []

    # ── 2. Structure results by layer ──
    layers = _extract_system_sections(documents, metadatas)
    flow_topology = _extract_flow_topo(metadatas, documents)

    # ── 3. Query Knowledge Graph ──
    gq = get_graph_query()
    try:
        graph_result = gq.analyze_description(description)
        graph_summary = graph_result.get("summary", "")
        matched_nodes = graph_result.get("matched_nodes", [])
        all_upstream = graph_result.get("all_upstream_sources", [])
        all_downstream = graph_result.get("all_downstream_impacts", [])
        system_topology = _build_graph_topology(graph_result)
    except Exception as e:
        graph_summary = ""
        matched_nodes = []
        all_upstream = []
        all_downstream = []
        system_topology = []

    # ── 4. Build ordered investigation flow ──
    investigation_flow = []
    for layer_key in LAYER_ORDER:
        if layer_key in layers:
            data = layers[layer_key]
            investigation_flow.append({
                "layer": LAYER_DISPLAY[layer_key],
                "symptoms": data.get("symptoms", []),
                "checks": data.get("checks", []),
                "common_causes": data.get("common_causes", []),
                "next_actions": data.get("next_actions", []),
            })

    # Mark which systems were matched from knowledge graph
    matched_systems = []
    for node in matched_nodes:
        for alias in ["saturn", "datahub", "data_hub", "ingestion", "upload_ingestion"]:
            if alias in node.lower():
                matched_systems.append(LAYER_DISPLAY.get(
                    SYSTEM_LAYER_MAP.get(alias, alias),
                    alias
                ))
                break

    matched_layers = set(matched_systems)
    for layer_key in LAYER_ORDER:
        if layer_key in layers:
            matched_layers.add(LAYER_DISPLAY[layer_key])

    return {
        "description": description,
        "analysis_timestamp": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "summary": {
            "matched_systems": sorted(matched_layers) if matched_layers else ["No specific systems matched"],
            "system_count": len(layers),
            "knowledge_graph": graph_summary if graph_summary else None,
        },
        "investigation_flow": investigation_flow,
        "system_topology": system_topology[:5] if system_topology else None,  # Top 5 for brevity
        "flow_definitions": flow_topology if flow_topology else None,
    }


# ─── Convenience: get summary stats ─────────────────────────────────────────

def get_knowledge_base_stats() -> dict:
    """Get statistics about both the knowledge graph and vector DB."""
    gq = get_graph_query()
    try:
        graph_stats = gq.get_graph_stats()
    except Exception as e:
        graph_stats = {"error": str(e)}

    return {
        "knowledge_graph": graph_stats,
    }


if __name__ == "__main__":
    import json
    test_desc = "EOD batch job failed - feed load timeout"
    print(f"Analyzing: {test_desc}\n")
    result = analyze_description(test_desc)
    print(json.dumps(result, indent=2))

