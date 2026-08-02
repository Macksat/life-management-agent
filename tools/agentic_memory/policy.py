"""Decision policy for A-MEM style source updates."""

from __future__ import annotations

from typing import Any, Callable

from .models import AgenticMemoryEntry, MemoryCandidate, MemoryDecision

JudgeFn = Callable[[AgenticMemoryEntry, list[MemoryCandidate]], MemoryDecision | dict[str, Any]]

VALID_ACTIONS = {"add_new", "update_existing", "skip_duplicate", "strengthen_link", "update_neighbor"}


def heuristic_decision(
    entry: AgenticMemoryEntry,
    candidates: list[MemoryCandidate],
) -> MemoryDecision:
    if not candidates:
        return MemoryDecision(
            action="add_new",
            target_path="",
            target_section=entry.target_section,
            reason="no similar candidates found",
            updated_text=entry.content,
        )

    top = candidates[0]
    same_layer = top.layer == entry.layer
    if same_layer and top.similarity >= 0.97:
        return MemoryDecision(
            action="skip_duplicate",
            target_path=top.source_path,
            target_section=top.section_name or entry.target_section,
            reason=f"top candidate is near-duplicate ({top.similarity:.3f})",
            matched_entry_id=top.entry_id,
            matched_text=top.text,
            similarity=top.similarity,
        )
    if same_layer and top.similarity >= 0.82:
        return MemoryDecision(
            action="update_existing",
            target_path=top.source_path,
            target_section=top.section_name or entry.target_section,
            reason=f"top candidate is similar enough to update ({top.similarity:.3f})",
            matched_entry_id=top.entry_id,
            matched_text=top.text,
            updated_text=entry.content,
            similarity=top.similarity,
        )
    if top.similarity >= 0.65:
        return MemoryDecision(
            action="strengthen_link",
            target_path=entry.source_path or top.source_path,
            target_section=entry.target_section,
            reason=f"candidate is related but not similar enough to overwrite ({top.similarity:.3f})",
            matched_entry_id=top.entry_id,
            matched_text=top.text,
            link_targets=[top.entry_id],
            similarity=top.similarity,
        )
    return MemoryDecision(
        action="add_new",
        target_path="",
        target_section=entry.target_section,
        reason=f"top similarity too low ({top.similarity:.3f})",
        updated_text=entry.content,
        similarity=top.similarity,
    )


def _normalize_judged_decision(
    raw: MemoryDecision | dict[str, Any],
    *,
    entry: AgenticMemoryEntry,
    candidates: list[MemoryCandidate],
) -> MemoryDecision:
    if isinstance(raw, MemoryDecision):
        decision = raw
    else:
        if "actions" in raw:
            actions = [str(item).strip() for item in raw.get("actions", [])]
            action = "update_neighbor" if "update_neighbor" in actions else (
                "strengthen_link" if "strengthen" in actions else str(raw.get("action", "")).strip()
            )
            raw = {
                "action": action,
                "matched_entry_id": (raw.get("suggested_connections") or [""])[0] if actions else raw.get("matched_entry_id", ""),
                "reason": raw.get("reason", "llm evolution decision"),
                "metadata_updates": {
                    "tags_to_update": list(raw.get("tags_to_update", [])),
                    "new_context_neighborhood": list(raw.get("new_context_neighborhood", [])),
                    "new_tags_neighborhood": list(raw.get("new_tags_neighborhood", [])),
                },
                "similarity": raw.get("similarity", 0.0),
            }
        action = str(raw.get("action", "")).strip()
        if action not in VALID_ACTIONS:
            raise ValueError(f"Unsupported action: {action}")
        matched_entry_id = str(raw.get("matched_entry_id", "")).strip()
        matched = next((candidate for candidate in candidates if candidate.entry_id == matched_entry_id), None)
        if matched is None and candidates and action in {"update_existing", "skip_duplicate", "strengthen_link", "update_neighbor"}:
            matched = candidates[0]
        decision = MemoryDecision(
            action=action,
            target_path=str(raw.get("target_path", matched.source_path if matched else "")).strip(),
            target_section=str(raw.get("target_section", matched.section_name if matched else entry.target_section)).strip(),
            reason=str(raw.get("reason", "llm decision")).strip(),
            matched_entry_id=matched.entry_id if matched else matched_entry_id,
            matched_text=matched.text if matched else str(raw.get("matched_text", "")).strip(),
            updated_text=str(raw.get("updated_text", entry.content)).strip(),
            link_targets=list(raw.get("link_targets", [matched.entry_id] if matched and action in {"strengthen_link", "update_neighbor"} else [])),
            metadata_updates=dict(raw.get("metadata_updates", {})),
            similarity=float(raw.get("similarity", matched.similarity if matched else 0.0)),
        )

    if decision.action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported action: {decision.action}")
    if not decision.target_section:
        decision.target_section = entry.target_section
    if decision.action == "add_new" and not decision.updated_text:
        decision.updated_text = entry.content
    return decision


def decide_memory_action(
    entry: AgenticMemoryEntry,
    candidates: list[MemoryCandidate],
    *,
    judge: JudgeFn | None = None,
) -> MemoryDecision:
    if judge is None:
        return heuristic_decision(entry, candidates)

    try:
        raw = judge(entry, candidates)
        return _normalize_judged_decision(raw, entry=entry, candidates=candidates)
    except Exception:
        return heuristic_decision(entry, candidates)
