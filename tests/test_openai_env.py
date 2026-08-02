from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import tools.openai_env as openai_env
from tools.openai_env import load_repo_dotenv


class OpenAIEnvTests(unittest.TestCase):
    def test_load_repo_dotenv_reads_repo_env_file(self) -> None:
        load_repo_dotenv.cache_clear()
        fixture_root = openai_env.REPO_ROOT / "tests" / "fixtures" / "openai_env_repo"
        dotenv_path = fixture_root / ".env"
        dotenv_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
        with patch.object(openai_env, "REPO_ROOT", fixture_root):
            load_repo_dotenv.cache_clear()
            with patch.dict(os.environ, {}, clear=True):
                load_repo_dotenv()
                self.assertTrue(os.environ.get("OPENAI_API_KEY"))
        dotenv_path.unlink()

    def tearDown(self) -> None:
        load_repo_dotenv.cache_clear()


if __name__ == "__main__":
    unittest.main()
