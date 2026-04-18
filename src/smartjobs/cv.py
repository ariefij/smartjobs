from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .config import Settings
from .errors import LLMRequiredError, LLMResponseFormatError
from .llm import OpenAIJobLLM


def extract_docx_text(file_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", ns):
        texts = [node.text for node in paragraph.findall(".//w:t", ns) if node.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs).strip()


def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""
    reader = PdfReader(io.BytesIO(file_bytes))
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts).strip()


def render_pdf_pages(file_bytes: bytes, max_pages: int = 5) -> list[tuple[bytes, str]]:
    try:
        import fitz
    except Exception:
        return []
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    images: list[tuple[bytes, str]] = []
    for index in range(min(len(doc), max_pages)):
        page = doc[index]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        images.append((pix.tobytes("png"), "image/png"))
    return images


def extract_cv_text(
    file_bytes: bytes,
    filename: str,
    content_type: str | None,
    llm: OpenAIJobLLM,
    settings: Settings,
) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        return file_bytes.decode("utf-8", errors="ignore"), "text"
    if suffix == ".docx":
        return extract_docx_text(file_bytes), "docx"
    if suffix == ".pdf":
        text = extract_pdf_text(file_bytes)
        if text.strip():
            return text, "pdf-text"
        if not llm.enabled:
            raise LLMRequiredError(
                "CV PDF hasil scan membutuhkan GPT-4 Vision/OpenAI agar teks bisa diekstrak dan dianalisis. Isi OPENAI_API_KEY terlebih dahulu."
            )
        vision_text = llm.extract_text_from_images(render_pdf_pages(file_bytes, settings.max_vision_pages))
        if not vision_text.strip():
            raise LLMResponseFormatError("GPT-4 Vision tidak menghasilkan teks CV dari PDF scan.")
        return vision_text, "pdf-vision"
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        if not llm.enabled:
            raise LLMRequiredError(
                "CV gambar membutuhkan GPT-4 Vision/OpenAI agar teks bisa diekstrak dan dianalisis. Isi OPENAI_API_KEY terlebih dahulu."
            )
        vision_text = llm.extract_text_from_images([(file_bytes, content_type or "image/png")])
        if not vision_text.strip():
            raise LLMResponseFormatError("GPT-4 Vision tidak menghasilkan teks CV dari gambar.")
        return vision_text, "image-vision"
    return file_bytes.decode("utf-8", errors="ignore"), "fallback"
