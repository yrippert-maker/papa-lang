"""Pydantic models for papa-rag."""

from pydantic import BaseModel
from typing import List, Optional


class RAGChunk(BaseModel):
    content: str
    score: float = 0.0
    source: str = ""


class RAGConfig(BaseModel):
    top_k: int = 5
    min_score: float = 0.5
    strategy: str = "semantic"  # semantic | keyword | hybrid
    rerank: bool = False


class RAGResult(BaseModel):
    query: str
    chunks: List[RAGChunk] = []
    total_found: int = 0
    retrieval_time_ms: int = 0
    context: str = ""
