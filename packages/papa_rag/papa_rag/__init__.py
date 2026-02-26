"""papa-rag — Hybrid RAG pipeline: semantic + keyword + RRF reranking."""

from .models import RAGConfig, RAGResult
from .pipeline import RAGPipeline

__version__ = "0.1.0"
__all__ = ["RAGPipeline", "RAGConfig", "RAGResult"]
