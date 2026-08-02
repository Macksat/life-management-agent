from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from tools.agentic_memory.models import AgenticMemoryEntry
from tools.agentic_memory.retrieval import load_memory_candidates, search_memory_candidates


def _write_memory_file(path: Path, title: str, section: str, bullets: list[str]) -> None:
    lines = [
        f"# {title}",
        "",
        "最終更新: 2026-07-07",
        "",
        f"## {section}",
        "",
    ]
    lines.extend(f"- {bullet}" for bullet in bullets)
    lines.extend(
        [
            "",
            "---",
            "",
            "## 変更履歴",
            "",
            "| 日付 | 変更内容 |",
            "|------|----------|",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class AgenticMemoryRetrievalTests(unittest.TestCase):
    def test_search_memory_candidates_ranks_same_memory_type_only(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            _write_memory_file(
                base / "preferences.md",
                "Preferences",
                "技術的な好み",
                [
                    "Python を主軸にする",
                    "TypeScript も扱う",
                ],
            )
            _write_memory_file(
                base / "facts.md",
                "Facts",
                "基本情報",
                [
                    "サンプル地域に住んでいる",
                ],
            )
            _write_memory_file(base / "decisions.md", "Decisions", "技術・設計", ["Issue 中心で運用する"])

            entry = AgenticMemoryEntry(
                content="Python を主軸にしつつ AI エージェント開発を進める",
                memory_type="preferences",
                target_section="技術的な好み",
            )
            fake_embeddings = [
                np.array([1.0] + [0.0] * 1535, dtype=np.float32),
                np.array([0.9, 0.1] + [0.0] * 1534, dtype=np.float32),
                np.array([0.0, 1.0] + [0.0] * 1534, dtype=np.float32),
            ]
            query_embedding = [np.array([1.0] + [0.0] * 1535, dtype=np.float32)]

            with patch(
                "tools.agentic_memory.retrieval.get_embeddings",
                side_effect=[fake_embeddings, query_embedding],
            ):
                candidates = search_memory_candidates(entry, base_dir=base, root=base, top_k=10)

            self.assertEqual(2, len(candidates))
            self.assertTrue(all(candidate.memory_type == "preferences" for candidate in candidates))
            self.assertGreaterEqual(candidates[0].similarity, candidates[1].similarity)

    def test_load_memory_candidates_uses_expected_sections(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            _write_memory_file(base / "preferences.md", "Preferences", "作業パターン", ["まず構造を整理してから進める"])
            _write_memory_file(base / "facts.md", "Facts", "基本情報", ["GitHub Issue を一元管理している"])
            _write_memory_file(base / "decisions.md", "Decisions", "方針・戦略", ["資産形成は長期で進める"])
            candidates = load_memory_candidates(base)
            self.assertEqual(3, len(candidates))
            self.assertEqual({"preferences", "facts", "decisions"}, {item.memory_type for item in candidates})


if __name__ == "__main__":
    unittest.main()
