#!/bin/bash
# Публикация 4 пакетов в порядке зависимостей
# 1. papa-guard   (нет зависимостей от нас)
# 2. papa-lang    (зависит от papa-guard)
# 3. papa-rag     (зависит от papa-lang)
# 4. @papa-lang/core (npm, независимый)

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== 1. papa-guard (PyPI) ==="
cd packages/papa_guard
python -m build
twine upload dist/*  # или --repository testpypi для TestPyPI
cd "$REPO_ROOT"

echo "=== 2. papa-lang (PyPI) ==="
cd packages/papa_lang
python -m build
twine upload dist/*
cd "$REPO_ROOT"

echo "=== 3. papa-rag (PyPI) ==="
cd packages/papa_rag
python -m build
twine upload dist/*
cd "$REPO_ROOT"

echo "=== 4. @papa-lang/core (npm) ==="
cd packages/papa-lang-core
npm run build
npm publish --access public
cd "$REPO_ROOT"

echo "Done. All 4 packages published."
