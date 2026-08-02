from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from scripts.backfill_agentic_memory import run_backfill


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


def _write_digest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# キャリアメモ\n\n## 主要トピック\n\n- AI エージェント設計\n\n## 重要な洞察・気づき\n\n- 設計も実装も行う\n",
        encoding="utf-8",
    )


def _write_conversation(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Daily Conversation Memory\n\ndate: 2026-07-07\nsource_agents: Codex\n\n## Sessions\n\n### A-MEM\n\n- summary: A-MEM を試した\n\n## Day Summary\n\n- key_topics:\n",
        encoding="utf-8",
    )


class BackfillAgenticMemoryTests(unittest.TestCase):
    def test_run_backfill_builds_store_and_audit(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "data" / "llm_wiki"
            memories = root / "sources" / "memories"
            second_brain = root / "sources" / "second_brain"
            conversation = root / "sources" / "conversation_memory"

            _write_memory_file(memories / "preferences.md", "Preferences", "技術的な好み", ["Python を主軸にする"])
            _write_memory_file(memories / "facts.md", "Facts", "基本情報", ["サンプル地域に住んでいる"])
            _write_memory_file(memories / "decisions.md", "Decisions", "技術・設計", ["Issue 中心で運用する"])
            _write_digest(second_brain / "digests" / "2026-07-07_note.md")
            (second_brain / "index.md").write_text("| 日付 | タイトル | テーマタグ | ファイル |\n|---|---|---|---|\n| 2026-07-07 | キャリアメモ | #ai #career | 2026-07-07_note.md |\n", encoding="utf-8")
            _write_conversation(conversation / "daily" / "2026" / "2026-07-07.md")

            def fake_build_candidate_embeddings(candidates, **_kwargs):
                embeddings = []
                for idx, _candidate in enumerate(candidates):
                    left = max(0.0, 1.0 - 0.05 * idx)
                    right = min(1.0, 0.05 * idx)
                    embeddings.append(np.array([left, right] + [0.0] * 1534, dtype=np.float32))
                return np.array(embeddings, dtype=np.float32), {}

            with patch("scripts.backfill_agentic_memory.build_candidate_embeddings", side_effect=fake_build_candidate_embeddings):
                result = run_backfill(root=root)

            self.assertGreaterEqual(result["processed"], 5)
            store = root / "indexes" / "agentic_memory_store.json"
            audit = root / "indexes" / "agentic_memory_decisions.jsonl"
            self.assertTrue(store.exists())
            self.assertTrue(audit.exists())
            payload = json.loads(store.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(payload), 5)


if __name__ == "__main__":
    unittest.main()
