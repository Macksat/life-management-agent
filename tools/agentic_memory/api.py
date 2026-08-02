"""Public API for Phase 1 agentic memory updates."""

from __future__ import annotations

from pathlib import Path

import hashlib

from .audit import append_audit_log
from .models import AgenticMemoryEntry, MemoryUpdateResult
from .policy import JudgeFn, decide_memory_action
from .retrieval import search_memory_candidates
from .store import (
    add_links,
    append_evolution,
    apply_neighbor_updates,
    load_store,
    save_store,
    touch_note,
    upsert_note,
)
from .writers import apply_memory_decision


def _entry_id_for_entry(entry: AgenticMemoryEntry) -> str:
    digest = hashlib.sha256(
        f"{entry.layer}|{entry.memory_type}|{entry.target_section}|{entry.content}".encode("utf-8")
    ).hexdigest()[:16]
    return f"{entry.layer}:{entry.memory_type}:{digest}"


def _extract_neighbor_updates(decision, index: int = 0) -> tuple[str | None, list[str] | None]:
    metadata = decision.metadata_updates or {}
    contexts = metadata.get("new_context_neighborhood", [])
    tags = metadata.get("new_tags_neighborhood", [])
    context = contexts[index] if index < len(contexts) else None
    tag_list = tags[index] if index < len(tags) else None
    return context, tag_list


def process_memory_entry(
    entry: AgenticMemoryEntry,
    *,
    base_dir: Path | str | None = None,
    root: Path | str | None = None,
    judge: JudgeFn | None = None,
    top_k: int = 10,
    apply: bool = True,
    force_embed: bool = False,
) -> MemoryUpdateResult:
    candidates = search_memory_candidates(
        entry,
        base_dir=base_dir,
        root=root,
        top_k=top_k,
        force_embed=force_embed,
    )
    decision = decide_memory_action(entry, candidates, judge=judge)
    changed = False
    error = ""
    store = load_store(root)
    entry_id = _entry_id_for_entry(entry)

    entry_note = upsert_note(
        store,
        entry_id=entry_id,
        content=entry.content,
        layer=entry.layer,
        memory_type=entry.memory_type,
        source_path=entry.source_path,
        target_section=entry.target_section,
        keywords=entry.keywords,
        context=entry.context or "General",
        tags=entry.tags,
    )

    try:
        for candidate in candidates:
            candidate_note = upsert_note(
                store,
                entry_id=candidate.entry_id,
                content=candidate.text,
                layer=candidate.layer,
                memory_type=candidate.memory_type,
                source_path=candidate.source_path,
                target_section=candidate.section_name,
                context=str(candidate.metadata.get("context", "General")),
                tags=list(candidate.metadata.get("tags", [])),
                keywords=list(candidate.metadata.get("keywords", [])),
            )
            touch_note(candidate_note)

        if apply:
            changed = apply_memory_decision(entry, decision, base_dir=base_dir)

        if decision.link_targets:
            add_links(entry_note, decision.link_targets)
            append_evolution(
                entry_note,
                {
                    "action": decision.action,
                    "reason": decision.reason,
                    "links": decision.link_targets,
                },
            )

        if decision.matched_entry_id and decision.matched_entry_id in store:
            neighbor = store[decision.matched_entry_id]
            add_links(neighbor, [entry_id])
            if decision.action == "update_neighbor":
                context, tags = _extract_neighbor_updates(decision, 0)
                apply_neighbor_updates(neighbor, context=context, tags=tags, reason=decision.reason)
            elif decision.action == "strengthen_link":
                append_evolution(
                    neighbor,
                    {
                        "action": "strengthen",
                        "reason": decision.reason,
                        "links": [entry_id],
                    },
                )

        if decision.action == "update_existing" and decision.matched_entry_id and decision.matched_entry_id in store:
            neighbor = store[decision.matched_entry_id]
            append_evolution(
                neighbor,
                {
                    "action": "update_existing",
                    "reason": decision.reason,
                    "content": decision.updated_text or entry.content,
                },
            )
            if decision.metadata_updates:
                context, tags = _extract_neighbor_updates(decision, 0)
                apply_neighbor_updates(neighbor, context=context, tags=tags, reason=decision.reason)
            neighbor.content = decision.updated_text or entry.content

        save_store(store, root)
    except Exception as exc:
        error = str(exc)
        changed = False
        save_store(store, root)

    audit_path = append_audit_log(
        entry=entry,
        candidates=candidates,
        decision=decision,
        changed=changed,
        root=root,
        error=error,
    )
    return MemoryUpdateResult(
        entry=entry,
        candidates=candidates,
        decision=decision,
        changed=changed,
        audit_path=str(audit_path),
        error=error,
    )


def preview_memory_entry(
    entry: AgenticMemoryEntry,
    *,
    base_dir: Path | str | None = None,
    root: Path | str | None = None,
    judge: JudgeFn | None = None,
    top_k: int = 10,
    force_embed: bool = False,
) -> MemoryUpdateResult:
    return process_memory_entry(
        entry,
        base_dir=base_dir,
        root=root,
        judge=judge,
        top_k=top_k,
        apply=False,
        force_embed=force_embed,
    )
