"""L3 co-reference linker."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from .coref_logger import load_co_references
from .models import CoReference, WikiLink, WikiPage

MIN_CO_OCCURRENCES = 2
MAX_LINKS_PER_PAGE = 10


def _aggregate_pairs(
    co_refs: list[CoReference],
) -> tuple[Counter[tuple[str, str]], dict[tuple[str, str], list[str]]]:
    pair_counts: Counter[tuple[str, str]] = Counter()
    pair_intents: dict[tuple[str, str], list[str]] = defaultdict(list)
    for ref in co_refs:
        for left_path, right_path in combinations(ref.pages, 2):
            pair = tuple(sorted((left_path, right_path)))
            pair_counts[pair] += 1
            pair_intents[pair].append(ref.query_intent)
    return pair_counts, pair_intents


def link_co_referenced(
    pages: list[WikiPage],
    *,
    root: Path | str | None = None,
) -> list[WikiPage]:
    co_refs = load_co_references(root=root)
    if not co_refs:
        return pages

    pair_counts, pair_intents = _aggregate_pairs(co_refs)
    by_path = {page.path: page for page in pages}
    added_count: dict[str, int] = defaultdict(int)

    for (path_a, path_b), count in sorted(pair_counts.items(), key=lambda item: item[1], reverse=True):
        if count < MIN_CO_OCCURRENCES:
            continue

        page_a = by_path.get(path_a)
        page_b = by_path.get(path_b)
        if page_a is None or page_b is None:
            continue

        representative_intent = pair_intents[(path_a, path_b)][-1]
        confidence = min(0.95, 0.3 + 0.1 * count)
        source_text = f"co_ref:{count}回, 代表: {representative_intent}"

        if added_count[path_a] < MAX_LINKS_PER_PAGE:
            existing_targets = {
                link.target_path for link in page_a.links if link.relation == "co_referenced"
            }
            if path_b not in existing_targets:
                page_a.links.append(
                    WikiLink(
                        relation="co_referenced",
                        target_page_id=page_b.page_id,
                        target_path=path_b,
                        confidence=confidence,
                        source=source_text,
                    )
                )
                added_count[path_a] += 1

        if added_count[path_b] < MAX_LINKS_PER_PAGE:
            existing_targets = {
                link.target_path for link in page_b.links if link.relation == "co_referenced"
            }
            if path_a not in existing_targets:
                page_b.links.append(
                    WikiLink(
                        relation="co_referenced",
                        target_page_id=page_a.page_id,
                        target_path=path_a,
                        confidence=confidence,
                        source=source_text,
                    )
                )
                added_count[path_b] += 1

    return pages
