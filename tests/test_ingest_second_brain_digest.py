from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from scripts.ingest_second_brain_digest import ingest_second_brain_digest


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


class IngestSecondBrainDigestTests(unittest.TestCase):
    def test_ingest_uses_agentic_memory_and_updates_indexes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "data" / "llm_wiki"
            second_brain = root / "sources" / "second_brain"
            digest = second_brain / "digests" / "2026-07-06_ai-lab.md"
            digest.parent.mkdir(parents=True, exist_ok=True)
            digest.write_text(
                "\n".join(
                    [
                        "# AIラボ技術研究コース第6回",
                        "",
                        "## 主要トピック",
                        "",
                        "- 強化学習ハンズオン",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            memories = root / "sources" / "memories"
            _write_memory_file(memories / "preferences.md", "Preferences", "技術的な好み", ["技術ブログで学びを共有する"])
            _write_memory_file(memories / "facts.md", "Facts", "基本情報", ["LLM の記憶設計に関心がある"])
            _write_memory_file(memories / "decisions.md", "Decisions", "技術・設計", ["Eval を重視する"])

            candidate_embeddings = [
                np.array([1.0] + [0.0] * 1535, dtype=np.float32),
                np.array([0.0, 1.0] + [0.0] * 1534, dtype=np.float32),
                np.array([0.5, 0.5] + [0.0] * 1534, dtype=np.float32),
                np.array([0.9, 0.1] + [0.0] * 1534, dtype=np.float32),
            ]
            query_embedding = [np.array([1.0] + [0.0] * 1535, dtype=np.float32)]

            with patch("tools.agentic_memory.retrieval.get_embeddings", side_effect=[candidate_embeddings, query_embedding]):
                result = ingest_second_brain_digest(
                    digest,
                    source_file="AIラボ元メモ.pdf",
                    tags="#AIラボ #強化学習 #Eval",
                    root=root,
                )

            self.assertTrue(result["changed"])
            self.assertTrue((root / "indexes" / "agentic_memory_decisions.jsonl").exists())
            self.assertTrue((root / "indexes" / "agentic_memory_store.json").exists())

            index_text = (second_brain / "index.md").read_text(encoding="utf-8")
            self.assertIn("| 2026-07-06 | AIラボ技術研究コース第6回 | #AIラボ #強化学習 #Eval | 2026-07-06_ai-lab.md |", index_text)

            processed = (second_brain / ".processed").read_text(encoding="utf-8")
            self.assertIn("AIラボ元メモ.pdf", processed)

            audit_lines = (root / "indexes" / "agentic_memory_decisions.jsonl").read_text(encoding="utf-8").splitlines()
            audit = json.loads(audit_lines[0])
            self.assertEqual("update_existing", audit["decision"]["action"])
            self.assertEqual("second_brain", audit["entry"]["layer"])


if __name__ == "__main__":
    unittest.main()
