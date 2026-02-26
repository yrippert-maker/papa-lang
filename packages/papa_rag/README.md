# papa-rag

> Hybrid RAG pipeline: semantic + keyword + RRF reranking.

## Install

```bash
pip install papa-rag
```

Requires `papa-lang` and `chromadb`.

## Quick Start

```python
from papa_rag import RAGPipeline, RAGConfig

config = RAGConfig(top_k=5)
pipeline = RAGPipeline(config=config)
result = pipeline.retrieve("What is the capital of France?")
print(result.context)
```
