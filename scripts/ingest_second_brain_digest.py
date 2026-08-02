#!/usr/bin/env python3
"""Register a second_brain digest through the A-MEM pipeline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools.agentic_memory.api import process_memory_entry
from tools.agentic_memory.models import AgenticMemoryEntry
from tools.agentic_memory.retrieval import EMBEDDING_DIM
from tools.llm_wiki.paths import DEFAULT_WIKI_ROOT, REPO_ROOT


def _rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _extract_date(path: Path) -> str:
    match = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
    return match.group(1) if match else ""


def _split_tags(raw: str) -> list[str]:
    return [part.lstrip("#") for part in re.split(r"[\s,]+", raw.strip()) if part.strip()]


def _keywords_from_title(title: str) -> list[str]:
    parts = [item.strip() for item in re.split(r"[\/:\-\s（）()]+", title) if item.strip()]
    return list(dict.fromkeys(parts[:8]))


def _update_index(index_path: Path, *, digest_date: str, title: str, tags: str, filename: str) -> bool:
    if not index_path.exists():
        lines = [
            "# Second Brain ダイジェスト索引",
            "",
            "| 日付 | タイトル | テーマタグ | ファイル |",
            "|---|---|---|---|",
        ]
    else:
        lines = index_path.read_text(encoding="utf-8").splitlines()

    row = f"| {digest_date} | {title} | {tags} | {filename} |"
    updated = False
    replaced = False
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped == row:
            if not replaced:
                new_lines.append(row)
                replaced = True
            continue
        if stripped.startswith(f"| {digest_date} | {title} |") or stripped.endswith(f"| {filename} |"):
            if not replaced:
                new_lines.append(row)
                replaced = True
                updated = True
            else:
                updated = True
            continue
        new_lines.append(line)

    if not replaced:
        new_lines.append(row)
        updated = True

    index_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return updated


def _update_processed(processed_path: Path, source_file: str) -> bool:
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    if processed_path.exists():
        existing = {
            line.strip()
            for line in processed_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    if source_file in existing:
        return False
    with processed_path.open("a", encoding="utf-8") as fh:
        fh.write(source_file)
        fh.write("\n")
    return True


def _ingest_judge(target_path: Path):
    target_path_str = _rel_path(target_path)

    def judge(entry: AgenticMemoryEntry, candidates):
        self_candidate = next(
            (
                candidate
                for candidate in candidates
                if candidate.layer == "second_brain" and candidate.source_path == target_path_str
            ),
            None,
        )
        related = [
            candidate
            for candidate in candidates
            if candidate.entry_id != (self_candidate.entry_id if self_candidate else "")
        ]
        link_targets = [candidate.entry_id for candidate in related[:3] if candidate.similarity >= 0.65]
        matched = related[0] if related else None

        return {
            "action": "update_existing" if target_path.exists() else "add_new",
            "target_path": target_path_str,
            "target_section": entry.target_section,
            "reason": "register second_brain digest through A-MEM",
            "matched_entry_id": matched.entry_id if matched else "",
            "updated_text": entry.content,
            "link_targets": link_targets,
            "similarity": matched.similarity if matched else 0.0,
        }

    return judge


def ingest_second_brain_digest(
    digest_path: Path | str,
    *,
    source_file: str = "",
    tags: str = "",
    title: str = "",
    digest_date: str = "",
    root: Path | str | None = None,
    force_embed: bool = False,
) -> dict[str, object]:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    second_brain_dir = wiki_root / "sources" / "second_brain"
    digest_path = Path(digest_path)
    content = digest_path.read_text(encoding="utf-8")

    inferred_title = _extract_title(content, digest_path.stem)
    final_title = title or inferred_title
    final_date = digest_date or _extract_date(digest_path)
    final_tags = tags.strip()

    entry = AgenticMemoryEntry(
        content=content,
        layer="second_brain",
        memory_type="second_brain",
        target_section="",
        source_path=_rel_path(digest_path),
        summary=final_title,
        keywords=_keywords_from_title(final_title),
        tags=_split_tags(final_tags),
        context=final_title,
    )
    result = process_memory_entry(
        entry,
        base_dir=second_brain_dir,
        root=wiki_root,
        judge=_ingest_judge(digest_path),
        top_k=10,
        force_embed=force_embed,
    )

    index_updated = _update_index(
        second_brain_dir / "index.md",
        digest_date=final_date,
        title=final_title,
        tags=final_tags,
        filename=digest_path.name,
    )
    processed_updated = False
    if source_file:
        processed_updated = _update_processed(second_brain_dir / ".processed", source_file)

    return {
        "digest_path": str(digest_path),
        "title": final_title,
        "date": final_date,
        "tags": final_tags,
        "embedding_dim": EMBEDDING_DIM,
        "changed": result.changed,
        "decision": result.decision.to_dict(),
        "audit_path": result.audit_path,
        "store_updated": True,
        "index_updated": index_updated,
        "processed_updated": processed_updated,
        "error": result.error,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a second_brain digest through A-MEM")
    parser.add_argument("digest_path", help="Path to the digest markdown file")
    parser.add_argument("--source-file", default="", help="Original raw file name to append to .processed")
    parser.add_argument("--tags", default="", help="Theme tags for second_brain/index.md")
    parser.add_argument("--title", default="", help="Optional digest title override")
    parser.add_argument("--date", default="", help="Optional digest date override (YYYY-MM-DD)")
    parser.add_argument("--root", default=None, help="Wiki root (default: data/llm_wiki)")
    parser.add_argument("--force-embed", action="store_true", help="Force rebuild A-MEM embeddings")
    args = parser.parse_args()

    result = ingest_second_brain_digest(
        args.digest_path,
        source_file=args.source_file,
        tags=args.tags,
        title=args.title,
        digest_date=args.date,
        root=args.root,
        force_embed=args.force_embed,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
