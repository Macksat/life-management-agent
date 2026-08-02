from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from tools.llm_wiki.api import wiki_log_co_reference
from tools.llm_wiki.compiler import build_wiki


class BuildWithLayersTests(unittest.TestCase):
    def test_build_wiki_with_all_layers(self) -> None:
        fake_embeddings = []
        for idx in range(35):
            vec = np.zeros(1536, dtype=np.float32)
            vec[0] = 1.0
            vec[min(idx + 1, 1535)] = 0.05
            fake_embeddings.append(vec)

        with TemporaryDirectory() as tmpdir:
            wiki_root = Path(tmpdir)
            wiki_log_co_reference(
                pages=["topics/design-notes.md", "people_self/preferences.md"],
                query_intent="cross-layer usage",
                root=wiki_root,
            )
            wiki_log_co_reference(
                pages=["topics/design-notes.md", "people_self/preferences.md"],
                query_intent="cross-layer usage again",
                root=wiki_root,
            )
            with patch("tools.llm_wiki.embedder.get_embeddings", return_value=fake_embeddings):
                with patch("tools.llm_wiki.linker_serendipity._ask_llm_for_bridge", return_value="抽象化と再利用"):
                    result = build_wiki(
                        root=wiki_root,
                        enable_semantic_links=True,
                        enable_serendipity=True,
                        use_llm=True,
                    )

            self.assertGreaterEqual(result["l2_similar_to_links"], 0)
            self.assertGreaterEqual(result["l3_co_referenced_links"], 2)
            self.assertGreaterEqual(result["l4_serendipity_links"], 2)

            graph = json.loads((wiki_root / "indexes" / "graph.json").read_text(encoding="utf-8"))
            all_relations = {
                link["relation"]
                for links in graph.values()
                for link in links
            }
            self.assertIn("similar_to", all_relations)
            self.assertIn("co_referenced", all_relations)
            self.assertIn("serendipity", all_relations)


if __name__ == "__main__":
    unittest.main()
