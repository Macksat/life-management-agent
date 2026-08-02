from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools.llm_wiki.api import wiki_log_co_reference
from tools.llm_wiki.linker_serendipity import _find_candidates, link_serendipity
from tools.llm_wiki.models import WikiPage


class LinkerSerendipityTests(unittest.TestCase):
    def test_find_candidates_filters_same_category(self) -> None:
        with TemporaryDirectory() as tmpdir:
            wiki_log_co_reference(
                pages=["topics/a.md", "topics/b.md", "people_self/p.md"],
                query_intent="cross category",
                root=tmpdir,
            )
            wiki_log_co_reference(
                pages=["topics/a.md", "topics/b.md"],
                query_intent="same category",
                root=tmpdir,
            )
            pages = [
                WikiPage(page_id="a", page_type="topics", title="A", path="topics/a.md", summary="", tags=["work"]),
                WikiPage(page_id="b", page_type="topics", title="B", path="topics/b.md", summary="", tags=["work"]),
                WikiPage(page_id="p", page_type="people_self", title="P", path="people_self/p.md", summary="", tags=["life"]),
            ]
            candidates = _find_candidates(pages, root=tmpdir)
            pairs = {tuple(sorted((left.path, right.path))) for left, right, _ in candidates}
            self.assertIn(("people_self/p.md", "topics/a.md"), pairs)
            self.assertNotIn(("topics/a.md", "topics/b.md"), pairs)

    def test_link_serendipity_uses_cache(self) -> None:
        with TemporaryDirectory() as tmpdir:
            indexes = Path(tmpdir) / "indexes"
            indexes.mkdir(parents=True, exist_ok=True)
            (indexes / "serendipity_cache.json").write_text(
                json.dumps({"a||b": "cached bridge"}, ensure_ascii=False),
                encoding="utf-8",
            )
            pages = [
                WikiPage(page_id="a", page_type="topics", title="A", path="topics/a.md", summary="", tags=["work"]),
                WikiPage(page_id="b", page_type="people_self", title="B", path="people_self/b.md", summary="", tags=["life"]),
            ]
            with patch("tools.llm_wiki.linker_serendipity._find_candidates", return_value=[(pages[0], pages[1], "co_ref")]):
                with patch("tools.llm_wiki.linker_serendipity._ask_llm_for_bridge") as ask_mock:
                    result = link_serendipity(pages, root=tmpdir, use_llm=True)
            ask_mock.assert_not_called()
            links = [link for page in result for link in page.links if link.relation == "serendipity"]
            self.assertEqual(2, len(links))


if __name__ == "__main__":
    unittest.main()
