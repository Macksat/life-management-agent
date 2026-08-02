"""L4 serendipity linker."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from tools.openai_env import load_repo_dotenv

from .coref_logger import load_co_references
from .embedder import _load_similarity_cache
from .models import WikiLink, WikiPage
from .paths import DEFAULT_WIKI_ROOT

MAX_CANDIDATES = 30
MAX_LINKS_PER_PAGE = 5
CACHE_FILE = "serendipity_cache.json"
DEFAULT_LLM_MODELS = ("gpt-5-mini", "gpt-4.1-mini")


def _cache_path(root: Path | str | None = None) -> Path:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    return wiki_root / "indexes" / CACHE_FILE


def _is_cross_category(page_a: WikiPage, page_b: WikiPage) -> bool:
    if page_a.page_type != page_b.page_type:
        return True
    tags_a = set(page_a.tags)
    tags_b = set(page_b.tags)
    return bool(tags_a and tags_b and not (tags_a & tags_b))


def _find_candidates(
    pages: list[WikiPage],
    *,
    root: Path | str | None = None,
) -> list[tuple[WikiPage, WikiPage, str]]:
    by_path = {page.path: page for page in pages}
    by_id = {page.page_id: page for page in pages}
    seen_pairs: set[tuple[str, str]] = set()
    candidates: list[tuple[WikiPage, WikiPage, str]] = []

    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    for ref in load_co_references(root=root):
        for left_path, right_path in combinations(ref.pages, 2):
            pair = tuple(sorted((left_path, right_path)))
            pair_counts[pair] += 1

    for (path_a, path_b), _count in sorted(pair_counts.items(), key=lambda item: item[1], reverse=True):
        page_a = by_path.get(path_a)
        page_b = by_path.get(path_b)
        if page_a is None or page_b is None or not _is_cross_category(page_a, page_b):
            continue
        pair_key = tuple(sorted((page_a.page_id, page_b.page_id)))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        candidates.append((page_a, page_b, "co_ref"))
        if len(candidates) >= MAX_CANDIDATES:
            return candidates

    sim_cache = _load_similarity_cache(root=root)
    for key, entry in sorted(
        sim_cache.items(),
        key=lambda item: item[1].get("similarity", 0.0),
        reverse=True,
    ):
        similarity = float(entry.get("similarity", 0.0))
        if similarity < 0.25 or similarity > 0.50:
            continue
        parts = key.split("||")
        if len(parts) != 2:
            continue
        page_a = by_id.get(parts[0])
        page_b = by_id.get(parts[1])
        if page_a is None or page_b is None or not _is_cross_category(page_a, page_b):
            continue
        pair_key = tuple(sorted((page_a.page_id, page_b.page_id)))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        candidates.append((page_a, page_b, "mid_distance_embedding"))
        if len(candidates) >= MAX_CANDIDATES:
            break

    return candidates


def _load_cache(root: Path | str | None = None) -> dict[str, str]:
    path = _cache_path(root)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_cache(cache: dict[str, str], root: Path | str | None = None) -> None:
    path = _cache_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _ask_llm_for_bridge(page_a: WikiPage, page_b: WikiPage) -> str | None:
    from openai import OpenAI

    load_repo_dotenv()
    client = OpenAI()
    prompt = f"""以下の2つのページに共通する抽象的な原理、構造的な類似性、
または片方から他方に転用できるアイデアを1行（40文字以内）で述べてください。
共通点がなければ「none」とだけ答えてください。

## ページA: {page_a.title}
要約: {page_a.summary}
タグ: {', '.join(page_a.tags)}
Key Facts: {'; '.join(page_a.key_facts[:3])}

## ページB: {page_b.title}
要約: {page_b.summary}
タグ: {', '.join(page_b.tags)}
Key Facts: {'; '.join(page_b.key_facts[:3])}"""
    models: list[str] = []
    env_model = os.getenv("LLMWIKI_SERENDIPITY_MODEL", "").strip()
    if env_model:
        models.append(env_model)
    for model in DEFAULT_LLM_MODELS:
        if model not in models:
            models.append(model)

    last_error: Exception | None = None
    for model in models:
        try:
            response = client.responses.create(
                model=model,
                input=prompt,
                max_output_tokens=80,
            )
            answer = getattr(response, "output_text", "").strip()
            if answer.lower() in {"none", "なし", "共通点なし"}:
                return None
            return answer or None
        except Exception as exc:  # pragma: no cover - exercised in live API runs
            last_error = exc

    if last_error is not None:
        raise last_error
    return None


def link_serendipity(
    pages: list[WikiPage],
    *,
    root: Path | str | None = None,
    use_llm: bool = True,
    dry_run: bool = False,
) -> list[WikiPage]:
    candidates = _find_candidates(pages, root=root)
    if not candidates or not use_llm:
        return pages

    cache = _load_cache(root=root)
    added_count: dict[str, int] = defaultdict(int)

    for page_a, page_b, reason in candidates:
        pair_key = "||".join(sorted((page_a.page_id, page_b.page_id)))
        if pair_key in cache:
            bridge = None if cache[pair_key] == "__none__" else cache[pair_key]
        else:
            bridge = _ask_llm_for_bridge(page_a, page_b)
            cache[pair_key] = bridge if bridge else "__none__"

        if bridge is None or dry_run:
            continue

        confidence = 0.6 if reason == "co_ref" else 0.4
        source_text = f"abstract_bridge: {bridge}"

        existing_a = {link.target_page_id for link in page_a.links if link.relation == "serendipity"}
        if added_count[page_a.page_id] < MAX_LINKS_PER_PAGE and page_b.page_id not in existing_a:
            page_a.links.append(
                WikiLink(
                    relation="serendipity",
                    target_page_id=page_b.page_id,
                    target_path=page_b.path,
                    confidence=confidence,
                    source=source_text,
                )
            )
            added_count[page_a.page_id] += 1

        existing_b = {link.target_page_id for link in page_b.links if link.relation == "serendipity"}
        if added_count[page_b.page_id] < MAX_LINKS_PER_PAGE and page_a.page_id not in existing_b:
            page_b.links.append(
                WikiLink(
                    relation="serendipity",
                    target_page_id=page_a.page_id,
                    target_path=page_a.path,
                    confidence=confidence,
                    source=source_text,
                )
            )
            added_count[page_b.page_id] += 1

    _save_cache(cache, root=root)
    return pages
