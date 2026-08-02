"""Candidate retrieval for A-MEM style source updates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from tools.llm_wiki.openai_embeddings import DIMENSIONS, MODEL, get_embeddings
from tools.llm_wiki.parsers import parse_conversation_memory, parse_memories, parse_second_brain
from tools.llm_wiki.paths import DEFAULT_WIKI_ROOT, REPO_ROOT

from .models import AgenticMemoryEntry, MemoryCandidate

EMBEDDING_MODEL_NAME = MODEL
EMBEDDING_DIM = DIMENSIONS
EMBEDDINGS_FILE = "agentic_memory_embeddings.npz"
EMBEDDINGS_META_FILE = "agentic_memory_embeddings_meta.json"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _normalize_rows(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return embeddings / norms


def _cache_paths(root: Path | str | None = None) -> tuple[Path, Path]:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    indexes = wiki_root / "indexes"
    return indexes / EMBEDDINGS_FILE, indexes / EMBEDDINGS_META_FILE


def _resolve_source_dir(base_dir: Path | str | None = None) -> Path:
    if base_dir is None:
        return REPO_ROOT / "data" / "llm_wiki" / "sources" / "memories"
    return Path(base_dir)


def _resolve_companion_memories_dir(base_dir: Path | str | None = None) -> Path:
    if base_dir is None:
        return REPO_ROOT / "data" / "llm_wiki" / "sources" / "memories"
    path = Path(base_dir)
    sibling = path.parent / "memories"
    if sibling.exists():
        return sibling
    nested = path / "memories"
    if nested.exists():
        return nested
    return _resolve_source_dir()


def _entry_text(entry: AgenticMemoryEntry) -> str:
    parts = [entry.content]
    if entry.summary:
        parts.append(entry.summary)
    if entry.context:
        parts.append(entry.context)
    if entry.tags:
        parts.append(", ".join(entry.tags))
    if entry.keywords:
        parts.append(", ".join(entry.keywords))
    return "\n".join(part for part in parts if part).strip()


def load_memory_candidates(base_dir: Path | str | None = None) -> list[MemoryCandidate]:
    candidates: list[MemoryCandidate] = []
    source_dir = _resolve_source_dir(base_dir)
    for record in parse_memories(source_dir):
        memory_type = str(record.metadata.get("memory_type", ""))
        if memory_type not in {"preferences", "facts", "decisions"}:
            continue
        candidates.append(
            MemoryCandidate(
                entry_id=f"{record.id}:{record.source_path}:{record.section}",
                layer="memories",
                source_path=record.source_path,
                section_name=record.section,
                text=record.text,
                memory_type=memory_type,
                similarity=0.0,
                metadata=dict(record.metadata),
            )
        )
    return candidates


def load_second_brain_candidates(base_dir: Path | str | None = None) -> list[MemoryCandidate]:
    candidates: list[MemoryCandidate] = []
    source_dir = Path(base_dir) if base_dir is not None else REPO_ROOT / "data" / "llm_wiki" / "sources" / "second_brain"
    for record in parse_second_brain(source_dir):
        candidates.append(
            MemoryCandidate(
                entry_id=record.id,
                layer="second_brain",
                source_path=record.source_path,
                section_name=record.title,
                text=record.text,
                memory_type="second_brain",
                similarity=0.0,
                metadata=dict(record.metadata),
            )
        )
    return candidates


def load_conversation_candidates(base_dir: Path | str | None = None) -> list[MemoryCandidate]:
    candidates: list[MemoryCandidate] = []
    source_dir = Path(base_dir) if base_dir is not None else REPO_ROOT / "data" / "llm_wiki" / "sources" / "conversation_memory"
    for record in parse_conversation_memory(source_dir):
        candidates.append(
            MemoryCandidate(
                entry_id=record.id,
                layer="conversation_memory",
                source_path=record.source_path,
                section_name=record.section,
                text=record.text,
                memory_type="conversation_memory",
                similarity=0.0,
                metadata=dict(record.metadata),
            )
        )
    return candidates


def _load_cached_embeddings(
    *,
    root: Path | str | None = None,
) -> tuple[dict[str, dict], np.ndarray | None]:
    embed_path, meta_path = _cache_paths(root)
    if not embed_path.exists() or not meta_path.exists():
        return {}, None
    cached_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    cached_entries = dict(cached_meta.get("entries", {}))
    with np.load(embed_path) as data:
        cached_embeddings = np.array(data["embeddings"], dtype=np.float32)
    return cached_entries, cached_embeddings


def build_candidate_embeddings(
    candidates: list[MemoryCandidate],
    *,
    root: Path | str | None = None,
    force: bool = False,
) -> tuple[np.ndarray, dict[str, str]]:
    embed_path, meta_path = _cache_paths(root)
    cached_meta_entries: dict[str, dict] = {}
    cached_embeddings: np.ndarray | None = None
    if not force:
        cached_meta_entries, cached_embeddings = _load_cached_embeddings(root=root)

    current_hashes = {candidate.entry_id: _content_hash(candidate.text) for candidate in candidates}
    row_by_id = {candidate.entry_id: idx for idx, candidate in enumerate(candidates)}
    embeddings = np.zeros((len(candidates), EMBEDDING_DIM), dtype=np.float32)
    missing: list[MemoryCandidate] = []

    for candidate in candidates:
        cached = cached_meta_entries.get(candidate.entry_id)
        if cached is None or cached.get("content_hash") != current_hashes[candidate.entry_id]:
            missing.append(candidate)
            continue
        row = int(cached.get("row", -1))
        if cached_embeddings is None or row < 0 or row >= len(cached_embeddings):
            missing.append(candidate)
            continue
        embeddings[row_by_id[candidate.entry_id]] = cached_embeddings[row]

    if missing:
        fresh = np.array(get_embeddings([candidate.text for candidate in missing]), dtype=np.float32)
        fresh = _normalize_rows(fresh)
        for idx, candidate in enumerate(missing):
            embeddings[row_by_id[candidate.entry_id]] = fresh[idx]

    embed_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(embed_path, embeddings=embeddings)
    meta_payload = {
        "model": EMBEDDING_MODEL_NAME,
        "dim": EMBEDDING_DIM,
        "entries": {
            candidate.entry_id: {"content_hash": current_hashes[candidate.entry_id], "row": row}
            for row, candidate in enumerate(candidates)
        },
    }
    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return embeddings, current_hashes


def search_memory_candidates(
    entry: AgenticMemoryEntry,
    *,
    base_dir: Path | str | None = None,
    root: Path | str | None = None,
    top_k: int = 10,
    force_embed: bool = False,
) -> list[MemoryCandidate]:
    memory_base = base_dir if entry.layer == "memories" else _resolve_companion_memories_dir(base_dir)
    candidates = load_memory_candidates(memory_base)
    if entry.layer == "memories":
        filtered = [candidate for candidate in candidates if candidate.memory_type == entry.memory_type]
    elif entry.layer == "second_brain":
        digest_dir = Path(base_dir) if base_dir is not None else REPO_ROOT / "data" / "llm_wiki" / "sources" / "second_brain"
        filtered = load_second_brain_candidates(digest_dir)
        filtered.extend(candidates)
    elif entry.layer == "conversation_memory":
        convo_dir = Path(base_dir) if base_dir is not None else REPO_ROOT / "data" / "llm_wiki" / "sources" / "conversation_memory"
        filtered = load_conversation_candidates(convo_dir)
        filtered.extend(candidates)
    else:
        filtered = []
    if not filtered:
        return []

    candidate_embeddings, _ = build_candidate_embeddings(filtered, root=root, force=force_embed)
    query_embedding = np.array(get_embeddings([_entry_text(entry)]), dtype=np.float32)
    query_embedding = _normalize_rows(query_embedding)[0]
    scores = np.dot(candidate_embeddings, query_embedding)

    ranked: list[MemoryCandidate] = []
    for candidate, score in zip(filtered, scores):
        ranked.append(
            MemoryCandidate(
                entry_id=candidate.entry_id,
                layer=candidate.layer,
                source_path=candidate.source_path,
                section_name=candidate.section_name,
                text=candidate.text,
                memory_type=candidate.memory_type,
                similarity=round(float(score), 6),
                metadata=dict(candidate.metadata),
            )
        )
    ranked.sort(key=lambda item: item.similarity, reverse=True)
    return ranked[:top_k]
