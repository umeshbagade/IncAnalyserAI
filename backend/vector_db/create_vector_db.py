"""
Vector DB Creator for ALL Reporting Domains
Recursively parses .md runbooks and .yml configs from all 4 domains
(Derivatives, FSB, NSFR, Stratplan) and stores them in ChromaDB
"""

import os
import json
import yaml
import chromadb
from sentence_transformers import SentenceTransformer

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data")
VECTOR_STORE_DIR = os.path.join(BASE_DIR, "vector_store")

# Ensure vector store directory exists
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

# Embedding model (runs locally, no API key needed)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Initialize embedding model
print("Loading embedding model: " + EMBEDDING_MODEL + "...")
embedder = SentenceTransformer(EMBEDDING_MODEL)
print("Embedding model loaded.")


def get_domain_from_path(filepath, base_dir):
    """Extract domain name from the file path relative to DATA_DIR."""
    rel_path = os.path.relpath(filepath, base_dir)
    parts = rel_path.split(os.sep)
    # First directory under Data/ is the domain (Derivatives, FSB, NSFR, Stratplan)
    if parts:
        return parts[0].lower()
    return "unknown"


def get_incident_id_from_path(filepath, base_dir):
    """Extract incident ID (e.g. INC_1) from path if present."""
    rel_path = os.path.relpath(filepath, base_dir)
    parts = rel_path.split(os.sep)
    for part in parts:
        if part.startswith("INC_"):
            return part
    return ""


def parse_markdown_sections(filepath, system_name, domain, incident_id):
    """Parse .md file into chunks by sections (Checks, Common causes, Next actions)."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = []
    # Get YAML front matter if present
    front_matter = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                front_matter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                front_matter = {}
            body = parts[2]

    # Extract front matter fields
    symptom = front_matter.get("symptom", "")
    severity = front_matter.get("severity", "")
    file_id = front_matter.get("id", "")

    # Also support inline heading-based id/system/symptom
    if not system_name:
        system_name = front_matter.get("system", os.path.basename(filepath).replace(".md", ""))

    # Split by # headings (markdown H1 sections like # Checks, # Common causes, etc.)
    sections = body.split("\n# ")
    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().split("\n")
        section_title = lines[0].strip().replace("# ", "")
        section_body = "\n".join(lines[1:]).strip()

        if not section_body:
            continue

        chunk_text = (
            "Domain: " + domain + "\n"
            + "System: " + system_name + "\n"
            + "Section: " + section_title + "\n"
        )
        if symptom:
            chunk_text += "Symptom: " + symptom + "\n"
        if severity:
            chunk_text += "Severity: " + severity + "\n"
        if incident_id:
            chunk_text += "Incident: " + incident_id + "\n"
        chunk_text += "\n" + section_body

        metadata = {
            "source_file": os.path.basename(filepath),
            "domain": domain,
            "system": system_name,
            "incident_id": incident_id,
            "file_type": "md",
            "section": section_title,
            "symptom": symptom,
            "severity": severity,
            "id": file_id,
        }
        chunks.append((chunk_text, metadata))

    return chunks


def parse_yml_file(filepath, domain, incident_id):
    """Parse .yml file into structured text chunks."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        print("Error parsing " + filepath + ": " + str(e))
        return []

    filename = os.path.basename(filepath)
    system_name = filename.replace(".yml", "").replace(".yaml", "")

    # Handle FSB-style wrapper: data may be under a root key like "fsb_lineage" or "reporting_flow"
    root_data = data
    for key in list(data.keys()):
        if key not in ("edges", "steps", "flow_id", "description", "sla"):
            # Could be a wrapper like fsb_lineage or reporting_flow
            if isinstance(data[key], dict) or isinstance(data[key], list):
                root_data = data[key]
                break

    chunks = []
    metadata_base = {
        "source_file": filename,
        "domain": domain,
        "incident_id": incident_id,
        "file_type": "yml",
    }

    if isinstance(root_data, dict) and "edges" in root_data:  # lineage.yml
        chunk_text = "Data Lineage (Domain: " + domain + "):\n"
        for edge in root_data["edges"]:
            from_node = edge.get("from", "?")
            to_node = edge.get("to", "?")
            via = edge.get("via", "?")
            chunk_text += "- Data flows FROM " + str(from_node) + " TO " + str(to_node) + " VIA " + str(via) + "\n"

        chunks.append((
            chunk_text,
            {**metadata_base, "system": "lineage", "section": "data_flow"},
        ))
    elif isinstance(root_data, list):  # lineage as a list (like FSB originally was)
        chunk_text = "Data Lineage (Domain: " + domain + "):\n"
        for edge in root_data:
            from_node = edge.get("from", "?")
            to_node = edge.get("to", "?")
            via = edge.get("via", "?")
            chunk_text += "- Data flows FROM " + str(from_node) + " TO " + str(to_node) + " VIA " + str(via) + "\n"

        chunks.append((
            chunk_text,
            {**metadata_base, "system": "lineage", "section": "data_flow"},
        ))

    if isinstance(root_data, dict) and "steps" in root_data:  # reporting.yml
        flow_id = root_data.get("flow_id", "unknown")
        description = root_data.get("description", "")
        chunk_text = "Reporting Flow (Domain: " + domain + "): " + str(flow_id) + "\nDescription: " + str(description) + "\n\nSteps:\n"
        for step in root_data["steps"]:
            # Support both 'artefact' and 'artifact' keys
            artifact = step.get("artifact") or step.get("artefact", "?")
            chunk_text += (
                "Step " + str(step.get('step', '?')) + ": " + str(step.get('system', '?')) + " - "
                + str(step.get('action', '?')) + "\n"
                + "  Success Signal: " + str(step.get('success_signal', '?')) + "\n"
                + "  Artifact: " + str(artifact) + "\n\n"
            )

        chunks.append((
            chunk_text,
            {**metadata_base, "system": flow_id, "section": "reporting_flow"},
        ))

    # Also add raw YAML as a document for direct reference
    chunks.append((
        "Configuration file: " + filename + " (Domain: " + domain + ")\n\n```yaml\n" + content + "\n```",
        {**metadata_base, "system": "config", "section": "raw_config"},
    ))

    return chunks


