"""
Vector DB Query Interface - Multi-Domain IncAnalyserAI Knowledge Base
Queries the ChromaDB vector store with semantic search,
supporting domain filtering and hybrid results.
"""

import os
import sys
import argparse
import chromadb
from sentence_transformers import SentenceTransformer

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_STORE_DIR = os.path.join(BASE_DIR, "vector_store")
COLLECTION_NAME = "incanalyser_knowledge"

# Embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Initialize
print("Loading embedding model...", file=sys.stderr)
embedder = SentenceTransformer(EMBEDDING_MODEL)

print("Connecting to vector store...", file=sys.stderr)
client = chromadb.PersistentClient(path=VECTOR_STORE_DIR)

try:
    collection = client.get_collection(COLLECTION_NAME)
except Exception as e:
    print(f"Error: Could not find collection '{COLLECTION_NAME}'.", file=sys.stderr)
    print("Run 'python3 create_vector_db.py' first to build the index.", file=sys.stderr)
    sys.exit(1)


def query_vector_db(query_text, n_results=5, system_filter=None, domain_filter=None):
    """Search the vector DB and return results with optional filters."""
    query_embedding = embedder.encode([query_text]).tolist()

    # Build where filter
    where_filter = {}
    if system_filter and domain_filter:
        where_filter = {"$and": [{"system": system_filter}, {"domain": domain_filter}]}
    elif system_filter:
        where_filter = {"system": system_filter}
    elif domain_filter:
        where_filter = {"domain": domain_filter}

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where_filter if where_filter else None,
    )

    return results


def query_vector_db_hybrid(query_text, n_results=5, domain_filter=None):
    """
    Hybrid query: runs separate queries for 'md' and 'yml' file types,
    then merges results for better coverage.
    """
    query_embedding = embedder.encode([query_text]).tolist()

    where_md = {"file_type": "md"}
    where_yml = {"file_type": "yml"}

    if domain_filter:
        where_md["domain"] = domain_filter
        where_yml["domain"] = domain_filter

    n_per_type = max(1, n_results // 2)

    # Query for MD runbook chunks
    md_results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_per_type,
        where=where_md,
    )

    # Query for YAML config chunks
    yml_results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_per_type,
        where=where_yml,
    )

    # Merge results (interleave MD and YML)
    merged_ids = []
    merged_distances = []
    merged_metadatas = []
    merged_documents = []

    max_len = max(
        len(md_results.get("ids", [[]])[0]),
        len(yml_results.get("ids", [[]])[0]),
    )

    for i in range(max_len):
        if i < len(md_results.get("ids", [[]])[0]):
            idx = i
            merged_ids.append(md_results["ids"][0][idx])
            merged_distances.append(md_results["distances"][0][idx] if md_results.get("distances") else 0)
            merged_metadatas.append(md_results["metadatas"][0][idx])
            merged_documents.append(md_results["documents"][0][idx])
        if i < len(yml_results.get("ids", [[]])[0]):
            idx = i
            merged_ids.append(yml_results["ids"][0][idx])
            merged_distances.append(yml_results["distances"][0][idx] if yml_results.get("distances") else 0)
            merged_metadatas.append(yml_results["metadatas"][0][idx])
            merged_documents.append(yml_results["documents"][0][idx])

    # Trim to requested number
    merged_ids = merged_ids[:n_results]
    merged_distances = merged_distances[:n_results]
    merged_metadatas = merged_metadatas[:n_results]
    merged_documents = merged_documents[:n_results]

    return {
        "ids": [merged_ids],
        "distances": [merged_distances] if merged_distances else None,
        "metadatas": [merged_metadatas],
        "documents": [merged_documents],
    }


