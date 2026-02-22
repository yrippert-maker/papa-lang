"""PAPA Lang Interpreter tests."""
import pytest
from src.lexer import lex
from src.parser import parse
from src.interpreter import Interpreter
from src.environment import PapaError

from tests.conftest import run_papa


class TestArithmetic:
    def test_add(self):
        interp = run_papa('x = 2 + 3\nsay x')
        assert "5" in interp.output[-1]

    def test_multiply(self):
        interp = run_papa('say 6 * 7')
        assert "42" in interp.output[-1]


class TestMaybe:
    def test_some_none(self):
        interp = run_papa("""
x = some(10)
say x ?? 0
y = none()
say y ?? 99
""")
        assert "10" in interp.output
        assert "99" in interp.output

    def test_optional_chaining(self):
        interp = run_papa('m = map()\nsay m.get("k") ?? "default"')
        assert "default" in interp.output[-1]


class TestImmutability:
    def test_reassign_without_mut_fails(self):
        with pytest.raises(PapaError):
            run_papa("x = 1\nx = 2")

    def test_reassign_with_mut_ok(self):
        interp = run_papa("mut x = 1\nx = 2\nsay x")
        assert "2" in interp.output[-1]


class TestFunctions:
    def test_simple_function(self):
        interp = run_papa("double(x) = x * 2\nsay double(5)")
        assert "10" in interp.output[-1]

    def test_recursive_fib(self):
        interp = run_papa("""
fib(n: int) -> int
  if n <= 1
    return n
  return fib(n - 1) + fib(n - 2)
say fib(10)
""")
        assert "55" in interp.output[-1]


class TestTypeChecking:
    def test_correct_types_pass(self):
        interp = run_papa("add(a: int, b: int) -> int = a + b\nsay add(2, 3)")
        assert "5" in interp.output[-1]

    def test_wrong_type_raises(self):
        with pytest.raises(PapaError):
            run_papa('add(a: int, b: int) -> int = a + b\nsay add("x", 3)')


class TestCollections:
    def test_list_count(self):
        interp = run_papa('lst = list([1, 2, 3])\nsay lst.count')
        assert "3" in interp.output[-1]

    def test_map_get(self):
        interp = run_papa('m = {a -> 1, b -> 2}\nv = m.get("a")\nsay v ?? 0')
        assert "1" in interp.output[-1]
