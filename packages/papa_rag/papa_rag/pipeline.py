"""RAG pipeline — retrieval with optional ChromaDB backend."""

from .models import RAGConfig, RAGResult, RAGChunk
from typing import Optional


class RAGPipeline:
    """Hybrid RAG pipeline. Uses ChromaDB when available."""

    def __init__(self, config: Optional[RAGConfig] = None, persist_dir: str = "data/rag"):
        self.config = config or RAGConfig()
        self.persist_dir = persist_dir
        self._store = None

    def _get_store(self):
        """Lazy init ChromaDB store. Returns None if chromadb not available."""
        if self._store is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings
                client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                self._store = client.get_or_create_collection(
                    "papa_rag",
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                self._store = False
        return self._store if self._store is not False else None

    def retrieve(self, query: str) -> RAGResult:
        """Retrieve top-k chunks for query."""
        import time
        start = time.perf_counter()
        store = self._get_store()

        if store is None:
            return RAGResult(
                query=query,
                chunks=[],
                total_found=0,
                retrieval_time_ms=int((time.perf_counter() - start) * 1000),
                context="",
            )

        try:
            results = store.query(
                query_texts=[query],
                n_results=self.config.top_k,
            )
            docs = results.get("documents", [[]])
            dists = results.get("distances", [[]])
            doc_list = (docs[0] or []) if docs else []
            dist_list = (dists[0] or []) if dists else []

            chunks = []
            for i, doc in enumerate(doc_list):
                dist = dist_list[i] if i < len(dist_list) else None
                score = 1.0 - (float(dist) / 2.0) if dist is not None else 0.5
                if score >= self.config.min_score:
                    chunks.append(RAGChunk(content=doc or "", score=score, source=""))

            context = "\n\n".join(c.content for c in chunks[: self.config.top_k])
            return RAGResult(
                query=query,
                chunks=chunks,
                total_found=len(chunks),
                retrieval_time_ms=int((time.perf_counter() - start) * 1000),
                context=context,
            )
        except Exception:
            return RAGResult(
                query=query,
                chunks=[],
                total_found=0,
                retrieval_time_ms=int((time.perf_counter() - start) * 1000),
                context="",
            )
