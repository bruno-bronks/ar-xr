"""REQ-ENG-006 / OUT-ENG-001: a matriz de rastreabilidade e consistente e verificavel."""

import csv
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MATRIX = ROOT / "docs/requirements/traceability.csv"
REQUIREMENTS = (ROOT / "docs/requirements/requirements.md").read_text("utf-8")
METRICS = (ROOT / "docs/outcomes/metrics.md").read_text("utf-8")

COLUMNS = [
    "req_id", "outcome_id", "spec", "z_spec", "adr", "contract",
    "tests", "code", "telemetry", "status", "notes",
]  # fmt: skip
PATH_COLUMNS = ["spec", "z_spec", "adr", "contract", "tests", "code"]
STATUSES = {"verified", "partial", "planned"}


def _rows() -> list[dict[str, str]]:
    with MATRIX.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        assert None not in row, f"{row['req_id']}: colunas a mais (virgula nao escapada?)"
        assert all(v is not None for v in row.values()), f"{row['req_id']}: colunas faltando"
    return rows


def _cells(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def _is_marker(cell: str) -> bool:
    """`n/a:<motivo>` ou `pending:<motivo>` — lacunas declaradas explicitamente."""
    return cell.startswith(("n/a:", "pending:"))


def test_header_has_expected_columns() -> None:
    with MATRIX.open(encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == COLUMNS


def test_every_requirement_in_catalog_has_exactly_one_row() -> None:
    catalog = re.findall(r"^\| (REQ-[A-Z]+-\d{3}) \|", REQUIREMENTS, flags=re.MULTILINE)
    rows = [row["req_id"] for row in _rows()]

    assert catalog
    assert sorted(rows) == sorted(catalog)
    assert len(rows) == len(set(rows))


def test_every_outcome_exists_in_metrics() -> None:
    for row in _rows():
        assert row["outcome_id"] in METRICS, row["req_id"]
        assert row["outcome_id"] in REQUIREMENTS, row["req_id"]


def test_status_is_known_and_planned_rows_do_not_claim_artifacts_as_verified() -> None:
    for row in _rows():
        assert row["status"] in STATUSES, row["req_id"]
        if row["status"] == "planned":
            assert row["code"].startswith("pending:"), row["req_id"]


def test_referenced_paths_exist() -> None:
    for row in _rows():
        for column in PATH_COLUMNS:
            for cell in _cells(row[column]):
                if _is_marker(cell):
                    continue
                assert (ROOT / cell).exists(), f"{row['req_id']}.{column}: {cell} nao existe"


def test_every_path_column_is_filled_or_explicitly_marked() -> None:
    for row in _rows():
        for column in PATH_COLUMNS:
            assert _cells(row[column]), f"{row['req_id']}.{column} vazio (use n/a: ou pending:)"


def test_verified_rows_are_linked_to_spec_test_and_code() -> None:
    for row in _rows():
        if row["status"] != "verified":
            continue
        for column in ("spec", "tests", "code"):
            assert not any(_is_marker(c) for c in _cells(row[column])), (row["req_id"], column)
        assert row["telemetry"].strip(), row["req_id"]


def test_partial_rows_explain_what_is_pending() -> None:
    for row in _rows():
        if row["status"] == "partial":
            assert row["notes"].strip(), row["req_id"]
            assert not _is_marker(_cells(row["tests"])[0]), row["req_id"]


@pytest.mark.parametrize("column", ["tests"])
def test_each_listed_test_file_mentions_its_requirement(column: str) -> None:
    for row in _rows():
        for cell in _cells(row[column]):
            if _is_marker(cell):
                continue
            assert row["req_id"] in (ROOT / cell).read_text("utf-8"), (row["req_id"], cell)


def test_adr_files_have_status_and_decision_sections() -> None:
    for adr in (ROOT / "docs/adr").glob("*.md"):
        text = adr.read_text("utf-8")
        assert re.search(r"^## Status", text, flags=re.MULTILINE), adr.name
        assert re.search(r"^## Decis", text, flags=re.MULTILINE), adr.name
