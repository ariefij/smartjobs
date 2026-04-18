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
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah record untuk test cepat.")
    parser.add_argument("--progress-every", type=int, default=25, help="Cetak progress tiap N record.")
    parser.add_argument("--strict-llm", action="store_true", help="Hentikan proses jika satu panggilan LLM gagal, alih-alih fallback ke normalizer lokal.")
    parser.add_argument("--show-llm-errors", action="store_true", help="Cetak error LLM mentah per record sebelum fallback dipakai.")
    args = parser.parse_args()

    settings = get_settings()
    input_path = args.input or ROOT / settings.raw_dataset_path
    output_db = args.output_db or ROOT / settings.sqlite_path
    output_jsonl = args.output_jsonl or ROOT / settings.cleaned_jsonl_path

    output_db.parent.mkdir(parents=True, exist_ok=True)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    if args.disable_llm:
        print("Mode SQLite build: fallback normalizer (--disable-llm aktif)")
    else:
        settings.require_openai_api_key("build_sqlite LLM enrichment")
        print(f"Mode SQLite build: OpenAI enrichment aktif (model={settings.llm_model})")

    llm = OpenAIJobLLM(settings)
    if not args.disable_llm and not llm.enabled:
        raise RuntimeError(
            "OPENAI_API_KEY terdeteksi tetapi client OpenAI tidak aktif. Pastikan dependency 'openai' terpasang dengan benar lewat 'poetry install'."
        )
    records = []
    fallback_count = 0
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for index, raw_payload in enumerate(iter_jsonl(input_path), start=1):
            if args.limit is not None and index > args.limit:
                break
            raw = RawJobRecord.model_validate(raw_payload)
            if llm.enabled and not args.disable_llm:
                try:
                    fallback_record = fallback_enrich_job(raw)
                    record = llm.enrich_job(raw, raise_on_error=args.strict_llm or args.show_llm_errors)
                    if record.model_dump() == fallback_record.model_dump():
                        fallback_count += 1
                except Exception as exc:
                    if args.strict_llm:
                        raise
                    if args.show_llm_errors:
                        print(f"Peringatan: enrichment LLM gagal pada record ke-{index} (source_id={raw.source_id}), fallback lokal dipakai. Detail: {exc}")
                    record = fallback_enrich_job(raw)
                    fallback_count += 1
            else:
                record = fallback_enrich_job(raw)
            records.append(record)
            handle.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")
            if args.progress_every > 0 and (index == 1 or index % args.progress_every == 0):
                print(f"Progress SQLite build: {index} record selesai diproses | fallback={fallback_count}")

    store = SQLiteJobStore(output_db)
    store.rebuild(records)
    print(f"Menulis {len(records)} record yang sudah dibersihkan ke {output_jsonl}")
    print(f"Basis data SQLite berhasil dibuat di {output_db}")
    print(f"Total fallback lokal selama build SQLite: {fallback_count}")
    print("Selesai build SQLite.")


if __name__ == "__main__":
    main()