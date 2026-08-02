from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from tools.agentic_memory.api import process_memory_entry
from tools.agentic_memory.models import AgenticMemoryEntry


def _write_memory_file(path: Path, title: str, section: str, bullets: list[str]) -> None:
    lines = [
        f"# {title}",
        "",
        "最終更新: 2026-07-01",
        "",
        f"## {section}",
        "",
    ]
    lines.extend(f"- {bullet}" for bullet in bullets)
    lines.extend(["", "---", "", "## 変更履歴", "", "| 日付 | 変更内容 |", "|------|----------|"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class AgenticMemoryPhase4Tests(unittest.TestCase):
    def test_strengthen_link_persists_note_metadata(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base = root / "memories"
            _write_memory_file(base / "preferences.md", "Preferences", "技術的な好み", ["Python を主軸にする"])
            _write_memory_file(base / "facts.md", "Facts", "基本情報", ["サンプル地域に住んでいる"])
            _write_memory_file(base / "decisions.md", "Decisions", "技術・設計", ["Issue 中心で運用する"])

            entry = AgenticMemoryEntry(
                content="AI ワークフロー設計も重視する",
                memory_type="preferences",
                target_section="技術的な好み",
                keywords=["AI", "workflow"],
                tags=["ai", "workflow"],
                context="AI workflow design",
            )
            candidate_embeddings = [
                np.array([1.0] + [0.0] * 1535, dtype=np.float32),
                np.array([0.1, 0.9] + [0.0] * 1534, dtype=np.float32),
                np.array([0.0, 1.0] + [0.0] * 1534, dtype=np.float32),
            ]
            query_embedding = [np.array([1.0] + [0.0] * 1535, dtype=np.float32)]

            def judge(_: AgenticMemoryEntry, candidates):
                return {
                    "action": "strengthen_link",
                    "matched_entry_id": candidates[0].entry_id,
                    "reason": "related preference",
                }

            with patch("tools.agentic_memory.retrieval.get_embeddings", side_effect=[candidate_embeddings, query_embedding]):
                result = process_memory_entry(entry, base_dir=base, root=root, judge=judge)

            self.assertFalse(result.changed)
            store_path = root / "indexes" / "agentic_memory_store.json"
            store = json.loads(store_path.read_text(encoding="utf-8"))
            entry_note = next(note for key, note in store.items() if key.startswith("memories:preferences:"))
            self.assertEqual("AI workflow design", entry_note["context"])
            self.assertEqual(["ai", "workflow"], entry_note["tags"])
            self.assertGreaterEqual(entry_note["retrieval_count"], 0)
            self.assertGreaterEqual(len(entry_note["links"]), 1)
            self.assertGreaterEqual(len(entry_note["evolution_history"]), 1)

    def test_update_neighbor_applies_context_and_tags(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base = root / "memories"
            _write_memory_file(base / "preferences.md", "Preferences", "技術的な好み", ["Python を主軸にする"])
            _write_memory_file(base / "facts.md", "Facts", "基本情報", ["サンプル地域に住んでいる"])
            _write_memory_file(base / "decisions.md", "Decisions", "技術・設計", ["Issue 中心で運用する"])

            entry = AgenticMemoryEntry(
                content="AI ワークフロー設計も重視する",
                memory_type="preferences",
                target_section="技術的な好み",
                context="new entry context",
                tags=["entry-tag"],
            )
            candidate_embeddings = [
                np.array([1.0] + [0.0] * 1535, dtype=np.float32),
                np.array([0.1, 0.9] + [0.0] * 1534, dtype=np.float32),
                np.array([0.0, 1.0] + [0.0] * 1534, dtype=np.float32),
            ]
            query_embedding = [np.array([1.0] + [0.0] * 1535, dtype=np.float32)]

            def judge(_: AgenticMemoryEntry, candidates):
                return {
                    "actions": ["update_neighbor"],
                    "suggested_connections": [candidates[0].entry_id],
                    "new_context_neighborhood": ["updated neighbor context"],
                    "new_tags_neighborhood": [["python", "agent"]],
                    "reason": "neighbor should evolve",
                }

            with patch("tools.agentic_memory.retrieval.get_embeddings", side_effect=[candidate_embeddings, query_embedding]):
                result = process_memory_entry(entry, base_dir=base, root=root, judge=judge)

            store_path = root / "indexes" / "agentic_memory_store.json"
            store = json.loads(store_path.read_text(encoding="utf-8"))
            neighbor_key = result.decision.matched_entry_id
            neighbor = store[neighbor_key]
            self.assertEqual("updated neighbor context", neighbor["context"])
            self.assertEqual(["python", "agent"], neighbor["tags"])
            self.assertGreaterEqual(neighbor["retrieval_count"], 1)
            self.assertGreaterEqual(len(neighbor["evolution_history"]), 1)


if __name__ == "__main__":
    unittest.main()
