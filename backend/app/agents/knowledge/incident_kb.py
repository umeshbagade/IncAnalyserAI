"""
Incident Knowledge Base — the REAL knowledge layer backing the MCP tools.

Instead of returning synthetic stub data, this module loads the curated
per-layer runbooks that live under::

    backend/vector_db/Data/<domain>/<INC_x>/{saturn,data_hub,upload_ingestion}.md

Each markdown file describes ONE layer of ONE incident and carries:
  - frontmatter: id, system, symptom, severity
  - "## Checks"        — what a specialist should verify at this layer
  - "## Common Causes" — candidate root causes (used for RCA)
  - "## Next Actions"  — where to escalate / how to remediate

The investigation always drills the reporting pipeline in reverse — from the
place the symptom surfaces (Saturn report) down to the source:

    saturn -> datahub -> ingestion   (ingestion = source = root-cause layer)

so the agents can walk the exact layer chain the runbooks describe, detect the
discrepancy at every layer, and pin the root cause at the deepest (endpoint)
layer, exactly like the runbooks' "Next Actions" instruct.

The data on disk is intentionally messy (mixed YAML/inline frontmatter, `#`
vs `##` headers, a few empty files, folders whose names don't match the
incident id). The parser below is deliberately tolerant of all of that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


# ---------------------------------------------------------------------------
# Layout / canonical layer model
# ---------------------------------------------------------------------------

# backend/app/agents/knowledge/incident_kb.py  -> parents[3] == backend/
_DATA_ROOT = Path(__file__).resolve().parents[3] / "vector_db" / "Data"

# markdown file stem -> canonical layer id used by the agent topology
_FILE_TO_LAYER: dict[str, str] = {
    "saturn": "saturn",
    "data_hub": "datahub",
    "upload_ingestion": "ingestion",
}

# Investigation drills from the reported symptom down to the source.
INVESTIGATION_ORDER: list[str] = ["saturn", "datahub", "ingestion"]

# Human-friendly labels for the UI / summaries.
LAYER_LABELS: dict[str, str] = {
    "saturn": "Saturn",
    "datahub": "Data Hub",
    "ingestion": "Upload Ingestion",
}

_SECTION_ALIASES: dict[str, str] = {
    "checks": "checks",
    "check": "checks",
    "common causes": "common_causes",
    "common cause": "common_causes",
    "next actions": "next_actions",
    "next action": "next_actions",
    "actions": "next_actions",
}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "to", "is", "are",
    "was", "were", "be", "been", "with", "at", "by", "from", "that", "this",
    "not", "no", "some", "few", "data", "report", "reports", "reporting",
    "issue", "failed", "failure", "error", "check", "checks", "system",
}


# ---------------------------------------------------------------------------
# Parsed records
# ---------------------------------------------------------------------------

@dataclass
class LayerDoc:
    """One layer runbook (one .md file) for one incident."""
    layer: str                      # canonical: saturn | datahub | ingestion
    file_system: str                # frontmatter `system` value (raw, may be noisy)
    incident_key: str               # frontmatter `id`
    symptom: str
    severity: str
    checks: list[str] = field(default_factory=list)
    common_causes: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    raw: str = ""


@dataclass
class IncidentCase:
    """All layers of a single incident folder, keyed by canonical layer."""
    domain: str                     # Derivatives | FSB | NSFR | Stratplan
    folder: str                     # INC_1 ...
    key: str                        # best incident id found across layers
    symptom: str                    # representative symptom
    severity: str
    layers: dict[str, LayerDoc] = field(default_factory=dict)

    @property
    def ordered_layers(self) -> list[str]:
        """Canonical layers this case actually has, in investigation order."""
        return [l for l in INVESTIGATION_ORDER if l in self.layers]

    @property
    def root_cause_layer(self) -> str | None:
        """Deepest available layer — the source / endpoint = root cause."""
        ordered = self.ordered_layers
        return ordered[-1] if ordered else None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _extract_meta(text: str, key: str) -> str:
    """Pull a frontmatter-style `key: value` regardless of YAML fences."""
    m = re.search(rf'(?im)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$', text)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def _parse_sections(text: str) -> dict[str, list[str]]:
    """Split markdown into Checks / Common Causes / Next Actions list items."""
    result: dict[str, list[str]] = {"checks": [], "common_causes": [], "next_actions": []}
    current: str | None = None

    for line in text.splitlines():
        header = re.match(r'^\s*#{1,4}\s*(.+?)\s*$', line)
        if header:
            title = re.sub(r'[^a-z ]', '', header.group(1).lower()).strip()
            current = _SECTION_ALIASES.get(title)
            continue
        if current is None:
            continue
        item = line.strip()
        if not item:
            continue
        marker = re.match(r'^(?:[-*•]|\d+[.)])\s+(.*)$', item)
        if marker:
            result[current].append(marker.group(1).strip())
        elif result[current]:
            # wrapped continuation of the previous bullet
            result[current][-1] = f"{result[current][-1]} {item}".strip()
    return result


def _parse_layer_doc(path: Path, layer: str) -> LayerDoc | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.strip():
        return None  # empty file (e.g. Derivatives/INC_4/saturn.md)

    sections = _parse_sections(text)
    return LayerDoc(
        layer=layer,
        file_system=_extract_meta(text, "system"),
        incident_key=_extract_meta(text, "id"),
        symptom=_extract_meta(text, "symptom"),
        severity=_extract_meta(text, "severity") or "high",
        checks=sections["checks"],
        common_causes=sections["common_causes"],
        next_actions=sections["next_actions"],
        raw=text,
    )


@lru_cache(maxsize=1)
def _load_cases() -> list[IncidentCase]:
    cases: list[IncidentCase] = []
    if not _DATA_ROOT.is_dir():
        return cases

    for domain_dir in sorted(_DATA_ROOT.iterdir()):
        if not domain_dir.is_dir():
            continue
        for inc_dir in sorted(domain_dir.iterdir()):
            if not inc_dir.is_dir() or not inc_dir.name.upper().startswith("INC"):
                continue

            layers: dict[str, LayerDoc] = {}
            for stem, canonical in _FILE_TO_LAYER.items():
                doc = _parse_layer_doc(inc_dir / f"{stem}.md", canonical)
                if doc is not None:
                    layers[canonical] = doc
            if not layers:
                continue

            # Prefer the id/symptom from the shallowest available layer.
            rep = next((layers[l] for l in INVESTIGATION_ORDER if l in layers), None)
            key = next((d.incident_key for d in layers.values() if d.incident_key), "") \
                or f"{domain_dir.name}/{inc_dir.name}"
            symptom = next((d.symptom for d in layers.values() if d.symptom), "")

            cases.append(
                IncidentCase(
                    domain=domain_dir.name,
                    folder=inc_dir.name,
                    key=key,
                    symptom=symptom or (rep.symptom if rep else ""),
                    severity=(rep.severity if rep else "high"),
                    layers=layers,
                )
            )
    return cases


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def all_cases() -> list[IncidentCase]:
    return list(_load_cases())


def _tokens(text: str) -> set[str]:
    return {
        t for t in re.findall(r'[a-z0-9]+', text.lower())
        if t not in _STOPWORDS and len(t) > 1
    }


def _case_match_text(case: IncidentCase) -> str:
    parts = [case.key, case.symptom]
    for doc in case.layers.values():
        parts.append(doc.symptom)
    return " ".join(p for p in parts if p)


def match_case(title: str, description: str, flow_id: str = "") -> IncidentCase | None:
    """
    Find the incident case that best matches a free-text incident report.

    Scored by meaningful-token overlap between the report and each case's
    id + symptoms, with a small bonus when the incident id appears verbatim
    or the reporting domain matches. Returns None when nothing is close.
    """
    report_tokens = _tokens(f"{title} {description}")
    report_text = f"{title} {description}".lower()
    if not report_tokens:
        return None

    best: IncidentCase | None = None
    best_score = 0.0
    for case in _load_cases():
        case_tokens = _tokens(_case_match_text(case))
        overlap = report_tokens & case_tokens
        score = float(len(overlap))
        # Distinctive-id bonus: e.g. "d60", "coefficient", "duplicate".
        key_norm = re.sub(r'[^a-z0-9]+', ' ', case.key.lower())
        if key_norm and key_norm.strip() and key_norm.strip() in report_text:
            score += 3.0
        if flow_id and flow_id.lower() in case.domain.lower():
            score += 1.0
        if score > best_score:
            best_score, best = score, case

    return best if best_score >= 2.0 else None


def find_similar(case: IncidentCase, k: int = 3) -> list[IncidentCase]:
    """Other incident cases whose symptoms share vocabulary with `case`."""
    base = _tokens(_case_match_text(case))
    scored: list[tuple[float, IncidentCase]] = []
    for other in _load_cases():
        if other is case or (other.key == case.key and other.folder == case.folder):
            continue
        overlap = base & _tokens(_case_match_text(other))
        if overlap:
            scored.append((float(len(overlap)), other))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]


def get_layer_doc(case: IncidentCase, layer: str) -> LayerDoc | None:
    return case.layers.get(layer)
