"""L2 semantic linker backed by cached OpenAI embeddings."""

from __future__ import annotations

from pathlib import Path

from .embedder import build_embeddings, find_similar_pairs
from .models import WikiLink, WikiPage

SIMILARITY_THRESHOLD = 0.45
TOP_K_PER_PAGE = 8


def link_semantic(
    pages: list[WikiPage],
    *,
    root: Path | str | None = None,
    force_embed: bool = False,
) -> list[WikiPage]:
    target_pages = [page for page in pages if page.page_type != "index"]
    if len(target_pages) < 2:
        return pages

    embeddings, page_ids, changed_ids, current_hashes = build_embeddings(
        target_pages,
        root=root,
        force=force_embed,
    )
    pairs = find_similar_pairs(
        embeddings,
        page_ids,
        changed_ids,
        current_hashes,
        threshold=SIMILARITY_THRESHOLD,
        top_k_per_page=TOP_K_PER_PAGE,
        root=root,
    )

    by_id = {page.page_id: page for page in pages}
    for left_id, right_id, similarity in pairs:
        left_page = by_id.get(left_id)
        right_page = by_id.get(right_id)
        if left_page is None or right_page is None:
            continue

        left_targets = {link.target_page_id for link in left_page.links}
        if right_id not in left_targets:
            left_page.links.append(
                WikiLink(
                    relation="similar_to",
                    target_page_id=right_id,
                    target_path=right_page.path,
                    confidence=round(similarity, 3),
                    source=f"embedding_cosine:{similarity:.3f}",
                )
            )

        right_targets = {link.target_page_id for link in right_page.links}
        if left_id not in right_targets:
            right_page.links.append(
                WikiLink(
                    relation="similar_to",
                    target_page_id=left_id,
                    target_path=left_page.path,
                    confidence=round(similarity, 3),
                    source=f"embedding_cosine:{similarity:.3f}",
                )
            )

    return pages
