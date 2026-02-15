#!/usr/bin/env python3
"""
scripts/seed_index.py — Bootstrap the design index from a directory of decks.

Usage:
    python scripts/seed_index.py ./decks/

TODO (Claude Code Phase 2):
    - Batch ingestion with progress bar
    - Parallel semantic enrichment via Index Curator
    - Batch embedding computation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ingest_deck import ingest_sdsl
from src.index.store import DesignIndexStore


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_index.py <directory>")
        sys.exit(1)

    deck_dir = Path(sys.argv[1])
    if not deck_dir.is_dir():
        print(f"ERROR: {deck_dir} is not a directory")
        sys.exit(1)

    store = DesignIndexStore("design_index.db")
    store.initialize()

    files = sorted(deck_dir.glob("**/*.sdsl"))
    print(f"Seeding index from {len(files)} .sdsl files in {deck_dir}\n")

    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {f.name}")
        try:
            ingest_sdsl(str(f), store)
        except Exception as e:
            print(f"  ERROR: {e}")

    stats = store.get_stats()
    print(f"\nDone. Index stats: {stats}")
    store.close()


if __name__ == "__main__":
    main()
