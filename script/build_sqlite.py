from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartjobs.config import get_settings
from smartjobs.llm import OpenAIJobLLM
from smartjobs.normalizers import fallback_enrich_job
from smartjobs.schemas import RawJobRecord
from smartjobs.sqlite_store import SQLiteJobStore


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bangun basis data SQLite dari jobs JSONL mentah.")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output-db", type=Path, default=None)
    parser.add_argument("--output-jsonl", type=Path, default=None)
    parser.add_argument("--disable-llm", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    input_path = args.input or ROOT / settings.raw_dataset_path
    output_db = args.output_db or ROOT / settings.sqlite_path
    output_jsonl = args.output_jsonl or ROOT / settings.cleaned_jsonl_path

    output_db.parent.mkdir(parents=True, exist_ok=True)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    llm = OpenAIJobLLM(settings)
    records = []
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for raw_payload in iter_jsonl(input_path):
            raw = RawJobRecord.model_validate(raw_payload)
            record = llm.enrich_job(raw) if llm.enabled and not args.disable_llm else fallback_enrich_job(raw)
            records.append(record)
            handle.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")

    store = SQLiteJobStore(output_db)
    store.rebuild(records)
    print(f"Menulis {len(records)} record yang sudah dibersihkan ke {output_jsonl}")
    print(f"Basis data SQLite berhasil dibuat di {output_db}")


if __name__ == "__main__":
    main()
