#!/usr/bin/env python3
"""Backfill A-MEM style note metadata from existing LLMWiki sources."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools.agentic_memory.audit import append_audit_log
from tools.agentic_memory.models import AgenticMemoryEntry, MemoryCandidate, MemoryDecision
from tools.agentic_memory.retrieval import build_candidate_embeddings
from tools.agentic_memory.store import (
    add_links,
    append_evolution,
    apply_neighbor_updates,
    save_store,
    touch_note,
    upsert_note,
)
from tools.llm_wiki.parsers import parse_all


TOP_K = 10
SIMILARITY_THRESHOLD = 0.65
UPDATE_NEIGHBOR_THRESHOLD = 0.82


def _split_tags(raw: str) -> list[str]:
    if not raw:
        return []
    parts = [part.strip().lstrip("#") for part in re.split(r"[,\s]+", raw) if part.strip()]
    return list(dict.fromkeys(parts))


def _keywords_from_record_title(title: str) -> list[str]:
    parts = [item.strip() for item in re.split(r"[\/\-\s（）()]+", title) if item.strip()]
    return list(dict.fromkeys(parts[:8]))


def _record_to_entry(record) -> AgenticMemoryEntry:
    memory_type = (
        str(record.metadata.get("memory_type", ""))
        if record.layer == "memories" else
        ("second_brain" if record.layer == "second_brain" else "conversation_memory")
    )
    target_section = record.section or record.title or "General"
    return AgenticMemoryEntry(
        content=record.text,
        layer=record.layer,
        memory_type=memory_type,
        target_section=target_section,
        source_path=record.source_path,
        summary=record.summary,
        keywords=_keywords_from_record_title(record.title),
        tags=_split_tags(record.tags),
        context=target_section,
    )


def _records_to_candidates(records) -> list[MemoryCandidate]:
    candidates: list[MemoryCandidate] = []
    for record in records:
        memory_type = (
            str(record.metadata.get("memory_type", ""))
            if record.layer == "memories" else
            ("second_brain" if record.layer == "second_brain" else "conversation_memory")
        )
        section_name = record.section or record.title or "General"
        candidates.append(
            MemoryCandidate(
                entry_id=record.id,
                layer=record.layer,
                source_path=record.source_path,
                section_name=section_name,
                text=record.text,
                memory_type=memory_type,
                similarity=0.0,
                metadata={
                    **dict(record.metadata),
                    "tags": _split_tags(record.tags),
                    "keywords": _keywords_from_record_title(record.title),
                    "context": section_name,
                },
            )
        )
    return candidates


def _top_neighbors(embeddings: np.ndarray, index: int, candidates: list[MemoryCandidate]) -> list[MemoryCandidate]:
    query = embeddings[index]
    scores = np.dot(embeddings, query)
    ranked: list[MemoryCandidate] = []
    for idx, candidate in enumerate(candidates):
        if idx == index:
            continue
        ranked.append(
            MemoryCandidate(
                entry_id=candidate.entry_id,
                layer=candidate.layer,
                source_path=candidate.source_path,
                section_name=candidate.section_name,
                text=candidate.text,
                memory_type=candidate.memory_type,
                similarity=round(float(scores[idx]), 6),
                metadata=dict(candidate.metadata),
            )
        )
    ranked.sort(key=lambda item: item.similarity, reverse=True)
    return ranked[:TOP_K]


def run_backfill(*, root: Path | str | None = None, dry_run: bool = False) -> dict[str, int]:
    records = [record for record in parse_all() if record.layer != "rules"]
    candidates = _records_to_candidates(records)
    embeddings, _ = build_candidate_embeddings(candidates, root=root, force=True)
    store: dict = {}
    processed = 0
    links_added = 0
    neighbor_updates = 0

    for record, candidate in zip(records, candidates):
        entry = _record_to_entry(record)
        note = upsert_note(
            store,
            entry_id=candidate.entry_id,
            content=entry.content,
            layer=entry.layer,
            memory_type=entry.memory_type,
            source_path=entry.source_path,
            target_section=entry.target_section,
            keywords=entry.keywords,
            context=entry.context,
            tags=entry.tags,
            category=entry.layer,
        )
        touch_note(note)
        neighbors = _top_neighbors(embeddings, processed, candidates)

        action = "skip_duplicate"
        reason = "no related neighbors"
        link_targets: list[str] = []
        metadata_updates: dict[str, object] = {}

        strong_neighbors = [neighbor for neighbor in neighbors if neighbor.similarity >= SIMILARITY_THRESHOLD]
        if strong_neighbors:
            action = "strengthen_link"
            reason = f"{len(strong_neighbors)} related neighbors found"
            link_targets = [neighbor.entry_id for neighbor in strong_neighbors]
            add_links(note, link_targets)
            append_evolution(
                note,
                {
                    "action": "strengthen",
                    "reason": reason,
                    "links": link_targets,
                },
            )
            links_added += len(link_targets)

            evolved_neighbors = [neighbor for neighbor in strong_neighbors if neighbor.layer == entry.layer and neighbor.similarity >= UPDATE_NEIGHBOR_THRESHOLD]
            if evolved_neighbors:
                action = "update_neighbor"
                reason = f"{len(evolved_neighbors)} same-layer neighbors updated"
                metadata_updates = {
                    "new_context_neighborhood": [entry.context for _ in evolved_neighbors],
                    "new_tags_neighborhood": [entry.tags for _ in evolved_neighbors],
                }
                for neighbor in evolved_neighbors:
                    neighbor_note = upsert_note(
                        store,
                        entry_id=neighbor.entry_id,
                        content=neighbor.text,
                        layer=neighbor.layer,
                        memory_type=neighbor.memory_type,
                        source_path=neighbor.source_path,
                        target_section=neighbor.section_name,
                        keywords=list(neighbor.metadata.get("keywords", [])),
                        context=str(neighbor.metadata.get("context", "General")),
                        tags=list(neighbor.metadata.get("tags", [])),
                        category=neighbor.layer,
                    )
                    add_links(neighbor_note, [candidate.entry_id])
                    apply_neighbor_updates(
                        neighbor_note,
                        context=entry.context,
                        tags=entry.tags,
                        reason=f"backfill from {candidate.entry_id}",
                    )
                    neighbor_updates += 1

        decision = MemoryDecision(
            action=action,
            target_path=entry.source_path,
            target_section=entry.target_section,
            reason=reason,
            matched_entry_id=strong_neighbors[0].entry_id if strong_neighbors else "",
            matched_text=strong_neighbors[0].text if strong_neighbors else "",
            link_targets=link_targets,
            metadata_updates=metadata_updates,
            similarity=strong_neighbors[0].similarity if strong_neighbors else 0.0,
        )
        append_audit_log(
            entry=entry,
            candidates=neighbors,
            decision=decision,
            changed=False,
            root=root,
        )
        processed += 1

    if not dry_run:
        save_store(store, root)

    return {
        "processed": processed,
        "links_added": links_added,
        "neighbor_updates": neighbor_updates,
        "store_notes": len(store),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill A-MEM note metadata from current LLMWiki sources")
    parser.add_argument("--root", type=str, default=None, help="LLMWiki root (default: data/llm_wiki)")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist store file")
    args = parser.parse_args()
    result = run_backfill(root=args.root, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
