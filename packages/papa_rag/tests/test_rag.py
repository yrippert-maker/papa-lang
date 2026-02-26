"""Tests for papa-rag."""

import pytest
from papa_rag import RAGPipeline, RAGConfig


def test_rag_retrieve_empty():
    pipeline = RAGPipeline(config=RAGConfig())
    result = pipeline.retrieve("test query")
    assert result.query == "test query"
    assert result.total_found >= 0
