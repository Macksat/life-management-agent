from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from tools.llm_wiki.linker_semantic import link_semantic
from tools.llm_wiki.models import WikiPage


class LinkerSemanticTests(unittest.TestCase):
    def test_link_semantic_adds_similar_to_links(self) -> None:
        pages = [
            WikiPage(
                page_id="topic-a",
                page_type="topics",
                title="キャリア設計",
                path="topics/career.md",
                summary="エンジニアのキャリアパスを考える",
            ),
            WikiPage(
                page_id="topic-b",
                page_type="topics",
                title="転職活動の進め方",
                path="topics/job-change.md",
                summary="転職の準備と面接対策",
            ),
        ]

        fake_embeddings = [
            np.array([1.0] + [0.0] * 1535, dtype=np.float32),
            np.array([0.9, 0.1] + [0.0] * 1534, dtype=np.float32),
        ]

        with TemporaryDirectory() as tmpdir:
            with patch("tools.llm_wiki.embedder.get_embeddings", return_value=fake_embeddings):
                result = link_semantic(pages, root=tmpdir)

        similar_links = [link for page in result for link in page.links if link.relation == "similar_to"]
        self.assertGreater(len(similar_links), 0)
        self.assertTrue(all(0.0 < link.confidence <= 1.0 for link in similar_links))


if __name__ == "__main__":
    unittest.main()
