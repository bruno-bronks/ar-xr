"""Base de conhecimento aprovada (SPEC-009, REQ-AI-002): carga, validacao e divisao em trechos."""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from spatial_assistant.policy import contains_injection
from spatial_assistant.text import fold, normalize_text

MAX_CHUNK_CHARS = 1500
_DOC_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_HIGH_RISK = re.compile(r"\s*\[risco:\s*alto\]\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    section: str
    version: str
    text: str
    equipment_types: frozenset[str]  # normalizados (sem acento, minusculas); "*" = todos
    high_risk: bool


@dataclass(frozen=True)
class Rejection:
    source: str
    reason: str


@dataclass(frozen=True)
class ParsedDocument:
    chunks: tuple[Chunk, ...]
    rejections: tuple[Rejection, ...]
    document_id: str | None = None


@dataclass(frozen=True)
class KnowledgeBase:
    chunks: tuple[Chunk, ...]
    rejections: tuple[Rejection, ...]


def _split_front_matter(text: str) -> tuple[dict[str, str], str] | None:
    lines = text.lstrip("﻿").replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep and key.strip():
            meta[key.strip().lower()] = value.strip()
    return meta, "\n".join(lines[end + 1 :])


def _valid_date(value: str) -> bool:
    if not _ISO_DATE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _approval_problem(meta: dict[str, str]) -> str | None:
    """Motivo pelo qual o documento NAO esta aprovado, ou None."""
    if not _DOC_ID.fullmatch(meta.get("id", "")):
        return "id missing or invalid"
    if meta.get("status", "") != "approved":
        return f"status is {meta.get('status', '')!r} (only 'approved' is loaded)"
    if not meta.get("approved_by"):
        return "approved_by is empty"
    if not _valid_date(meta.get("approved_on", "")):
        return "approved_on is missing or not an ISO date"
    if not any(t.strip() for t in meta.get("equipment_types", "").split(",")):
        return "equipment_types is empty"
    return None


def parse_document(source: str, text: str) -> ParsedDocument:
    """Valida um documento. Reprovado => nada e indexado; trecho com injecao => so ele e excluido."""
    split = _split_front_matter(text)
    if split is None:
        return ParsedDocument((), (Rejection(source, "missing front matter"),))
    meta, body = split
    problem = _approval_problem(meta)
    if problem is not None:
        return ParsedDocument((), (Rejection(source, problem),))

    doc_id = meta["id"]
    types = frozenset(fold(t).strip() for t in meta["equipment_types"].split(",") if t.strip())
    sections: list[tuple[str, list[str]]] = []
    for line in body.split("\n"):
        heading = _HEADING.match(line)
        if heading:
            sections.append((heading.group(1), []))
        elif sections:
            sections[-1][1].append(line)

    chunks: list[Chunk] = []
    rejections: list[Rejection] = []
    for index, (raw_title, lines) in enumerate(sections, start=1):
        label = f"{source}#{index}"
        high_risk = _HIGH_RISK.search(raw_title) is not None
        section = normalize_text(_HIGH_RISK.sub("", raw_title))
        content = normalize_text(" ".join(lines))
        if not content:
            rejections.append(Rejection(label, "empty section"))
        elif len(content) > MAX_CHUNK_CHARS:
            rejections.append(Rejection(label, "section too long"))
        elif contains_injection(section) or contains_injection(content):
            rejections.append(
                Rejection(
                    label, "section excluded: embedded instruction (possible prompt injection)"
                )
            )
        else:
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}#{index}",
                    document_id=doc_id,
                    title=normalize_text(meta.get("title", doc_id)),
                    section=section,
                    version=meta.get("version", "") or "0",
                    text=content,
                    equipment_types=types,
                    high_risk=high_risk,
                )
            )
    return ParsedDocument(tuple(chunks), tuple(rejections), doc_id)


def load_knowledge_base(directory: Path) -> KnowledgeBase:
    """Carrega `*.md` do diretorio (ordem alfabetica). Diretorio ausente => base vazia."""
    if not directory.is_dir():
        return KnowledgeBase((), ())
    chunks: list[Chunk] = []
    rejections: list[Rejection] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.md")):
        try:
            text = path.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            rejections.append(Rejection(path.name, "unreadable"))
            continue
        parsed = parse_document(path.name, text)
        rejections.extend(parsed.rejections)
        if parsed.document_id is not None and parsed.document_id in seen:
            rejections.append(Rejection(path.name, "duplicate document id"))
            continue
        if parsed.document_id is not None:
            seen.add(parsed.document_id)
        chunks.extend(parsed.chunks)
    return KnowledgeBase(tuple(chunks), tuple(rejections))
