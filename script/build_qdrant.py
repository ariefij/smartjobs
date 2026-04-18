from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartjobs.chunking import build_chunk_documents
from smartjobs.config import get_settings
from smartjobs.qdrant_store import QdrantJobStore
from smartjobs.sqlite_store import SQLiteJobStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Buat preview chunk atau indeks record ke Qdrant.")
    parser.add_argument("--sqlite-path", type=Path, default=None)
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--preview-output", type=Path, default=None)
    args = parser.parse_args()

    settings = get_settings()
    sqlite_path = args.sqlite_path or ROOT / settings.sqlite_path
    preview_output = args.preview_output or ROOT / settings.chunks_preview_path
    preview_output.parent.mkdir(parents=True, exist_ok=True)

    records = SQLiteJobStore(sqlite_path).load_all_records()
    chunks = []
    for record in records:
        chunks.extend(build_chunk_documents(record, settings.chunk_size, settings.chunk_overlap))

    with preview_output.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"Preview chunk ditulis ke {preview_output} dengan total {len(chunks)} chunk")

    if not args.preview_only:
        total = QdrantJobStore(settings).index_records(records)
        print(f"Berhasil mengindeks {total} chunk ke koleksi Qdrant '{settings.qdrant_collection_name}'")


if __name__ == "__main__":
    main()
