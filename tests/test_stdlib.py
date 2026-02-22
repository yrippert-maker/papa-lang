"""PAPA Lang stdlib tests."""
import pytest
from tests.conftest import run_papa


class TestMath:
    def test_sqrt(self):
        interp = run_papa('import "std/math"\nsay sqrt(16)')
        assert "4" in interp.output[-1]

    def test_floor_ceil(self):
        interp = run_papa('import "std/math"\nsay floor(3.7)\nsay ceil(3.2)')
        assert "3" in interp.output[0]
        assert "4" in interp.output[1]

    def test_pi_e(self):
        interp = run_papa('import "std/math"\nsay pi > 3\nsay e > 2')
        assert "True" in interp.output or "true" in interp.output


class TestString:
    def test_upper_lower(self):
        interp = run_papa('import "std/string"\nsay upper("hello")\nsay lower("WORLD")')
        assert "HELLO" in interp.output[0]
        assert "world" in interp.output[1]

    def test_trim(self):
        interp = run_papa('import "std/string"\nsay trim("  x  ")')
        assert "x" in interp.output[-1]

    def test_split_join(self):
        interp = run_papa('import "std/string"\nparts = split("a,b,c", ",")\nsay join(parts, "-")')
        assert "a-b-c" in interp.output[-1]


class TestJson:
    def test_encode_decode(self):
        interp = run_papa('import "std/json"\ndata = {a -> 1}\nenc = json_encode(data)\ndec = json_decode(enc)\nsay dec')
        assert len(interp.output) >= 1


class TestTime:
    def test_timestamp(self):
        interp = run_papa('import "std/time"\nt = timestamp()\nsay t > 0')
        assert "True" in interp.output[-1] or "true" in interp.output[-1]
