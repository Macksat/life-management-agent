"""OpenAI embedding helpers for LLMWiki."""

from __future__ import annotations

import numpy as np

from tools.openai_env import load_repo_dotenv

MODEL = "text-embedding-3-small"
DIMENSIONS = 1536
MAX_BATCH = 100


def get_embeddings(texts: list[str]) -> list[np.ndarray]:
    from openai import OpenAI

    if not texts:
        return []

    load_repo_dotenv()
    client = OpenAI()
    embeddings: list[np.ndarray] = []
    for start in range(0, len(texts), MAX_BATCH):
        batch = texts[start : start + MAX_BATCH]
        response = client.embeddings.create(input=batch, model=MODEL)
        for item in response.data:
            embeddings.append(np.array(item.embedding, dtype=np.float32))
    return embeddings
