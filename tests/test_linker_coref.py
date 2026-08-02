from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory

from tools.llm_wiki.api import wiki_log_co_reference
from tools.llm_wiki.linker_coref import link_co_referenced
from tools.llm_wiki.models import WikiPage


class LinkerCorefTests(unittest.TestCase):
    def test_link_co_referenced_requires_min_occurrences(self) -> None:
        with TemporaryDirectory() as tmpdir:
            wiki_log_co_reference(
                pages=["topics/a.md", "topics/b.md"],
                query_intent="single occurrence",
                root=tmpdir,
            )
            pages = [
                WikiPage(page_id="a", page_type="topics", title="A", path="topics/a.md", summary=""),
                WikiPage(page_id="b", page_type="topics", title="B", path="topics/b.md", summary=""),
            ]
            result = link_co_referenced(pages, root=tmpdir)
            self.assertFalse(any(link.relation == "co_referenced" for page in result for link in page.links))

    def test_link_co_referenced_creates_bidirectional_links(self) -> None:
        with TemporaryDirectory() as tmpdir:
            for intent in ("first", "second"):
                wiki_log_co_reference(
                    pages=["topics/a.md", "topics/b.md"],
                    query_intent=intent,
                    root=tmpdir,
                )
            pages = [
                WikiPage(page_id="a", page_type="topics", title="A", path="topics/a.md", summary=""),
                WikiPage(page_id="b", page_type="topics", title="B", path="topics/b.md", summary=""),
            ]
            result = link_co_referenced(pages, root=tmpdir)
            links_a = [link for link in result[0].links if link.relation == "co_referenced"]
            links_b = [link for link in result[1].links if link.relation == "co_referenced"]
            self.assertEqual(1, len(links_a))
            self.assertEqual(1, len(links_b))
            self.assertEqual("topics/b.md", links_a[0].target_path)
            self.assertEqual("topics/a.md", links_b[0].target_path)


if __name__ == "__main__":
    unittest.main()
