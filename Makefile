.PHONY: test coverage lint clean

test:
	python3 -m pytest tests/ -v 2>/dev/null || python3 papa.py test tests/test_core_std.papa

coverage:
	python3 -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing 2>/dev/null || (echo "Install: pip install pytest pytest-cov"; python3 papa.py test tests/test_core_std.papa)

lint:
	python3 -m py_compile src/lexer.py
	python3 -m py_compile src/parser.py
	python3 -m py_compile src/interpreter.py
	@echo "All files compile OK"

clean:
	rm -rf htmlcov/ .coverage .pytest_cache __pycache__
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