def print_results(results, query_text):
    """Pretty-print query results."""
    if not results or not results["ids"] or len(results["ids"][0]) == 0:
        print("\nNo results found.")
        return

    print("\n" + "=" * 70)
    print(f"Query: {query_text}")
    print(f"Results: {len(results['ids'][0])}")
    print("=" * 70)

    for i in range(len(results["ids"][0])):
        metadata = results["metadatas"][0][i]
        document = results["documents"][0][i]
        distance = results["distances"][0][i] if results.get("distances") else None

        print(f"\n--- Result {i + 1} ---")
        print(f"  Source File : {metadata.get('source_file', '?')}")
        print(f"  Domain      : {metadata.get('domain', '?')}")
        print(f"  System      : {metadata.get('system', '?')}")
        print(f"  Section     : {metadata.get('section', '?')}")
        print(f"  Incident    : {metadata.get('incident_id', 'N/A')}")
        if distance is not None:
            print(f"  Similarity  : {1 - distance:.4f}")
        print(f"  Symptom     : {metadata.get('symptom', 'N/A')}")
        print(f"  Severity    : {metadata.get('severity', 'N/A')}")
        print(f"  {'─' * 60}")
        print(f"{document}")
        print(f"  {'─' * 60}")


def show_stats():
    """Display collection statistics."""
    count = collection.count()
    print("\n" + "=" * 50)
    print("IncAnalyserAI Knowledge Vector DB - Statistics")
    print("=" * 50)
    print(f"  Collection      : {COLLECTION_NAME}")
    print(f"  Total Documents : {count}")
    print(f"  Embedding Model : {EMBEDDING_MODEL}")
    print(f"  Store Location  : {VECTOR_STORE_DIR}")
    print()

    # Show domain breakdown
    all_data = collection.get()
    domain_counts = {}
    file_counts = {}
    for meta in all_data["metadatas"]:
        d = meta.get("domain", "unknown")
        domain_counts[d] = domain_counts.get(d, 0) + 1
        fname = meta.get("source_file", "unknown")
        file_counts[fname] = file_counts.get(fname, 0) + 1

    print("  Domains indexed:")
    for domain, count in sorted(domain_counts.items()):
        print(f"    - {domain}: {count} chunk(s)")
    print()
    print("  Files indexed:")
    for fname, count in sorted(file_counts.items()):
        print(f"    - {fname}: {count} chunk(s)")
    print()


def interactive_mode():
    """Run interactive query loop."""
    print("\n" + "=" * 50)
    print("IncAnalyserAI Knowledge Vector DB - Interactive Mode")
    print("Type 'exit', 'quit', or press Ctrl+C to stop.")
    print("Type ':stats' to show collection statistics.")
    print("Type ':hybrid <query>' for runbook + config blended results.")
    print("=" * 50)

    while True:
        try:
            raw = input("\n🔍 Query: ").strip()
            if not raw:
                continue
            if raw.lower() in ("exit", "quit"):
                break
            if raw == ":stats":
                show_stats()
                continue
            if raw.startswith(":hybrid "):
                query = raw[8:].strip()
                results = query_vector_db_hybrid(query)
            else:
                results = query_vector_db(raw)
            print_results(results, raw)

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Query the IncAnalyserAI Multi-Domain Knowledge Vector DB"
    )
    parser.add_argument("query", nargs="?", default=None,
                        help="Search query text")
    parser.add_argument("-n", "--n-results", type=int, default=5,
                        help="Number of results to return (default: 5)")
    parser.add_argument("--system", type=str, default=None,
                        help="Filter by system name (e.g., data_hub, saturn)")
    parser.add_argument("--domain", type=str, default=None,
                        help="Filter by domain (e.g., derivatives, fsb, nsfr, stratplan)")
    parser.add_argument("--hybrid", action="store_true",
                        help="Use hybrid mode (interleave MD + YML results)")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Run in interactive mode")
    parser.add_argument("--stats", action="store_true",
                        help="Show collection statistics and exit")

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.interactive:
        interactive_mode()
        return

    if args.query:
        if args.hybrid:
            results = query_vector_db_hybrid(args.query, args.n_results, args.domain)
        else:
            results = query_vector_db(args.query, args.n_results, args.system, args.domain)
        print_results(results, args.query)
        return

    # No arguments - show help
    parser.print_help()


if __name__ == "__main__":
    main()

