#!/bin/bash
# Публикация с переменными окружения (без интерактивного ввода)
# Использование:
#   TEST=1 TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-xxx ./scripts/publish_with_env.sh  # TestPyPI
#   TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-xxx NPM_TOKEN=xxx ./scripts/publish_with_env.sh  # Prod

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

[ -f "$REPO_ROOT/.env.publish" ] && set -a && source "$REPO_ROOT/.env.publish" && set +a
USE_TEST="${TEST:-0}"

# PyPI
if [ -z "$TWINE_USERNAME" ] || [ -z "$TWINE_PASSWORD" ]; then
  echo "⚠️  Установите TWINE_USERNAME и TWINE_PASSWORD (для TestPyPI: username=__token__, password=pypi-xxx)"
  exit 1
fi

echo "=== 1. papa-guard ==="
cd packages/papa_guard
python3 -m build --quiet 2>/dev/null || python3 -m build
if [ "$USE_TEST" = "1" ]; then
  twine upload --repository testpypi --non-interactive dist/*
else
  twine upload --non-interactive dist/*
fi
cd "$REPO_ROOT"

echo "=== 2. papa-lang ==="
cd packages/papa_lang
python3 -m build --quiet 2>/dev/null || python3 -m build
if [ "$USE_TEST" = "1" ]; then
  twine upload --repository testpypi --non-interactive dist/*
else
  twine upload --non-interactive dist/*
fi
cd "$REPO_ROOT"

echo "=== 3. papa-rag ==="
cd packages/papa_rag
python3 -m build --quiet 2>/dev/null || python3 -m build
if [ "$USE_TEST" = "1" ]; then
  twine upload --repository testpypi --non-interactive dist/*
else
  twine upload --non-interactive dist/*
fi
cd "$REPO_ROOT"

echo "=== 4. @papa-lang/core (npm) ==="
cd packages/papa-lang-core
npm run build --silent 2>/dev/null || npm run build
if [ -n "$NPM_TOKEN" ]; then
  echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > ~/.npmrc.papa 2>/dev/null || true
  npm config set //registry.npmjs.org/:_authToken "$NPM_TOKEN"
fi
npm publish --access public
cd "$REPO_ROOT"

echo "✅ Done."
