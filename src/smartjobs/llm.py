from __future__ import annotations

import base64
import json
import re
import time
from typing import Any, Iterable

from pydantic import ValidationError

from .config import Settings
from .errors import LLMRequiredError, LLMResponseFormatError
from .normalizers import fallback_enrich_job, infer_skills
from .observability import NoOpLangfuseObserver
from .prompt_registry import PromptRegistry
from .schemas import EnrichedJobRecord, GapSkillAnalysis, ParsedCV, RawJobRecord, SearchMatch, StructuredOutput

VALID_INTENTS = {"chat_lowongan", "kueri_sql", "analisis_cv", "rekomendasi_cv", "konsultasi_gap_skill"}


class OpenAIJobLLM:
    def __init__(self, settings: Settings, observer: NoOpLangfuseObserver | None = None):
        self.settings = settings
        self.observer = observer or NoOpLangfuseObserver()
        self.client = None
        self.langfuse_client = getattr(self.observer, "client", None)
        self.prompts = PromptRegistry(
            "langfuse_prompts.json",
            observer=self.observer,
            langfuse_client=self.langfuse_client,
        )
        if settings.openai_api_key:
            try:
                from openai import OpenAI
            except Exception:
                OpenAI = None
            if OpenAI is not None:
                kwargs = {"api_key": settings.openai_api_key, "timeout": settings.llm_request_timeout_seconds}
                kwargs["max_retries"] = max(settings.llm_max_retries, 0)
                if settings.openai_base_url:
                    kwargs["base_url"] = settings.openai_base_url
                self.client = OpenAI(**kwargs)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def enrich_job(self, raw: RawJobRecord, *, raise_on_error: bool = False) -> EnrichedJobRecord:
        if not self.enabled:
            if raise_on_error:
                raise LLMRequiredError("OpenAI client tidak aktif untuk job enrichment.")
            return fallback_enrich_job(raw)

        schema_hint = {
            "source_id": "string",
            "raw_job_title": "string",
            "standardized_job_title": "string",
            "company_name": "string",
            "location": "string",
            "city": "string|null",
            "province": "string|null",
            "work_type": "string",
            "salary_raw": "string|null",
            "salary_min": "integer|null",
            "salary_max": "integer|null",
            "currency": "string|null",
            "seniority": "string|null",
            "skills": ["string"],
            "description_clean": "string",
            "search_text": "string",
            "scraped_at": "string|null",
            "raw_json": "string",
        }
        try:
            content = self._chat_json(
                prompt_key="job_enrichment",
                model=self.settings.llm_model,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"schema_hint": schema_hint, "raw_record": raw.model_dump(by_alias=True)},
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            return EnrichedJobRecord.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError) as exc:
            if raise_on_error:
                raise RuntimeError(
                    "Output LLM untuk job enrichment tidak valid JSON / schema. "
                    f"source_id={raw.source_id}. Detail: {exc}"
                ) from exc
            return fallback_enrich_job(raw)
        except Exception as exc:
            if raise_on_error:
                raise RuntimeError(
                    "Panggilan LLM untuk job enrichment gagal. "
                    f"source_id={raw.source_id}. Detail: {exc}"
                ) from exc
            return fallback_enrich_job(raw)

    def analyze_cv_text(self, cv_text: str) -> ParsedCV:
        self._ensure_runtime_llm_enabled("analisis CV")
        schema_hint = {
            "ringkasan": "string",
            "peran_kandidat": ["string"],
            "keahlian": ["string"],
            "lokasi_preferensi": ["string"],
            "senioritas": "string|null",
            "kueri_pencarian": "string",
            "teks_mentah": "string",
        }
        content = self._chat_json(
            prompt_key="cv_analysis",
            model=self.settings.llm_model,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps({"schema_hint": schema_hint, "teks_cv": cv_text[:20000]}, ensure_ascii=False),
                },
            ],
        )
        try:
            return ParsedCV.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMResponseFormatError("Output LLM untuk analisis CV tidak sesuai kontrak JSON yang diwajibkan.") from exc

    def classify_intent(self, pertanyaan: str, has_cv: bool = False) -> tuple[str, str | None]:
        self._ensure_runtime_llm_enabled("intent router")
        content = self._chat_json(
            prompt_key="intent_router",
            model=self.settings.llm_model,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "pertanyaan": pertanyaan,
                            "has_cv": has_cv,
                            "label_valid": sorted(VALID_INTENTS),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMResponseFormatError("Output LLM untuk intent router tidak valid JSON.") from exc
        intent = str(payload.get("intent") or "").strip()
        if intent not in VALID_INTENTS:
            raise LLMResponseFormatError("Output LLM untuk intent router tidak memuat label intent yang valid.")
        target_role = payload.get("target_role")
        if isinstance(target_role, str):
            target_role = target_role.strip() or None
        else:
            target_role = None
        return intent, target_role or self.extract_target_role(pertanyaan)

    def extract_target_role(self, text: str) -> str | None:
        text = (text or "").strip()
        if not text:
            return None
        match = re.search(r"(?:role|posisi|jabatan|untuk|sebagai)\s+([A-Za-z][A-Za-z /-]{2,40})", text, re.I)
        if match:
            return " ".join(word.capitalize() for word in match.group(1).split())
        for role in [
            "Data Analyst", "Data Scientist", "Data Engineer", "Business Analyst", "Software Engineer",
            "Product Manager", "UI UX Designer", "Machine Learning Engineer",
        ]:
            if role.lower() in text.lower():
                return role
        return None

    def extract_text_from_images(self, images: Iterable[tuple[bytes, str]]) -> str:
        self._ensure_runtime_llm_enabled("vision OCR untuk CV gambar/PDF scan")
        image_items = list(images)
        if not image_items:
            raise LLMResponseFormatError("Tidak ada gambar yang bisa diproses untuk vision OCR.")
        content: list[dict[str, Any]] = [
            {"type": "input_text", "text": "Ekstrak teks CV dari halaman atau gambar ini secara setia. Kembalikan teks polos saja."}
        ]
        for image_bytes, mime_type in image_items:
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            content.append({"type": "input_image", "image_url": f"data:{mime_type};base64,{encoded}"})
        try:
            with self.observer.trace("llm.extract_text_from_images", {"model": self.settings.vision_model, "image_count": len(image_items)}):
                response = self.client.responses.create(
                    model=self.settings.vision_model,
                    input=[{"role": "user", "content": content}],
                )
            text = (response.output_text or "").strip()
            if not text:
                raise LLMResponseFormatError("GPT-4 Vision tidak mengembalikan teks OCR yang bisa dipakai.")
            return text
        except LLMResponseFormatError:
            raise
        except Exception as exc:
            raise LLMResponseFormatError(
                "Vision OCR gagal diproses. Periksa format file, ukuran gambar/PDF, koneksi ke OpenAI, dan respons model. "
                f"Detail asli: {exc}"
            ) from exc

    def generate_outputs(
        self,
        query_used: str,
        route: str,
        matches: list[SearchMatch],
        cv_analysis: ParsedCV | None = None,
        *,
        intent: str = "chat_lowongan",
        nama_agen: str = "search_lowongan_agent",
        hasil_sql: dict | None = None,
        analisis_gap_skill: GapSkillAnalysis | None = None,
    ) -> tuple[StructuredOutput, str]:
        self._ensure_runtime_llm_enabled("generasi output response")
        content = self._chat_json(
            prompt_key="response_generation",
            model=self.settings.llm_model,
            temperature=0.2,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "pertanyaan_dipakai": query_used,
                            "jalur": route,
                            "intent": intent,
                            "nama_agen": nama_agen,
                            "analisis_cv": cv_analysis.model_dump() if cv_analysis else None,
                            "hasil_cocok": [match.model_dump() for match in matches],
                            "hasil_sql": hasil_sql,
                            "analisis_gap_skill": analisis_gap_skill.model_dump() if analisis_gap_skill else None,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMResponseFormatError("Output LLM untuk response generation tidak valid JSON.") from exc
        structured_payload = (
            payload.get("output_1_json_terstruktur")
            or payload.get("output_terstruktur")
            or payload.get("structured_output")
        )
        summary_payload = (
            payload.get("output_2_summary_natural")
            or payload.get("ringkasan")
            or payload.get("summary")
        )
        if structured_payload is None or summary_payload is None:
            raise LLMResponseFormatError(
                "LLM wajib mengembalikan dua output: output_1_json_terstruktur dan output_2_summary_natural."
            )
        try:
            structured = StructuredOutput.model_validate(structured_payload)
        except ValidationError as exc:
            raise LLMResponseFormatError("Output 1 JSON terstruktur dari LLM tidak sesuai schema sistem.") from exc
        summary = str(summary_payload).strip()
        if not summary:
            raise LLMResponseFormatError("Output 2 summary natural dari LLM kosong.")
        return structured, summary

    def analyze_skill_gap(
        self,
        target_role: str,
        cv_analysis: ParsedCV,
        matches: list[SearchMatch],
    ) -> GapSkillAnalysis:
        self._ensure_runtime_llm_enabled("analisis gap skill")
        content = self._chat_json(
            prompt_key="skill_gap",
            model=self.settings.llm_model,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "target_role": target_role,
                            "cv_analysis": cv_analysis.model_dump(),
                            "lowongan_relevan": [match.model_dump() for match in matches[:10]],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        try:
            return GapSkillAnalysis.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMResponseFormatError("Output LLM untuk analisis gap skill tidak sesuai kontrak JSON.") from exc

    def _chat_json(self, *, prompt_key: str, model: str, temperature: float, messages: list[dict[str, Any]]) -> str:
        self._ensure_runtime_llm_enabled(prompt_key)
        system_prompt = self.prompts.get_prompt(prompt_key)
        max_attempts = max(1, int(self.settings.llm_max_retries))
        backoff_seconds = max(0.0, float(self.settings.llm_retry_backoff_seconds))
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                with self.observer.trace(
                    "llm.chat_json",
                    {
                        "prompt_key": prompt_key,
                        "prompt_name": self.prompts.get_prompt_meta(prompt_key).get("name", prompt_key),
                        "model": model,
                        "message_count": len(messages) + 1,
                        "attempt": attempt,
                    },
                ):
                    response = self.client.chat.completions.create(
                        model=model,
                        temperature=temperature,
                        response_format={"type": "json_object"},
                        messages=[{"role": "system", "content": system_prompt}, *messages],
                    )
                return response.choices[0].message.content or "{}"
            except Exception as exc:
                last_exc = exc
                if attempt >= max_attempts:
                    raise RuntimeError(
                        f"Panggilan OpenAI gagal setelah {max_attempts} percobaan untuk prompt '{prompt_key}'. "
                        f"Periksa OPENAI_API_KEY, koneksi jaringan, quota, dan timeout. Detail asli: {exc}"
                    ) from exc
                if backoff_seconds > 0:
                    time.sleep(backoff_seconds * attempt)
        raise RuntimeError(f"Panggilan OpenAI gagal untuk prompt '{prompt_key}'.") from last_exc

    def _ensure_runtime_llm_enabled(self, feature: str) -> None:
        if self.enabled:
            return
        raise LLMRequiredError(
            f"Fitur '{feature}' wajib memakai OpenAI LLM. Isi OPENAI_API_KEY agar chat, analisis CV teks/gambar, vision OCR, intent router, dan dua output response bisa berjalan penuh secara LLM-based."
        )

    def _fallback_cv(self, cv_text: str) -> ParsedCV:
        skills = infer_skills([cv_text])
        lowered = cv_text.lower()
        roles = []
        for role in ["Data Analyst", "Data Scientist", "Data Engineer", "Business Analyst", "Machine Learning Engineer"]:
            if role.lower() in lowered:
                roles.append(role)
        if not roles and skills:
            roles = ["Data Analyst"]
        seniority = None
        for token, label in [("intern", "Intern"), ("junior", "Junior"), ("senior", "Senior"), ("manager", "Manager")]:
            if re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", lowered):
                seniority = label
                break
        query = ", ".join(roles + skills[:5]) if roles or skills else "rekomendasi pekerjaan berdasarkan CV"
        return ParsedCV(
            ringkasan="CV dianalisis dengan mode fallback tanpa LLM. Gunakan OPENAI_API_KEY untuk hasil ekstraksi yang lebih kaya.",
            peran_kandidat=roles,
            keahlian=skills,
            lokasi_preferensi=[],
            senioritas=seniority,
            kueri_pencarian=query,
            teks_mentah=cv_text,
        )

    def _fallback_skill_gap(self, target_role: str, cv_analysis: ParsedCV, matches: list[SearchMatch]) -> GapSkillAnalysis:
        required_skills: list[str] = []
        for match in matches:
            for skill in match.keahlian:
                if skill not in required_skills:
                    required_skills.append(skill)
        owned = list(dict.fromkeys(cv_analysis.keahlian))
        same = [skill for skill in owned if skill in required_skills]
        gap = [skill for skill in required_skills if skill not in owned]
        suggestions = [f"Pelajari {skill} melalui project mini, kursus, dan portofolio." for skill in gap[:5]]
        return GapSkillAnalysis(
            target_role=target_role,
            skill_dimiliki=owned,
            skill_dibutuhkan=required_skills,
            skill_cocok=same,
            skill_gap=gap,
            saran_belajar=suggestions,
        )

    def _fallback_summary(
        self,
        query_used: str,
        route: str,
        matches: list[SearchMatch],
        cv_analysis: ParsedCV | None,
        hasil_sql: dict | None,
        analisis_gap_skill: GapSkillAnalysis | None,
        intent: str,
    ) -> str:
        if intent == "kueri_sql" and hasil_sql:
            return self._format_sql_summary(query_used, hasil_sql)
        if intent == "konsultasi_gap_skill" and analisis_gap_skill:
            gap = ", ".join(analisis_gap_skill.skill_gap[:5]) or "tidak ada gap utama"
            return f"Analisis gap skill untuk role {analisis_gap_skill.target_role}: gap utama adalah {gap}."
        if intent in {"analisis_cv", "rekomendasi_cv"} and cv_analysis:
            peran = ", ".join(cv_analysis.peran_kandidat) or "belum terdeteksi"
            intro = f"CV berhasil dianalisis. Peran kandidat yang terdeteksi: {peran}."
        else:
            intro = ""
        if not matches:
            return intro + (" Tidak ada hasil yang ditemukan. Coba ubah kata kunci atau aktifkan pencarian semantik Qdrant.")
        head = f"Ditemukan {len(matches)} hasil untuk '{query_used}' melalui jalur {route}."
        bullets = []
        for match in matches[:3]:
            snippet = (match.cuplikan or "")[:120].strip()
            bullets.append(f"- {match.judul} di {match.nama_perusahaan} ({match.lokasi}){': ' + snippet if snippet else ''}")
        return (intro + " " + head).strip() + "\n" + "\n".join(bullets)

    def _format_sql_summary(self, query_used: str, hasil_sql: dict) -> str:
        rows = hasil_sql.get("baris") or []
        if not rows:
            return f"Kueri '{query_used}' diproses melalui jalur text-to-SQL aman, tetapi tidak mengembalikan data."
        first = rows[0]
        numeric_items = [(key, value) for key, value in first.items() if isinstance(value, (int, float))]
        if len(rows) == 1 and len(numeric_items) == 1:
            key, value = numeric_items[0]
            label = key.replace("_", " ")
            return f"Kueri '{query_used}' diproses melalui jalur text-to-SQL aman. Nilai {label} adalah {value}."
        return f"Kueri '{query_used}' diproses melalui jalur text-to-SQL aman dan menghasilkan {len(rows)} baris data."
