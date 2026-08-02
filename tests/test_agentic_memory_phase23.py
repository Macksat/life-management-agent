from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from tools.agentic_memory.api import process_memory_entry
from tools.agentic_memory.models import AgenticMemoryEntry


def _write_digest(path: Path, title: str, topic: str, insight: str) -> None:
    lines = [
        f"# {title}",
        "",
        "## 主要トピック",
        "",
        f"- {topic}",
        "",
        "## 重要な洞察・気づき",
        "",
        f"- {insight}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_conversation_daily(path: Path, heading: str, summary: str) -> None:
    lines = [
        "# Daily Conversation Memory",
        "",
        "date: 2026-07-07",
        "source_agents: Codex",
        "",
        "## Sessions",
        "",
        f"### {heading}",
        "",
        f"- summary: {summary}",
        "",
        "## Day Summary",
        "",
        "- key_topics:",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


class AgenticMemoryPhase23Tests(unittest.TestCase):
    def test_second_brain_update_existing_rewrites_digest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            digest_dir = root / "second_brain"
            digest_path = digest_dir / "digests" / "2026-07-07_profile.md"
            _write_digest(digest_path, "キャリアプロフィール", "AI エンジニア像の整理", "バックエンド設計を強みとする")
            memory_dir = root / "memories"
            _write_memory_file(memory_dir / "preferences.md", "Preferences", "技術的な好み", ["Python を主軸にする"])
            _write_memory_file(memory_dir / "facts.md", "Facts", "基本情報", ["サンプル地域に住んでいる"])
            _write_memory_file(memory_dir / "decisions.md", "Decisions", "技術・設計", ["Issue 中心で運用する"])

            entry = AgenticMemoryEntry(
                content="# キャリアプロフィール\n\n## 主要トピック\n\n- AI エンジニア像の整理\n\n## 重要な洞察・気づき\n\n- AI ワークフロー設計も強みとする",
                layer="second_brain",
                memory_type="second_brain",
                target_section="重要な洞察・気づき",
                source_path=str(digest_path),
            )
            candidate_embeddings = [
                np.array([1.0] + [0.0] * 1535, dtype=np.float32),
                np.array([0.1, 0.9] + [0.0] * 1534, dtype=np.float32),
                np.array([0.0, 1.0] + [0.0] * 1534, dtype=np.float32),
                np.array([0.0, 0.8, 0.2] + [0.0] * 1533, dtype=np.float32),
            ]
            query_embedding = [np.array([1.0] + [0.0] * 1535, dtype=np.float32)]

            def judge(_: AgenticMemoryEntry, candidates):
                digest_candidate = next(candidate for candidate in candidates if candidate.layer == "second_brain")
                return {
                    "action": "update_existing",
                    "matched_entry_id": digest_candidate.entry_id,
                    "target_path": str(digest_path),
                    "target_section": "重要な洞察・気づき",
                    "updated_text": "- AI ワークフロー設計も強みとする",
                    "reason": "refresh digest insight",
                }

            with patch("tools.agentic_memory.retrieval.get_embeddings", side_effect=[candidate_embeddings, query_embedding]):
                result = process_memory_entry(entry, base_dir=digest_dir, root=root, judge=judge)

            self.assertTrue(result.changed)
            updated = digest_path.read_text(encoding="utf-8")
            self.assertIn("- AI ワークフロー設計も強みとする", updated)

        # audit file should exist and capture update
            audit = root / "indexes" / "agentic_memory_decisions.jsonl"
            self.assertTrue(audit.exists())
            record = json.loads(audit.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual("update_existing", record["decision"]["action"])

    def test_conversation_memory_add_new_inserts_session(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            convo_dir = root / "conversation_memory"
            daily_path = convo_dir / "daily" / "2026" / "2026-07-07.md"
            _write_conversation_daily(daily_path, "2026-07-07 Existing Session", "既存セッション")
            memory_dir = root / "memories"
            _write_memory_file(memory_dir / "preferences.md", "Preferences", "技術的な好み", ["Python を主軸にする"])
            _write_memory_file(memory_dir / "facts.md", "Facts", "基本情報", ["サンプル地域に住んでいる"])
            _write_memory_file(memory_dir / "decisions.md", "Decisions", "技術・設計", ["Issue 中心で運用する"])

            entry = AgenticMemoryEntry(
                content="- summary: ユーザーは A-MEM の Phase 3 実装を依頼した。\n- decisions:\n  - conversation_memory に A-MEM を適用する。",
                layer="conversation_memory",
                memory_type="conversation_memory",
                target_section="2026-07-07 A-MEM Phase 3",
                source_path=str(daily_path),
            )
            candidate_embeddings = [
                np.array([0.2, 0.8] + [0.0] * 1534, dtype=np.float32),
                np.array([0.0, 1.0] + [0.0] * 1534, dtype=np.float32),
                np.array([1.0] + [0.0] * 1535, dtype=np.float32),
                np.array([0.7, 0.3] + [0.0] * 1534, dtype=np.float32),
                np.array([0.3, 0.7] + [0.0] * 1534, dtype=np.float32),
            ]
            query_embedding = [np.array([1.0] + [0.0] * 1535, dtype=np.float32)]

            def judge(_: AgenticMemoryEntry, __):
                return {
                    "action": "add_new",
                    "target_path": str(daily_path),
                    "target_section": "2026-07-07 A-MEM Phase 3",
                    "updated_text": entry.content,
                    "reason": "new session worth recording",
                }

            with patch("tools.agentic_memory.retrieval.get_embeddings", side_effect=[candidate_embeddings, query_embedding]):
                result = process_memory_entry(entry, base_dir=convo_dir, root=root, judge=judge)

            self.assertTrue(result.changed)
            updated = daily_path.read_text(encoding="utf-8")
            self.assertIn("### 2026-07-07 A-MEM Phase 3", updated)
            self.assertIn("A-MEM の Phase 3 実装を依頼した", updated)


if __name__ == "__main__":
    unittest.main()
