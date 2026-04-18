from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JenisRespons = Literal[
    "chat_lowongan",
    "kueri_sql",
    "analisis_cv",
    "rekomendasi_cv",
    "konsultasi_gap_skill",
]

SumberHasil = Literal["sqlite_exact", "sqlite_fts", "qdrant_semantic"]


class RawJobRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_title: str
    company_name: str
    location: str
    work_type: str
    salary: str | None = None
    job_description: str
    scrape_timestamp: str | None = Field(default=None, alias="_scrape_timestamp")


class EnrichedJobRecord(BaseModel):
    source_id: str
    source_file: str = "jobs.jsonl"
    raw_job_title: str
    standardized_job_title: str
    company_name: str
    location: str
    city: str | None = None
    province: str | None = None
    work_type: str
    salary_raw: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    seniority: str | None = None
    skills: list[str] = Field(default_factory=list)
    description_clean: str
    search_text: str
    scraped_at: str | None = None
    raw_json: str


class SearchMatch(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id_pekerjaan: int | None = Field(default=None, alias="job_id")
    id_sumber: str | None = Field(default=None, alias="source_id")
    judul: str = Field(alias="title")
    nama_perusahaan: str = Field(alias="company_name")
    lokasi: str = Field(alias="location")
    tipe_kerja: str | None = Field(default=None, alias="work_type")
    senioritas: str | None = Field(default=None, alias="seniority")
    skor: float | None = Field(default=None, alias="score")
    sumber: SumberHasil = Field(alias="source")
    cuplikan: str | None = Field(default=None, alias="snippet")
    keahlian: list[str] = Field(default_factory=list, alias="skills")

    @property
    def title(self) -> str:
        return self.judul

    @property
    def company_name(self) -> str:
        return self.nama_perusahaan

    @property
    def location(self) -> str:
        return self.lokasi

    @property
    def snippet(self) -> str | None:
        return self.cuplikan


class ParsedCV(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ringkasan: str = Field(alias="summary")
    peran_kandidat: list[str] = Field(default_factory=list, alias="candidate_roles")
    keahlian: list[str] = Field(default_factory=list, alias="skills")
    lokasi_preferensi: list[str] = Field(default_factory=list, alias="preferred_locations")
    senioritas: str | None = Field(default=None, alias="seniority")
    kueri_pencarian: str = Field(alias="search_query")
    teks_mentah: str = Field(alias="raw_text")

    @property
    def summary(self) -> str:
        return self.ringkasan

    @property
    def candidate_roles(self) -> list[str]:
        return self.peran_kandidat

    @property
    def skills(self) -> list[str]:
        return self.keahlian

    @property
    def preferred_locations(self) -> list[str]:
        return self.lokasi_preferensi

    @property
    def seniority(self) -> str | None:
        return self.senioritas

    @property
    def search_query(self) -> str:
        return self.kueri_pencarian

    @property
    def raw_text(self) -> str:
        return self.teks_mentah


class SQLPlan(BaseModel):
    aman: bool = True
    sql: str
    parameter: list[Any] = Field(default_factory=list)
    alasan: str
    template: str


class HasilSQL(BaseModel):
    sql_aman: SQLPlan
    baris: list[dict[str, Any]] = Field(default_factory=list)
    total_baris: int = 0


class GapSkillAnalysis(BaseModel):
    target_role: str
    skill_dimiliki: list[str] = Field(default_factory=list)
    skill_dibutuhkan: list[str] = Field(default_factory=list)
    skill_cocok: list[str] = Field(default_factory=list)
    skill_gap: list[str] = Field(default_factory=list)
    saran_belajar: list[str] = Field(default_factory=list)


class StructuredOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sumber: str = Field(alias="source")
    pertanyaan_dipakai: str = Field(alias="query_used")
    total_hasil: int = Field(alias="total_results")
    analisis_cv: ParsedCV | None = Field(default=None, alias="cv_analysis")
    hasil: list[SearchMatch] = Field(default_factory=list, alias="results")
    hasil_sql: HasilSQL | None = None
    analisis_gap_skill: GapSkillAnalysis | None = None
    intent: JenisRespons = "chat_lowongan"
    nama_agen: str = "supervisor_agent"


class SearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pertanyaan: str = Field(default="", alias="query")
    riwayat: str = Field(default="", alias="history")
    teks_cv: str | None = Field(default=None, alias="cv_text")
    batas: int = Field(default=5, alias="limit")
    target_role: str | None = None

    @property
    def query(self) -> str:
        return self.pertanyaan

    @property
    def history(self) -> str:
        return self.riwayat

    @property
    def cv_text(self) -> str | None:
        return self.teks_cv

    @property
    def limit(self) -> int:
        return self.batas


class SearchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    jalur: str = Field(alias="route")
    jenis_respons: JenisRespons = "chat_lowongan"
    nama_agen: str = "supervisor_agent"
    pertanyaan_dipakai: str = Field(alias="query_used")
    output_1_json_terstruktur: StructuredOutput = Field(alias="structured_output")
    output_2_summary_natural: str = Field(alias="summary")
    catatan: list[str] = Field(default_factory=list, alias="notes")

    @property
    def output_terstruktur(self) -> StructuredOutput:
        return self.output_1_json_terstruktur

    @property
    def ringkasan(self) -> str:
        return self.output_2_summary_natural


class SQLQueryRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pertanyaan: str = Field(alias="query")
    batas: int = Field(default=20, alias="limit")


class SQLQueryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    jenis_respons: JenisRespons = "kueri_sql"
    nama_agen: str = "text_to_sql_agent"
    pertanyaan_dipakai: str
    output_1_json_terstruktur: HasilSQL = Field(alias="hasil_sql")
    output_2_summary_natural: str = Field(alias="ringkasan")
    catatan: list[str] = Field(default_factory=list)

    @property
    def hasil_sql(self) -> HasilSQL:
        return self.output_1_json_terstruktur

    @property
    def ringkasan(self) -> str:
        return self.output_2_summary_natural
