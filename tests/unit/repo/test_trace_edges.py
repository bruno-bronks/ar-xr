"""REQ-ENG-008: arestas VERIFICADAS de rastreabilidade (Graphify e so indice auxiliar)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


trace_edges = _load("trace_edges")
crosscheck = _load("graph_crosscheck")


def test_committed_edge_file_is_up_to_date_with_the_matrix() -> None:
    assert trace_edges.main(["--check"]) == 0


def test_every_edge_is_verified_and_points_to_an_existing_artifact_or_requirement() -> None:
    document = json.loads((ROOT / "graph/mappings/traceability-edges.json").read_text("utf-8"))
    reqs = {e["source"] for e in document["edges"] if e["source"].startswith("REQ-")}
    reqs |= {e["target"] for e in document["edges"] if e["target"].startswith("REQ-")}

    assert document["edge_count"] == len(document["edges"]) > 0
    for edge in document["edges"]:
        assert edge["status"] == "VERIFIED"
        assert edge["origin"] == "traceability.csv"
        for end in (edge["source"], edge["target"]):
            assert end in reqs or end.startswith("OUT-") or (ROOT / end).exists(), end


def test_edge_vocabulary_matches_the_plan() -> None:
    document = json.loads((ROOT / "graph/mappings/traceability-edges.json").read_text("utf-8"))
    relations = {e["relation"] for e in document["edges"]}

    assert {"IMPLEMENTS", "TESTED_BY", "DECIDED_BY"} <= relations  # plano §9


def test_declared_gaps_do_not_become_edges() -> None:
    document = json.loads((ROOT / "graph/mappings/traceability-edges.json").read_text("utf-8"))

    for edge in document["edges"]:
        assert not edge["target"].startswith(("n/a:", "pending:"))
        assert not edge["source"].startswith(("n/a:", "pending:"))


def test_code_implements_requirement_direction() -> None:
    edges = trace_edges.build_edges()

    assert {
        "source": "services/api/app/twin.py",
        "relation": "IMPLEMENTS",
        "target": "REQ-MNT-002",
        "status": "VERIFIED",
        "origin": "traceability.csv",
    } in edges
    assert any(e["relation"] == "TESTED_BY" and e["source"] == "REQ-MNT-002" for e in edges)


def test_crosscheck_never_walks_through_external_nodes() -> None:
    """Regressao: `pytest`/`datetime` conectavam tudo com tudo e 'confirmavam' cobertura falsa."""
    nodes = {
        "t": {"source_file": "tests/a.py"},
        "ext": {"source_file": ""},
        "c": {"source_file": "src/b.py"},
    }
    adjacency = {"t": [("ext", "EXTRACTED")], "ext": [("t", "EXTRACTED"), ("c", "EXTRACTED")]}

    assert crosscheck.connected(nodes, adjacency, "tests/a.py", "src/b.py", 4) is None

    adjacency_direct = {"t": [("c", "EXTRACTED")], "c": [("t", "EXTRACTED")]}
    assert crosscheck.connected(nodes, adjacency_direct, "tests/a.py", "src/b.py", 4) == (
        "EXTRACTED",
        1,
    )


def test_crosscheck_flags_inference_in_the_path() -> None:
    nodes = {
        "t": {"source_file": "t.py"},
        "m": {"source_file": "m.py"},
        "c": {"source_file": "c.py"},
    }
    adjacency = {"t": [("m", "EXTRACTED")], "m": [("c", "INFERRED")]}

    assert crosscheck.connected(nodes, adjacency, "t.py", "c.py", 4) == ("INFERRED", 2)
