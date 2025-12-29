#!/usr/bin/env python3
"""
Manticore Search Indexer

Loads parsed trademark data into Manticore Search for phonetic search testing.

Usage:
    python index.py --input /path/to/marks.json
    python index.py --limit 1000  # Load limited records for testing
"""

import argparse
import json
import requests
from pathlib import Path

import yaml


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


def create_table(manticore_url: str):
    """Create the trademarks table if it doesn't exist."""
    query = """CREATE TABLE IF NOT EXISTS trademarks (
        serial_number text,
        registration_number text,
        mark_text text,
        goods_services text,
        owner_name text,
        status_code text,
        status text
    ) morphology='soundex, metaphone'"""

    response = requests.post(f"{manticore_url}/cli", data=query, timeout=30)
    print(f"Create table: {response.text.strip()}")


def load_records(manticore_url: str, records: list, batch_size: int = 100):
    """Load records into Manticore in batches."""
    total = len(records)
    loaded = 0
    errors = 0

    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]

        # Build bulk insert
        docs = []
        for r in batch:
            docs.append({
                "insert": {
                    "index": "trademarks",
                    "doc": {
                        "serial_number": r.get("serial_number", ""),
                        "registration_number": r.get("registration_number") or "",
                        "mark_text": r.get("mark_text", ""),
                        "goods_services": r.get("goods_services", ""),
                        "owner_name": r.get("owner_name", ""),
                        "status_code": r.get("status_code", ""),
                        "status": r.get("status", "")
                    }
                }
            })

        # Send as NDJSON
        ndjson = "\n".join(json.dumps(d) for d in docs)

        try:
            response = requests.post(
                f"{manticore_url}/bulk",
                data=ndjson,
                headers={"Content-Type": "application/x-ndjson"},
                timeout=60
            )

            if response.status_code == 200:
                loaded += len(batch)
            else:
                errors += len(batch)
                print(f"  Batch error: {response.text[:200]}")

        except Exception as e:
            errors += len(batch)
            print(f"  Exception: {e}")

        # Progress
        if (i + batch_size) % 1000 == 0 or i + batch_size >= total:
            print(f"  Loaded {min(i + batch_size, total):,}/{total:,} records")

    return loaded, errors


def search_test(manticore_url: str, query: str):
    """Run a test search."""
    sql = f"SELECT serial_number, mark_text, status FROM trademarks WHERE MATCH('{query}') LIMIT 10"
    response = requests.post(f"{manticore_url}/cli", data=sql, timeout=30)
    return response.text


def main():
    parser = argparse.ArgumentParser(description="Load trademark data into Manticore")
    parser.add_argument("--input", type=Path, help="Input JSON file")
    parser.add_argument("--manticore", default="http://127.0.0.1:9308", help="Manticore URL")
    parser.add_argument("--limit", type=int, help="Limit records to load")
    parser.add_argument("--test", action="store_true", help="Run test searches after loading")

    args = parser.parse_args()
    config = load_config()

    # Find latest release
    if args.input:
        input_path = args.input
    else:
        releases_path = Path(config.get("data", {}).get("output_path", "/tmp/ilegalflow/releases"))
        releases = sorted(releases_path.glob("*/marks.json"), reverse=True)
        if not releases:
            print(f"No marks.json found in {releases_path}")
            return
        input_path = releases[0]

    print(f"Loading from: {input_path}")

    # Create table
    create_table(args.manticore)

    # Load JSON
    with open(input_path) as f:
        records = json.load(f)

    if args.limit:
        records = records[:args.limit]

    print(f"Loading {len(records):,} records into Manticore...")
    loaded, errors = load_records(args.manticore, records)
    print(f"\nDone! Loaded {loaded:,} records, {errors:,} errors")

    # Test searches
    if args.test or True:  # Always run tests
        print("\n--- Test Searches ---")

        # Exact match
        print("\n1. Exact match 'JUICY JUICE':")
        print(search_test(args.manticore, "JUICY JUICE"))

        # Phonetic match (sounds like)
        print("\n2. Phonetic match 'JOOSY JOOS' (should find JUICY JUICE):")
        print(search_test(args.manticore, "JOOSY JOOS"))

        # Another phonetic test
        print("\n3. Phonetic match 'HILTIN' (should find HILTON):")
        print(search_test(args.manticore, "HILTIN"))


if __name__ == "__main__":
    main()