def process_directory(dirpath, domain):
    """Recursively process all .md and .yml files in a directory tree."""
    chunks = []
    file_count = 0

    for root, dirs, files in os.walk(dirpath):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for fname in sorted(files):
            if fname.startswith('.'):
                continue

            filepath = os.path.join(root, fname)
            incident_id = get_incident_id_from_path(filepath, DATA_DIR)

            if fname.endswith(".md"):
                system_name = fname.replace(".md", "")
                print("\n[MD] Processing: " + os.path.relpath(filepath, DATA_DIR) + " (system: " + system_name + ")")
                md_chunks = parse_markdown_sections(filepath, system_name, domain, incident_id)
                print("   -> " + str(len(md_chunks)) + " sections extracted")
                chunks.extend(md_chunks)
                file_count += 1

            elif fname.endswith((".yml", ".yaml")):
                print("\n[YML] Processing: " + os.path.relpath(filepath, DATA_DIR))
                yml_chunks = parse_yml_file(filepath, domain, incident_id)
                print("   -> " + str(len(yml_chunks)) + " chunks extracted")
                chunks.extend(yml_chunks)
                file_count += 1

    return chunks, file_count


def main():
    print("=" * 60)
    print("IncAnalyserAI - Multi-Domain Vector DB Creator")
    print("=" * 60)

    # Collect all documents from all domains
    all_chunks = []
    total_file_count = 0

    # Process each domain directory
    for domain_dir in sorted(os.listdir(DATA_DIR)):
        domain_path = os.path.join(DATA_DIR, domain_dir)
        if not os.path.isdir(domain_path) or domain_dir.startswith('.'):
            continue

        domain = domain_dir.lower()
        print("\n" + "=" * 50)
        print("Domain: " + domain)
        print("=" * 50)

        chunks, file_count = process_directory(domain_path, domain)
        all_chunks.extend(chunks)
        total_file_count += file_count
        print("\n   Domain total: " + str(len(chunks)) + " chunks from " + str(file_count) + " files")

    print("\n" + "=" * 60)
    print("Total files processed across all domains: " + str(total_file_count))
    print("Total chunks extracted: " + str(len(all_chunks)))
    print("=" * 60)

    if not all_chunks:
        print("No chunks found. Nothing to store.")
        return

    # Initialize ChromaDB
    print("\nInitializing ChromaDB...")
    client = chromadb.PersistentClient(path=VECTOR_STORE_DIR)

    # Delete existing collection if present
    try:
        client.delete_collection("incanalyser_knowledge")
        print("   Removed existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        name="incanalyser_knowledge",
        metadata={"hnsw:space": "cosine"},
    )

    # Generate embeddings and add to collection
    print("\nGenerating embeddings for " + str(len(all_chunks)) + " chunks...")
    texts = [chunk[0] for chunk in all_chunks]
    metadatas = [chunk[1] for chunk in all_chunks]
    ids = ["chunk_" + str(i).zfill(5) for i in range(len(all_chunks))]

    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()

    print("\nStoring in ChromaDB...")
    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    print("\nVector DB created successfully!")
    print("   Collection: incanalyser_knowledge")
    print("   Total documents: " + str(collection.count()))
    print("   Storage path: " + VECTOR_STORE_DIR)

    # Save metadata summary
    # Count chunks per domain
    domain_counts = {}
    for _, m in all_chunks:
        d = m.get("domain", "unknown")
        domain_counts[d] = domain_counts.get(d, 0) + 1

    summary = {
        "total_chunks": len(all_chunks),
        "total_files": total_file_count,
        "domains": domain_counts,
        "embedding_model": EMBEDDING_MODEL,
        "collection": "incanalyser_knowledge",
        "files_processed": [
            {
                "file": m["source_file"],
                "domain": m.get("domain", "?"),
                "system": m.get("system", "?"),
                "type": m["file_type"],
                "incident": m.get("incident_id", ""),
            }
            for _, m in all_chunks
        ],
    }
    with open(os.path.join(VECTOR_STORE_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("   Summary saved to: " + os.path.join(VECTOR_STORE_DIR, "summary.json"))


if __name__ == "__main__":
    main()

