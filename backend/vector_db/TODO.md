# IncAnalyserAI - Knowledge Base Pipeline Progress

## ✅ Completed

### Phase 1: Standardize & Normalize Data Files
- [x] 1. Normalize `derivatives_reporting.yml` — `artefact` → `artifact`
- [x] 2. Fix `fsb_bsm_reporting.yml` — Removed `reporting_flow:` wrapper, flattened structure
- [x] 3. Fix `nsfr_reporting.yml` — Corrected `flow_id` to `nsfr_reporting`, proper NSFR content
- [x] 4. Normalize `FSB/lineage.yml` — Removed `fsb_lineage:` root key wrapper
- [x] 5. Normalize `NSFR/lineage.yml` — Fixed `hive.ingest` → `hive.ingestion`, `upload.ingest` → `upload_ingestion`
- [x] 6. Normalize `Stratplan/lineage.yml` — Fixed `upload_ingest` → `upload_ingestion`

### Phase 2: Rebuilt Vector DB Creator
- [x] 7. Rewrote `create_vector_db.py` — Recursive, multi-domain (4 domains), handles all YAML variants
- [x] 8. Rewrote `query_vector_db.py` — Supports domain filtering, hybrid query mode

### Phase 3: Built Graph DB Module
- [x] 9. Created `backend/knowledge_graph/__init__.py`
- [x] 10. Created `backend/knowledge_graph/build_graph.py` — Parses all lineage YAMLs into NetworkX graph
- [x] 11. Created `backend/knowledge_graph/graph_query.py` — Traversal, path finding, impact analysis

### Phase 4: Wired API Endpoints
- [x] 12. Updated `main.py` — Added `/api/analyze`, `/api/knowledge/graph/stats`, `/api/knowledge/graph/nodes`, `/api/knowledge/graph/edges`, `/api/knowledge/graph/impact/{node}`

## Testing Results

### Vector DB
- **Before:** 13 chunks from 5 files (single domain)
- **After:** 112 chunks from 53 files across 4 domains
- Domains: derivatives (13), fsb (19), nsfr (40), stratplan (40)

### Knowledge Graph
- **Nodes:** 19 across 4 domains
- **Edges:** 15 across 4 domains
- **Domains:** derivatives, fsb, nsfr, stratplan

## Next Steps (When LLM/Agents Are Added)
- [ ] Create `backend/llm_prompt/prompt_builder.py` — Combine user description + graph context + vector DB results
- [ ] Create `backend/llm_prompt/prompt_templates.py` — RCA, next actions, causal chain templates
- [ ] Create `backend/llm_prompt/llm_client.py` — Interface to call OpenAI/Anthropic/Ollama
- [ ] Wire LLM prompt into `/api/analyze` endpoint

