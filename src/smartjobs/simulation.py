from __future__ import annotations

import json
import os
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="SmartJobs", layout="wide")
st.title("SmartJobs Demo")
st.caption("Multi-agent LLM untuk chat lowongan, text-to-SQL aman, analisis CV, rekomendasi pekerjaan, dan konsultasi gap skill.")
st.warning("Runtime API ini wajib memakai OpenAI/LLM aktif. Tanpa OPENAI_API_KEY, endpoint akan mengembalikan error 503.")

mode = st.radio(
    "Pilih mode",
    ["Chat lowongan", "Kueri data lowongan", "Analisis CV / rekomendasi", "Konsultasi gap skill"],
    horizontal=True,
)

pertanyaan = st.text_input("Pertanyaan", placeholder="Contoh: lowongan Data Analyst di Jakarta")
riwayat = st.text_area("Riwayat percakapan (opsional)", height=80)
batas = st.slider("Jumlah hasil", min_value=1, max_value=20, value=5)
target_role = st.text_input("Role target (opsional)", placeholder="Contoh: Data Scientist")

teks_cv = None
berkas_unggahan = None
if mode in {"Analisis CV / rekomendasi", "Konsultasi gap skill"}:
    teks_cv = st.text_area("Teks CV (opsional)", height=180, placeholder="Tempel isi CV di sini bila tidak mengunggah file")
    berkas_unggahan = st.file_uploader(
        "Unggah file CV (opsional)",
        type=["txt", "md", "docx", "pdf", "png", "jpg", "jpeg", "webp"],
    )


def _extract_error_message(payload: Any, response: requests.Response) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message") or payload.get("error")
        if detail:
            return str(detail)
    text = (response.text or "").strip()
    if text:
        return text[:1000]
    return f"Permintaan gagal dengan status {response.status_code}"



def _parse_response_payload(response: requests.Response) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type.lower():
        try:
            payload = response.json()
        except ValueError as exc:
            raw_text = (response.text or "").strip()
            raise RuntimeError(
                "API mengembalikan content-type JSON tetapi body tidak valid JSON. "
                f"Status={response.status_code}. Cuplikan respons: {raw_text[:500]}"
            ) from exc
        if not isinstance(payload, dict):
            raise RuntimeError(
                "API mengembalikan JSON, tetapi bentuk payload bukan object/dict seperti yang diharapkan Streamlit."
            )
        return payload

    raw_text = (response.text or "").strip()
    if response.status_code >= 400:
        raise RuntimeError(_extract_error_message(None, response))
    raise RuntimeError(
        "API mengembalikan respons non-JSON padahal frontend mengharapkan JSON. "
        f"Status={response.status_code}. Content-Type={content_type or 'tidak ada'}. Cuplikan respons: {raw_text[:500]}"
    )


if st.button("Proses"):
    try:
        if mode == "Kueri data lowongan":
            response = requests.post(f"{API_URL}/kueri-lowongan", json={"pertanyaan": pertanyaan, "batas": batas}, timeout=120)
        elif berkas_unggahan is not None:
            response = requests.post(
                f"{API_URL}/unggah-cv",
                data={"pertanyaan": pertanyaan, "riwayat": riwayat, "batas": batas, "target_role": target_role},
                files={"file": (berkas_unggahan.name, berkas_unggahan.getvalue(), berkas_unggahan.type or "application/octet-stream")},
                timeout=120,
            )
        else:
            endpoint = "/analisis-gap-skill" if mode == "Konsultasi gap skill" else "/obrolan"
            response = requests.post(
                f"{API_URL}{endpoint}",
                json={"pertanyaan": pertanyaan, "riwayat": riwayat, "teks_cv": teks_cv or None, "batas": batas, "target_role": target_role or None},
                timeout=120,
            )

        payload = _parse_response_payload(response)
        if response.status_code >= 400:
            st.error(_extract_error_message(payload, response))
            st.stop()

        kiri, kanan = st.columns([1, 1])
        with kiri:
            st.subheader("Output 2 - Summary natural")
            st.write(payload.get("output_2_summary_natural", ""))
            if payload.get("catatan"):
                st.info("\n".join(payload["catatan"]))
        with kanan:
            st.subheader("Output 1 - JSON terstruktur")
            st.code(json.dumps(payload.get("output_1_json_terstruktur", {}), ensure_ascii=False, indent=2), language="json")
    except Exception as exc:
        st.error(f"Permintaan gagal: {exc}")
