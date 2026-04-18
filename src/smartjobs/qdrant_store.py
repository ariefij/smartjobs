from __future__ import annotations

from typing import Iterable
from uuid import NAMESPACE_URL, uuid5

from .chunking import build_chunk_documents
from .config import Settings
from .schemas import EnrichedJobRecord, SearchMatch


def make_qdrant_point_id(source_id: str, chunk_index: int) -> str:
    seed = f"smartjobs:{source_id}:{chunk_index}"
    return str(uuid5(NAMESPACE_URL, seed))


class QdrantJobStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def index_records(self, records: Iterable[EnrichedJobRecord]) -> int:
        try:
            from langchain_core.documents import Document
            from langchain_openai import OpenAIEmbeddings
            from langchain_qdrant import QdrantVectorStore
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except Exception as exc:
            raise RuntimeError("Dependensi Qdrant/LangChain belum terpasang.") from exc

        qdrant_url = self.settings.require_qdrant_url()
        openai_api_key = self.settings.require_openai_api_key("indexing embedding ke Qdrant")
        client = QdrantClient(url=qdrant_url, api_key=self.settings.qdrant_api_key)
        collections = {item.name for item in client.get_collections().collections}
        if self.settings.qdrant_collection_name not in collections:
            client.create_collection(
                collection_name=self.settings.qdrant_collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )

        embeddings = OpenAIEmbeddings(
            model=self.settings.embedding_model,
            api_key=openai_api_key,
            base_url=self.settings.openai_base_url,
        )
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=self.settings.qdrant_collection_name,
            embedding=embeddings,
        )

        documents: list[Document] = []
        ids: list[str] = []
        for record in records:
            for chunk in build_chunk_documents(record, self.settings.chunk_size, self.settings.chunk_overlap):
                documents.append(Document(page_content=chunk["text"], metadata=chunk["metadata"]))
                ids.append(make_qdrant_point_id(record.source_id, int(chunk['chunk_index'])))
        if documents:
            vector_store.add_documents(documents=documents, ids=ids)
        return len(documents)

    def semantic_search(self, query: str, limit: int = 5) -> list[SearchMatch]:
        try:
            from langchain_openai import OpenAIEmbeddings
            from langchain_qdrant import QdrantVectorStore
            from qdrant_client import QdrantClient
        except Exception as exc:
            raise RuntimeError("Dependensi untuk pencarian semantik belum terpasang.") from exc

        qdrant_url = self.settings.require_qdrant_url()
        openai_api_key = self.settings.require_openai_api_key("semantic search ke Qdrant")
        client = QdrantClient(url=qdrant_url, api_key=self.settings.qdrant_api_key)
        embeddings = OpenAIEmbeddings(
            model=self.settings.embedding_model,
            api_key=openai_api_key,
            base_url=self.settings.openai_base_url,
        )
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=self.settings.qdrant_collection_name,
            embedding=embeddings,
        )
        docs = vector_store.similarity_search_with_score(query, k=limit)
        results: list[SearchMatch] = []
        for doc, score in docs:
            metadata = doc.metadata or {}
            results.append(
                SearchMatch(
                    job_id=None,
                    source_id=metadata.get("source_id"),
                    title=metadata.get("title", "Pekerjaan Tidak Dikenal"),
                    company_name=metadata.get("company_name", "Perusahaan Tidak Dikenal"),
                    location=metadata.get("location", "Lokasi Tidak Dikenal"),
                    work_type=metadata.get("work_type"),
                    seniority=metadata.get("seniority"),
                    score=float(score),
                    source="qdrant_semantic",
                    snippet=doc.page_content[:320],
                    skills=list(metadata.get("skills") or []),
                )
            )
        return results
