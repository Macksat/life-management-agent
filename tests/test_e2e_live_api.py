from __future__ import annotations

import contextlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openai import APIConnectionError

from tools.llm_wiki.api import wiki_log_co_reference
from tools.llm_wiki.compiler import build_wiki

class LiveApiE2ETests(unittest.TestCase):
    def test_build_wiki_with_live_openai_api(self) -> None:
        with TemporaryDirectory() as tmpdir:
            wiki_root = Path(tmpdir)
            wiki_log_co_reference(
                pages=["topics/design-notes.md", "people_self/preferences.md"],
                query_intent="live api e2e",
                root=wiki_root,
            )
            wiki_log_co_reference(
                pages=["topics/design-notes.md", "people_self/preferences.md"],
                query_intent="live api e2e repeated",
                root=wiki_root,
            )
            wiki_log_co_reference(
                pages=["people_self/user_context.md", "people_self/preferences.md"],
                query_intent="live api e2e style",
                root=wiki_root,
            )
            wiki_log_co_reference(
                pages=["people_self/user_context.md", "people_self/preferences.md"],
                query_intent="live api e2e style repeated",
                root=wiki_root,
            )

            try:
                result = build_wiki(
                    root=wiki_root,
                    enable_semantic_links=True,
                    enable_serendipity=True,
                    use_llm=True,
                )
            except APIConnectionError as exc:
                self.skipTest(f"live OpenAI API is not reachable: {exc}")

            self.assertGreater(result["l2_similar_to_links"], 0)
            self.assertGreater(result["l3_co_referenced_links"], 0)
            self.assertGreaterEqual(result["l4_serendipity_links"], 0)

            indexes = wiki_root / "indexes"
            self.assertTrue((indexes / "embeddings.npz").exists())
            self.assertTrue((indexes / "embeddings_meta.json").exists())
            self.assertTrue((indexes / "similarity_cache.json").exists())
            self.assertTrue((indexes / "serendipity_cache.json").exists())
            serendipity_cache = json.loads((indexes / "serendipity_cache.json").read_text(encoding="utf-8"))
            self.assertGreater(len(serendipity_cache), 0)

            graph = json.loads((indexes / "graph.json").read_text(encoding="utf-8"))
            relations = {
                link["relation"]
                for links in graph.values()
                for link in links
            }
            self.assertIn("similar_to", relations)
            self.assertIn("co_referenced", relations)
            if result["l4_serendipity_links"] > 0:
                self.assertIn("serendipity", relations)


if __name__ == "__main__":
    unittest.main()
