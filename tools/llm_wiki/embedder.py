"""LLMWiki semantic embedding and similarity cache helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .models import WikiPage
from .openai_embeddings import DIMENSIONS, MODEL, get_embeddings
from .paths import DEFAULT_WIKI_ROOT

EMBEDDING_MODEL_NAME = MODEL
EMBEDDING_DIM = DIMENSIONS
EMBEDDINGS_FILE = "embeddings.npz"
EMBEDDINGS_META_FILE = "embeddings_meta.json"
SIMILARITY_CACHE_FILE = "similarity_cache.json"


def _page_text(page: WikiPage) -> str:
    parts = [page.title]
    if page.summary:
        parts.append(page.summary)
    if page.tags:
        parts.append(", ".join(page.tags))
    if page.key_facts:
        parts.append(". ".join(page.key_facts[:5]))
    return "\n".join(parts)


def _page_content_hash(page: WikiPage) -> str:
    return hashlib.sha256(_page_text(page).encode("utf-8")).hexdigest()[:16]


def _pair_key(id_a: str, id_b: str) -> str:
    left, right = sorted((id_a, id_b))
    return f"{left}||{right}"


def _cache_paths(root: Path | str | None = None) -> tuple[Path, Path, Path]:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    indexes = wiki_root / "indexes"
    return (
        indexes / EMBEDDINGS_FILE,
        indexes / EMBEDDINGS_META_FILE,
        indexes / SIMILARITY_CACHE_FILE,
    )


def _normalize_rows(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return embeddings / norms


def build_embeddings(
    pages: list[WikiPage],
    root: Path | str | None = None,
    *,
    force: bool = False,
) -> tuple[np.ndarray, list[str], set[str], dict[str, str]]:
    """Build page embeddings with incremental per-page caching."""

    embed_path, meta_path, _ = _cache_paths(root)
    page_ids = [page.page_id for page in pages]
    page_by_id = {page.page_id: page for page in pages}
    row_by_id = {page_id: idx for idx, page_id in enumerate(page_ids)}
    current_hashes = {page.page_id: _page_content_hash(page) for page in pages}

    cached_meta_pages: dict[str, dict] = {}
    cached_embeddings: np.ndarray | None = None
    if not force and meta_path.exists() and embed_path.exists():
        cached_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        cached_meta_pages = dict(cached_meta.get("pages", {}))
        with np.load(embed_path) as data:
            cached_embeddings = np.array(data["embeddings"], dtype=np.float32)

    changed_ids: set[str] = set()
    reuse_rows: dict[str, int] = {}
    for page_id in page_ids:
        cached = cached_meta_pages.get(page_id)
        if cached is None or cached.get("content_hash") != current_hashes[page_id]:
            changed_ids.add(page_id)
            continue
        cached_row = int(cached.get("row", -1))
        if cached_embeddings is None or cached_row < 0 or cached_row >= len(cached_embeddings):
            changed_ids.add(page_id)
            continue
        reuse_rows[page_id] = cached_row

    embeddings = np.zeros((len(pages), EMBEDDING_DIM), dtype=np.float32)
    for page_id, cached_row in reuse_rows.items():
        embeddings[row_by_id[page_id]] = cached_embeddings[cached_row]

    pages_to_embed = [page_by_id[page_id] for page_id in page_ids if page_id in changed_ids]
    if pages_to_embed:
        texts = [_page_text(page) for page in pages_to_embed]
        fresh = np.array(get_embeddings(texts), dtype=np.float32)
        fresh = _normalize_rows(fresh)
        for idx, page in enumerate(pages_to_embed):
            embeddings[row_by_id[page.page_id]] = fresh[idx]

    embed_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(embed_path, embeddings=embeddings)
    meta_path.write_text(
        json.dumps(
            {
                "model": EMBEDDING_MODEL_NAME,
                "dim": EMBEDDING_DIM,
                "pages": {
                    page_id: {"content_hash": current_hashes[page_id], "row": row}
                    for row, page_id in enumerate(page_ids)
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return embeddings, page_ids, changed_ids, current_hashes


def _load_similarity_cache(root: Path | str | None = None) -> dict[str, dict]:
    _, _, sim_path = _cache_paths(root)
    if not sim_path.exists():
        return {}
    return json.loads(sim_path.read_text(encoding="utf-8"))


def _save_similarity_cache(cache: dict[str, dict], root: Path | str | None = None) -> None:
    _, _, sim_path = _cache_paths(root)
    sim_path.parent.mkdir(parents=True, exist_ok=True)
    sim_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def find_similar_pairs(
    embeddings: np.ndarray,
    page_ids: list[str],
    changed_ids: set[str],
    current_hashes: dict[str, str],
    *,
    threshold: float = 0.45,
    top_k_per_page: int = 8,
    root: Path | str | None = None,
) -> list[tuple[str, str, float]]:
    """Return qualifying page pairs while caching cosine similarities by pair."""

    current_id_set = set(page_ids)
    cache = _load_similarity_cache(root)
    valid_cache: dict[str, dict] = {}
    for key, entry in cache.items():
        parts = key.split("||")
        if len(parts) != 2:
            continue
        if parts[0] in current_id_set and parts[1] in current_id_set:
            valid_cache[key] = entry

    row_by_id = {page_id: idx for idx, page_id in enumerate(page_ids)}
    updated_cache: dict[str, dict] = {}
    by_page: dict[str, list[tuple[str, float]]] = {page_id: [] for page_id in page_ids}

    for left_idx, left_id in enumerate(page_ids):
        left_hash = current_hashes[left_id]
        left_row = row_by_id[left_id]
        for right_idx in range(left_idx + 1, len(page_ids)):
            right_id = page_ids[right_idx]
            right_hash = current_hashes[right_id]
            key = _pair_key(left_id, right_id)
            cached = valid_cache.get(key)

            if (
                cached is not None
                and left_id not in changed_ids
                and right_id not in changed_ids
                and cached.get("hash_a") == left_hash
                and cached.get("hash_b") == right_hash
            ):
                similarity = float(cached["similarity"])
            else:
                similarity = float(np.dot(embeddings[left_row], embeddings[right_idx]))

            updated_cache[key] = {
                "similarity": round(similarity, 6),
                "hash_a": left_hash,
                "hash_b": right_hash,
            }

            if similarity < threshold:
                continue
            by_page[left_id].append((right_id, similarity))
            by_page[right_id].append((left_id, similarity))

    _save_similarity_cache(updated_cache, root)

    selected_pairs: dict[tuple[str, str], float] = {}
    for page_id, candidates in by_page.items():
        candidates.sort(key=lambda item: item[1], reverse=True)
        for other_id, similarity in candidates[:top_k_per_page]:
            pair = tuple(sorted((page_id, other_id)))
            if pair not in selected_pairs or similarity > selected_pairs[pair]:
                selected_pairs[pair] = similarity

    return [
        (left_id, right_id, similarity)
        for (left_id, right_id), similarity in sorted(
            selected_pairs.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
