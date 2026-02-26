"""Tests for Stage 3A/3B/4/5/6 features."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from papa_lang.compiler.lexer import Lexer
from papa_lang.compiler.parser import Parser
from papa_lang.compiler.validator import Validator, ValidationError
from papa_lang.compiler.codegen.python_gen import PythonGenerator
from papa_lang.compiler.codegen.crewai_gen import generate_crewai
from papa_lang.compiler.codegen.dotnet_gen import generate_dotnet, _pascal
from papa_lang.kya import generate_kya, export_kya, verify_kya
from papa_guard.blockchain import InMemoryAnchor, make_record
from papa_lang.observability import get_tracer


def _parse(src: str):
    return Parser(Lexer(src).tokenize()).parse()


def test_retrieval_parsed():
    src = "agent a { model: gpt-4o  retrieval: graph }"
    ast = _parse(src)
    assert ast.agents[0].retrieval == "graph"


def test_retrieval_graph_requires_memory():
    src = "agent a { retrieval: graph }"  # no memory
    ast = _parse(src)
    with pytest.raises(ValidationError, match="retrieval: graph requires memory"):
        Validator().validate(ast)


def test_codegen_retrieval_graph():
    src = "agent a { model: gpt-4o  memory: enabled  retrieval: graph }"
    ast = _parse(src)
    code = PythonGenerator().generate(ast)
    assert "GraphRetriever" in code
    assert "a_retriever" in code


def test_crewai_agent():
    src = "agent analyst { model: claude-3-sonnet  guard: strict }"
    ast = _parse(src)
    code = generate_crewai(ast)
    assert "from crewai import Agent" in code
    assert "analyst_agent" in code


def test_crewai_crew():
    src = "agent a {} swarm s { agents: [a] }"
    ast = _parse(src)
    code = generate_crewai(ast)
    assert "Crew(" in code


def test_pii_presidio_parsed():
    src = "swarm s { agents: [a]  pii: presidio }"
    ast = _parse(src)
    assert ast.swarms[0].pii == "presidio"


def test_presidio_codegen():
    src = "agent a {} swarm s { agents: [a]  pii: presidio }"
    ast = _parse(src)
    code = PythonGenerator().generate(ast)
    assert "PresidioPIIFilter" in code


def test_observability_parsed():
    src = "pipeline p { route: single  observability: otel }"
    ast = _parse(src)
    assert ast.pipelines[0].observability == "otel"


def test_console_tracer_works():
    tracer = get_tracer("console")
    tracer.trace_agent("test_agent", 0.05, "PASS")


def test_metaqa_ast_parsed():
    src = "agent a { model: gpt-4o  hrs_engine: metaqa }"
    ast = _parse(src)
    assert ast.agents[0].hrs_engine == "metaqa"


def test_inmemory_anchor_submit_verify():
    anchor = InMemoryAnchor()
    rec = make_record("test", "q", "r", 0.05, "PASS", "strict", "gpt-4o")
    fp = anchor.submit(rec)
    assert anchor.verify(fp) is True
    assert anchor.verify("bad") is False


def test_anchor_blockchain_parsed():
    src = "swarm s { agents: [a]  anchor: blockchain }"
    ast = _parse(src)
    assert ast.swarms[0].anchor == "blockchain"


def test_dotnet_pascal():
    assert _pascal("medical_analyst") == "MedicalAnalyst"
    assert _pascal("doctor") == "Doctor"


def test_dotnet_agent_class():
    src = "agent doctor { model: claude-3-sonnet  guard: strict }"
    ast = _parse(src)
    code = generate_dotnet(ast)
    assert "using Microsoft.SemanticKernel" in code
    assert "PapaAgentBase" in code
    assert "DoctorAgent" in code


def test_kya_generation():
    from papa_lang.compiler.ast_nodes import AgentDef

    agent = AgentDef(
        name="test", model="gpt-4o", guard="strict",
        hrs_threshold=0.10, memory=True,
    )
    kya = generate_kya(agent, "agent test {}", issued_by="TestCo")
    assert kya["kya_version"] == "1.0"
    assert kya["agent_id"] == "urn:papa-lang:agent:test"
    assert kya["issued_by"] == "TestCo"
    assert kya["constraints"]["guard"] == "strict"
    assert kya["source_hash"].startswith("sha256:")


def test_kya_verify_pass(tmp_path):
    src = "agent doc { model: gpt-4o }"
    src_file = tmp_path / "doc.papa"
    src_file.write_text(src)
    ast = _parse(src)
    kya = generate_kya(ast.agents[0], src)
    kya_file = export_kya(kya, tmp_path / "doc")
    assert verify_kya(kya_file, src_file) is True
