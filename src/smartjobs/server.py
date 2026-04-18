from __future__ import annotations

from functools import lru_cache

import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from .agent import SmartJobsAgent
from .config import get_settings
from .errors import LLMRequiredError, LLMResponseFormatError
from .schemas import SQLQueryRequest, SQLQueryResponse, SearchRequest, SearchResponse

settings = get_settings()
app = FastAPI(
    title="SmartJobs API",
    description="API multi-agent berbahasa Indonesia untuk pencarian lowongan, text-to-SQL aman, analisis CV, rekomendasi pekerjaan, dan konsultasi gap skill.",
)


@lru_cache(maxsize=1)
def get_agent() -> SmartJobsAgent:
    return SmartJobsAgent(settings)


@app.exception_handler(LLMRequiredError)
async def handle_llm_required(_: Request, exc: LLMRequiredError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc), "error_type": "llm_required"})


@app.exception_handler(LLMResponseFormatError)
async def handle_llm_response(_: Request, exc: LLMResponseFormatError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc), "error_type": "llm_response_format_error"})


@app.exception_handler(Exception)
async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc), "error_type": "unexpected_error"})


@app.get("/")
def root() -> dict:
    return {"pesan": "SmartJobs API berjalan", "mode": "multi-agent-llm"}


@app.get("/kesehatan")
def health() -> dict:
    return {
        "status": "ok",
        "pesan": "Layanan sehat",
        "build_version": "2026-04-19-ocr-fix",
        "jalur_sqlite": str(settings.sqlite_path),
        "koleksi_qdrant": settings.qdrant_collection_name,
        "llm_runtime_enabled": bool(settings.openai_api_key),
    }


@app.post("/obrolan", response_model=SearchResponse, response_model_by_alias=False)
def chat(request: SearchRequest) -> SearchResponse:
    return get_agent().search(request)


@app.post("/kueri-lowongan", response_model=SQLQueryResponse, response_model_by_alias=False)
def kueri_lowongan(request: SQLQueryRequest) -> SQLQueryResponse:
    return get_agent().supervisor.query_sql_agent.run(request.pertanyaan, limit=request.batas)


@app.post("/analisis-gap-skill", response_model=SearchResponse, response_model_by_alias=False)
def analisis_gap_skill(request: SearchRequest) -> SearchResponse:
    request.target_role = request.target_role or get_agent().llm.extract_target_role(request.query or "")
    if request.teks_cv is None:
        request.teks_cv = ""
    return get_agent().supervisor.gap_skill_agent.run(request)


@app.post("/unggah-cv", response_model=SearchResponse, response_model_by_alias=False)
async def upload_cv(
    file: UploadFile = File(...),
    pertanyaan: str = Form(default=""),
    riwayat: str = Form(default=""),
    batas: int = Form(default=5),
    target_role: str = Form(default=""),
) -> SearchResponse:
    file_bytes = await file.read()
    response = get_agent().search_from_file(
        file_bytes=file_bytes,
        filename=file.filename or "berkas_unggahan",
        content_type=file.content_type,
        query=pertanyaan,
        history=riwayat,
        limit=batas,
    )
    if target_role:
        response.output_terstruktur.analisis_gap_skill = get_agent().llm.analyze_skill_gap(
            target_role,
            response.output_terstruktur.analisis_cv or get_agent().llm.analyze_cv_text(""),
            response.output_terstruktur.hasil,
        )
    return response


if __name__ == "__main__":
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
