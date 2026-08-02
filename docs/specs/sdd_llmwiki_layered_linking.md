# SDD: LLMWiki 4 層リンキングシステム

> **Status:** Draft
> **Author:** Claude Code
> **Date:** 2026-06-28
> **Depends on:** `docs/llm_wiki.md`（正本）

---

## 1. 背景と目的

### 1.1 現状の課題

現在の `linker.py` は **トークン集合の積（set intersection）** のみでリンクを生成している。

```python
# 現状のアルゴリズム（linker.py L61）
overlap = topic_tokens_set & token_cache[person.page_id]
confidence = min(0.95, 0.4 + 0.1 * len(overlap))
```

**限界:**
- 「転職」と「キャリアチェンジ」のような同義語・言い換えを拾えない
- 「料理の段取り」と「プロジェクト管理」のような異分野の構造的類似を発見できない
- リンクがビルド時の静的計算のみで、実際の使用パターンが反映されない

### 1.2 ゴール

4 層のリンキングを導入し、以下を実現する:

| レイヤー | 目的 | 生成タイミング |
|---|---|---|
| L1: 構造リンク | メタデータに基づく確実なリンク | ビルド時 |
| L2: 意味類似リンク | Embedding による類似ページの発見 | ビルド時 |
| L3: 共起リンク | 会話で実際に一緒に参照されたページの記録 | **会話時**（C 案） |
| L4: セレンディピティリンク | 異カテゴリ間の意外な接続の発見 | ビルド時（L3 データ活用） |

### 1.3 設計原則

- **既存の構造リンク（L1）は変更しない。** 新しいレイヤーを追加する形で拡張する
- **L3 の記録は会話中に Claude が明示的に行う（C 案）。** 検索ログの自動記録ではなく、実際に役立ったページだけを記録する
- **外部 API 不要でビルドできる。** L1/L2/L3 はローカルで完結。L4 のみオプションで LLM API を使用する
- **段階的に導入可能。** L1 → L2 → L3 → L4 の順に独立して実装できる

---

## 2. アーキテクチャ概要

### 2.1 全体フロー

```
┌─────────────────────────────────────────────────────────┐
│  会話時（リアルタイム）                                    │
│                                                         │
│  ユーザーが質問                                           │
│       ↓                                                 │
│  Claude が wiki_search / wiki_read で複数ページ参照        │
│       ↓                                                 │
│  回答を生成                                              │
│       ↓                                                 │
│  ★ wiki_log_co_reference() で共起を記録 ★                │
│       ↓                                                 │
│  co_references.jsonl に追記                               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  ビルド時（build_llm_wiki.py）                            │
│                                                         │
│  parse_all() → build_*_pages()                          │
│       ↓                                                 │
│  L1: link_structural()      ← 既存 linker.py の処理      │
│       ↓                                                 │
│  L2: link_semantic()        ← Embedding コサイン類似度    │
│       ↓                                                 │
│  L3: link_co_referenced()   ← co_references.jsonl 集計   │
│       ↓                                                 │
│  L4: link_serendipity()     ← L3 データ + LLM 抽象化     │
│       ↓                                                 │
│  validate → write                                       │
└─────────────────────────────────────────────────────────┘
```

### 2.2 ディレクトリ構成の変更

```diff
 data/llm_wiki/
   ├── sources/                  # 変更なし
   ├── pages/                    # 変更なし
   ├── indexes/
   │   ├── page_index.json       # 変更なし
   │   ├── alias_index.json      # 変更なし
   │   ├── graph.json            # 変更なし（新 relation が追加されるだけ）
+  │   ├── co_references.jsonl   # L3: 会話時の共起記録（append-only）
+  │   ├── embeddings.npz        # L2: ページ埋め込みベクトル（ページ単位キャッシュ）
+  │   ├── embeddings_meta.json  # L2: ページ→行番号+content_hash のマッピング
+  │   └── similarity_cache.json # L2/L4共用: ペアごとのコサイン類似度キャッシュ
   ├── error_book/               # 変更なし
   └── ...

 tools/llm_wiki/
   ├── linker.py                 # 変更: link_pages() を分割リファクタ
+  ├── linker_semantic.py        # 新規: L2 Embedding リンク
+  ├── linker_coref.py           # 新規: L3 共起リンク
+  ├── linker_serendipity.py     # 新規: L4 セレンディピティリンク
+  ├── embedder.py               # 新規: Embedding 生成・増分キャッシュ管理
   ├── models.py                 # 変更: CoReference モデル追加
   ├── api.py                    # 変更: wiki_log_co_reference() 追加
   ├── compiler.py               # 変更: 新リンカーの呼び出し追加
   └── ...
```

---

## 3. データモデルの変更

### 3.1 新規: `CoReference` データクラス

**ファイル:** `tools/llm_wiki/models.py` に追加

```python
@dataclass
class CoReference:
    """会話中に同時参照されたページ群の記録。"""

    pages: list[str]             # 同時に参照されたページの path リスト
    query_intent: str            # 何を解決しようとしたか（Claude が1行で要約）
    timestamp: str               # ISO 8601 形式（例: "2026-06-28T21:30:00+09:00"）
    conversation_id: str         # 会話セッション識別子（任意文字列）

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoReference":
        return cls(
            pages=list(data["pages"]),
            query_intent=data["query_intent"],
            timestamp=data["timestamp"],
            conversation_id=data.get("conversation_id", "unknown"),
        )
```

### 3.2 WikiLink.relation の追加値

既存の `relation` フィールドに以下の値を追加する。`WikiLink` のデータ構造自体は変更不要。

```python
# 既存（変更なし）
"index_of"           # L1: インデックス → 配下ページ
"relates_to"         # L1: トピック → people_self（トークン重複）
"mentions"           # L1: トピック → timeline（トークン重複）
"derived_from"       # L1: ページ → 元ソースファイル
"references_issue"   # L1: トピック → issue（トークン重複）
"relates_to_topic"   # L1: トピック ↔ トピック / issue → トピック
"child_of"           # L1: issue → 親プロジェクト
"parent_of"          # L1: プロジェクト → 子 issue
"related_issue"      # L1: issue → 関連 issue

# 新規追加
"similar_to"         # L2: Embedding コサイン類似度によるリンク
"co_referenced"      # L3: 会話中の共起によるリンク
"serendipity"        # L4: 異カテゴリ間の抽象的接続
```

### 3.3 WikiLink.source の新しいフォーマット

```python
# L2 の source 例
"embedding_cosine:0.73"

# L3 の source 例
"co_ref:5回, 代表: 認知リソース枯渇時の生活維持"

# L4 の source 例
"abstract_bridge: 依存タスクの並行スケジューリング"
```

---

## 4. レイヤー 1: 構造リンク（既存）

### 4.1 変更内容

`linker.py` の `link_pages()` 関数を **`link_structural()`** にリネームし、他のリンカーと並列で呼べるようにする。ロジック自体は変更なし。

### 4.2 リファクタリング手順

**ファイル:** `tools/llm_wiki/linker.py`

```python
"""Phase 1 LLMWiki linker — L1 構造リンク。"""

from __future__ import annotations
from collections import defaultdict
from .builders import topic_tokens
from .models import WikiLink, WikiPage


def _page_token_set(page: WikiPage) -> set[str]:
    pieces = [page.title, page.summary, *page.tags, *page.aliases]
    tokens: set[str] = set()
    for piece in pieces:
        tokens.update(topic_tokens(piece))
    return tokens


def _shared_source_paths(page: WikiPage) -> set[str]:
    return {ref.source_path for ref in page.source_refs}


def link_structural(pages: list[WikiPage]) -> list[WikiPage]:
    """L1: メタデータ・トークン重複ベースの構造リンク。既存 link_pages() と同一ロジック。"""
    # --- 以下、現在の link_pages() の中身をそのまま維持 ---
    ...  # 既存コード全体をここに移動


# 後方互換のエイリアス（既存の呼び出し元が壊れないように）
link_pages = link_structural
```

**変更理由:** 新リンカー（L2/L3/L4）と名前空間を分け、`compiler.py` から段階的に呼び出せるようにする。

---

## 5. レイヤー 2: 意味類似リンク（Embedding）

### 5.1 概要

`sentence-transformers`（インストール済み: v3.0.1）と `faiss-cpu`（インストール済み: v1.12.0）を使い、各ページの `title + summary + tags` を埋め込みベクトル化し、コサイン類似度でリンクを生成する。

### 5.2 増分キャッシュ戦略（コア設計）

**課題:** ページが増えるほどコサイン類似度の計算コストが増大する。全ページ N に対して類似度計算は O(N²)。ページ 1 つの追加・変更のたびに全ペア再計算するのは非効率。

**解決:** 2 層の増分キャッシュを導入し、**変更があったページに関わる計算だけを再実行する。**

```
キャッシュ層 1: ページ単位の Embedding キャッシュ
  embeddings_meta.json に各ページの content_hash を記録
  → 内容が変わっていないページは再 Embedding しない

キャッシュ層 2: ペア単位のコサイン類似度キャッシュ
  similarity_cache.json に (page_a, page_b) → similarity を記録
  → 両方のページが変わっていないペアは再計算しない
```

#### 計算量の改善効果

500 ページ中 10 ページが変更された場合:

| 処理 | キャッシュなし | キャッシュあり | 削減率 |
|---|---|---|---|
| Embedding 生成 | 500 回 | **10 回** | 98% |
| 類似度計算 | 124,750 ペア | **10×500 = 5,000 ペア** | 96% |
| FAISS 検索 | 全件再構築 | **変更ページのみ検索** | 96% |

#### キャッシュの判定フロー

```
ビルド開始
  ↓
各ページの content_hash を計算
  ↓
embeddings_meta.json と比較
  ↓
┌─────────────────────────────────────────────┐
│ ページ A の hash が一致 → Embedding 再利用     │
│ ページ B の hash が不一致 → Embedding 再計算    │
│ ページ C は新規 → Embedding 新規計算           │
│ ページ D はキャッシュにあるが今回不在 → 無視     │
└─────────────────────────────────────────────┘
  ↓
変更ページセット changed_ids = {B, C} を特定
  ↓
similarity_cache.json から既存ペアをロード
  ↓
┌──────────────────────────────────────────────────────────┐
│ ペア (A, E): 両方 unchanged → キャッシュの similarity を再利用 │
│ ペア (A, B): B が changed → コサイン類似度を再計算            │
│ ペア (B, C): 両方 changed → コサイン類似度を再計算            │
│ ペア (A, C): C が新規 → コサイン類似度を新規計算              │
│ ペア (A, D): D が今回不在 → キャッシュから削除               │
└──────────────────────────────────────────────────────────┘
  ↓
更新後の similarity_cache.json を保存
```

#### キャッシュファイルの構造

**`embeddings_meta.json`:**
```json
{
  "model": "all-MiniLM-L6-v2",
  "dim": 384,
  "pages": {
    "topic-career": {"content_hash": "a1b2c3d4", "row": 0},
    "topic-cooking": {"content_hash": "e5f6g7h8", "row": 1},
    "topic-life-admin": {"content_hash": "i9j0k1l2", "row": 2}
  }
}
```

- `row`: `embeddings.npz` 内の numpy 配列における行インデックス
- `content_hash`: `_page_content_hash()` で計算したページ固有のハッシュ

**`similarity_cache.json`:**
```json
{
  "topic-career||topic-cooking": {
    "similarity": 0.42,
    "hash_a": "a1b2c3d4",
    "hash_b": "e5f6g7h8"
  },
  "topic-career||topic-life-admin": {
    "similarity": 0.73,
    "hash_a": "a1b2c3d4",
    "hash_b": "i9j0k1l2"
  }
}
```

- キー: `sorted([page_id_a, page_id_b])` を `||` で結合（順序固定）
- `hash_a`, `hash_b`: 計算時点でのページの content_hash。どちらかが変わったら無効

### 5.3 新規ファイル: `tools/llm_wiki/embedder.py`

```python
"""LLMWiki ページ埋め込みの生成・増分キャッシュ管理。

キャッシュ戦略:
  層1 — ページ単位 Embedding キャッシュ（embeddings.npz + embeddings_meta.json）
       content_hash が一致するページは再 Embedding しない。
  層2 — ペア単位コサイン類似度キャッシュ（similarity_cache.json）
       両方のページの hash が一致するペアは再計算しない。
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import faiss
import numpy as np

from .models import WikiPage
from .paths import DEFAULT_WIKI_ROOT

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
EMBEDDINGS_FILE = "embeddings.npz"
EMBEDDINGS_META_FILE = "embeddings_meta.json"
SIMILARITY_CACHE_FILE = "similarity_cache.json"


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _page_text(page: WikiPage) -> str:
    """埋め込み対象テキストを構築する。"""
    parts = [page.title]
    if page.summary:
        parts.append(page.summary)
    if page.tags:
        parts.append(", ".join(page.tags))
    if page.key_facts:
        parts.append(". ".join(page.key_facts[:5]))
    return " ".join(parts)


def _page_content_hash(page: WikiPage) -> str:
    """単一ページの content hash（16 文字 hex）。"""
    return hashlib.sha256(_page_text(page).encode("utf-8")).hexdigest()[:16]


def _pair_key(id_a: str, id_b: str) -> str:
    """ペアキーを正規化（アルファベット順で || 結合）。"""
    a, b = sorted([id_a, id_b])
    return f"{a}||{b}"


def _cache_paths(root: Path | None) -> tuple[Path, Path, Path]:
    wiki_root = root or DEFAULT_WIKI_ROOT
    idx = wiki_root / "indexes"
    return idx / EMBEDDINGS_FILE, idx / EMBEDDINGS_META_FILE, idx / SIMILARITY_CACHE_FILE


# ---------------------------------------------------------------------------
# 層1: ページ単位 Embedding キャッシュ
# ---------------------------------------------------------------------------

def build_embeddings(
    pages: list[WikiPage],
    root: Path | None = None,
    force: bool = False,
) -> tuple[np.ndarray, list[str], set[str]]:
    """全ページの埋め込みベクトルを生成する（増分キャッシュ付き）。

    Returns:
        embeddings : np.ndarray (N, 384) — 正規化済み
        page_ids   : list[str] — embeddings の行順に対応する page_id リスト
        changed_ids: set[str]  — 今回新規 or 再計算されたページの page_id 集合
                                 （呼び出し元が類似度の差分更新に使う）
    """
    embed_path, meta_path, _ = _cache_paths(root)

    # --- 現在のページの hash を計算 ---
    current_hashes: dict[str, str] = {}
    page_by_id: dict[str, WikiPage] = {}
    for page in pages:
        current_hashes[page.page_id] = _page_content_hash(page)
        page_by_id[page.page_id] = page

    page_ids = [page.page_id for page in pages]

    # --- キャッシュ読み込み ---
    cached_meta: dict[str, dict] = {}  # page_id → {"content_hash", "row"}
    cached_embeddings: np.ndarray | None = None

    if not force and meta_path.exists() and embed_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        cached_meta = meta.get("pages", {})
        cached_embeddings = np.load(str(embed_path))["embeddings"]

    # --- 差分判定: どのページが変更されたか ---
    changed_ids: set[str] = set()
    reuse_map: dict[str, int] = {}  # page_id → キャッシュ内の row

    for pid in page_ids:
        cached = cached_meta.get(pid)
        if cached is None:
            # 新規ページ
            changed_ids.add(pid)
        elif cached["content_hash"] != current_hashes[pid]:
            # 内容が変わったページ
            changed_ids.add(pid)
        else:
            # 内容が同じ → キャッシュの Embedding を再利用
            reuse_map[pid] = cached["row"]

    # --- Embedding 構築 ---
    embeddings = np.zeros((len(pages), EMBEDDING_DIM), dtype=np.float32)

    # キャッシュから再利用
    for pid, cached_row in reuse_map.items():
        new_row = page_ids.index(pid)
        if cached_embeddings is not None and cached_row < len(cached_embeddings):
            embeddings[new_row] = cached_embeddings[cached_row]

    # 変更ページのみ再 Embedding
    pages_to_embed = [page_by_id[pid] for pid in changed_ids if pid in page_by_id]
    if pages_to_embed:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        texts = [_page_text(p) for p in pages_to_embed]
        new_vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        new_vectors = np.array(new_vectors, dtype=np.float32)

        for i, page in enumerate(pages_to_embed):
            row = page_ids.index(page.page_id)
            embeddings[row] = new_vectors[i]

    # --- キャッシュ保存 ---
    embed_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(str(embed_path), embeddings=embeddings)

    new_meta = {
        "model": EMBEDDING_MODEL_NAME,
        "dim": EMBEDDING_DIM,
        "pages": {
            pid: {"content_hash": current_hashes[pid], "row": idx}
            for idx, pid in enumerate(page_ids)
        },
    }
    meta_path.write_text(json.dumps(new_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return embeddings, page_ids, changed_ids


# ---------------------------------------------------------------------------
# 層2: ペア単位コサイン類似度キャッシュ
# ---------------------------------------------------------------------------

def _load_similarity_cache(root: Path | None) -> dict[str, dict]:
    _, _, sim_path = _cache_paths(root)
    if sim_path.exists():
        return json.loads(sim_path.read_text(encoding="utf-8"))
    return {}


def _save_similarity_cache(cache: dict[str, dict], root: Path | None) -> None:
    _, _, sim_path = _cache_paths(root)
    sim_path.parent.mkdir(parents=True, exist_ok=True)
    sim_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def find_similar_pairs(
    embeddings: np.ndarray,
    page_ids: list[str],
    changed_ids: set[str],
    current_hashes: dict[str, str],
    threshold: float = 0.45,
    top_k_per_page: int = 10,
    root: Path | None = None,
) -> list[tuple[str, str, float]]:
    """コサイン類似度が閾値以上のページペアを返す（増分キャッシュ付き）。

    changed_ids に含まれないページ同士のペアは、キャッシュの類似度を再利用する。
    changed_ids に含まれるページが関与するペアのみ FAISS で再計算する。

    Args:
        embeddings    : 正規化済みベクトル (N, dim)
        page_ids      : embeddings の行順に対応する page_id リスト
        changed_ids   : build_embeddings() が返した変更ページ集合
        current_hashes: page_id → content_hash のマッピング
        threshold     : リンク化の閾値
        top_k_per_page: FAISS 検索時の近傍数
        root          : wiki root（キャッシュファイルの場所）

    Returns:
        [(page_id_a, page_id_b, cosine_similarity), ...]
    """
    n = len(embeddings)
    id_to_row = {pid: i for i, pid in enumerate(page_ids)}
    current_id_set = set(page_ids)

    # --- 類似度キャッシュ読み込み ---
    sim_cache = _load_similarity_cache(root)

    # --- キャッシュの棚卸し: 今回存在しないページを含むエントリを削除 ---
    valid_cache: dict[str, dict] = {}
    for key, entry in sim_cache.items():
        parts = key.split("||")
        if len(parts) != 2:
            continue
        if parts[0] in current_id_set and parts[1] in current_id_set:
            valid_cache[key] = entry

    # --- ペアを3分類 ---
    #   reusable: 両方 unchanged → キャッシュの similarity をそのまま使う
    #   stale:    片方以上 changed → FAISS で再計算が必要
    #   new:      キャッシュにない新規ペア → FAISS で計算

    reusable_pairs: list[tuple[str, str, float]] = []
    stale_keys: set[str] = set()

    for key, entry in valid_cache.items():
        id_a, id_b = key.split("||")
        ha = current_hashes.get(id_a, "")
        hb = current_hashes.get(id_b, "")

        if entry.get("hash_a") == ha and entry.get("hash_b") == hb:
            # 両方 unchanged → 再利用
            sim = entry["similarity"]
            if sim >= threshold:
                reusable_pairs.append((id_a, id_b, sim))
        else:
            # hash 不一致 → 再計算対象としてマーク
            stale_keys.add(key)

    # --- 再計算対象ページの特定 ---
    # changed_ids に含まれるページ、または stale ペアに関与するページ
    pages_needing_search: set[str] = set(changed_ids)
    for key in stale_keys:
        parts = key.split("||")
        pages_needing_search.update(parts)

    # 新規ページ（キャッシュに一切登場しないページ）も追加
    cached_page_ids = set()
    for key in valid_cache:
        cached_page_ids.update(key.split("||"))
    new_page_ids = current_id_set - cached_page_ids
    pages_needing_search.update(new_page_ids)

    # --- FAISS で再計算対象のみ検索 ---
    fresh_pairs: list[tuple[str, str, float]] = []

    if pages_needing_search and n >= 2:
        # 全ベクトルで FAISS インデックスを構築（検索対象は全ページ）
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        # 変更ページのみをクエリとして検索
        query_rows = [id_to_row[pid] for pid in pages_needing_search if pid in id_to_row]
        if query_rows:
            query_vectors = embeddings[np.array(query_rows)]
            k = min(top_k_per_page + 1, n)
            scores, indices = index.search(query_vectors, k)

            seen: set[tuple[str, str]] = set()
            for qi, src_row in enumerate(query_rows):
                src_id = page_ids[src_row]
                for ji in range(len(indices[qi])):
                    dst_row = int(indices[qi][ji])
                    sim = float(scores[qi][ji])
                    if src_row == dst_row:
                        continue
                    dst_id = page_ids[dst_row]
                    pk = tuple(sorted([src_id, dst_id]))
                    if pk in seen:
                        continue
                    seen.add(pk)
                    fresh_pairs.append((pk[0], pk[1], sim))

    # --- 類似度キャッシュを更新 ---
    updated_cache: dict[str, dict] = {}

    # まず reusable をそのまま移行
    for key, entry in valid_cache.items():
        if key not in stale_keys:
            updated_cache[key] = entry

    # 新規・再計算分を追加（閾値以下も記録して次回の判定に使う）
    for id_a, id_b, sim in fresh_pairs:
        key = _pair_key(id_a, id_b)
        sorted_ids = sorted([id_a, id_b])
        updated_cache[key] = {
            "similarity": round(sim, 4),
            "hash_a": current_hashes.get(sorted_ids[0], ""),
            "hash_b": current_hashes.get(sorted_ids[1], ""),
        }

    _save_similarity_cache(updated_cache, root)

    # --- 結果を統合して返す ---
    all_pairs = reusable_pairs + [
        (a, b, s) for a, b, s in fresh_pairs if s >= threshold
    ]

    # 重複排除（reusable と fresh で同じペアが出る可能性がある）
    final: dict[tuple[str, str], float] = {}
    for a, b, s in all_pairs:
        pk = tuple(sorted([a, b]))
        # 新しい計算結果を優先
        if pk not in final or (a, b, s) in fresh_pairs:
            final[pk] = s

    return [(a, b, s) for (a, b), s in sorted(final.items(), key=lambda x: x[1], reverse=True)]
```

### 5.4 新規ファイル: `tools/llm_wiki/linker_semantic.py`

```python
"""L2: Embedding コサイン類似度によるリンク生成。"""

from __future__ import annotations

from .embedder import _page_content_hash, build_embeddings, find_similar_pairs
from .models import WikiLink, WikiPage

# --- 設定 ---
# L1 トークン重複で既にリンクされているペアは除外するため、
# L2 の閾値は低めに設定（L1 が拾えない「言い換え」を捕捉する目的）
SIMILARITY_THRESHOLD = 0.45
TOP_K_PER_PAGE = 8


def link_semantic(pages: list[WikiPage], *, force_embed: bool = False) -> list[WikiPage]:
    """L2: Embedding コサイン類似度でリンクを追加する。

    - index ページは除外する（内容が薄いため）
    - 既に L1 で同じペアにリンクがある場合は追加しない（重複回避）
    - Embedding とコサイン類似度は増分キャッシュされる
    """
    target_pages = [p for p in pages if p.page_type != "index"]
    if len(target_pages) < 2:
        return pages

    # 層1: Embedding 生成（変更ページのみ再計算）
    embeddings, page_ids, changed_ids = build_embeddings(target_pages, force=force_embed)

    # ページごとの content_hash を渡す（層2 のキャッシュ判定に必要）
    current_hashes = {p.page_id: _page_content_hash(p) for p in target_pages}

    # 層2: 類似度計算（変更ページが関与するペアのみ再計算）
    pairs = find_similar_pairs(
        embeddings,
        page_ids,
        changed_ids=changed_ids,
        current_hashes=current_hashes,
        threshold=SIMILARITY_THRESHOLD,
        top_k_per_page=TOP_K_PER_PAGE,
    )

    # page_id → WikiPage の逆引き
    by_id: dict[str, WikiPage] = {p.page_id: p for p in pages}

    for id_a, id_b, sim in pairs:
        page_a = by_id.get(id_a)
        page_b = by_id.get(id_b)
        if page_a is None or page_b is None:
            continue

        # L1 で既にリンクされていたら追加しない
        existing_targets_a = {link.target_page_id for link in page_a.links}
        if id_b not in existing_targets_a:
            page_a.links.append(
                WikiLink(
                    relation="similar_to",
                    target_page_id=id_b,
                    target_path=page_b.path,
                    confidence=round(sim, 3),
                    source=f"embedding_cosine:{sim:.3f}",
                )
            )

        existing_targets_b = {link.target_page_id for link in page_b.links}
        if id_a not in existing_targets_b:
            page_b.links.append(
                WikiLink(
                    relation="similar_to",
                    target_page_id=id_a,
                    target_path=page_a.path,
                    confidence=round(sim, 3),
                    source=f"embedding_cosine:{sim:.3f}",
                )
            )

    return pages
```

### 5.5 閾値の設計判断

| 閾値 | 意味 | 想定用途 |
|---|---|---|
| 0.70+ | 強い類似（ほぼ同じトピック） | 重複検出向き |
| 0.45〜0.70 | 中程度の類似（関連トピック） | **L2 のターゲットゾーン** |
| 0.30〜0.45 | 弱い類似（遠い関連） | L4 セレンディピティの候補 |
| 0.30 未満 | 無関係 | 無視 |

**0.45 を選んだ理由:** L1 のトークン重複は同じ単語が出現するペアしか拾わない。L2 は「同じ単語は使っていないが意味的に関連する」ペアを補完する役割なので、類似度の中間帯を狙う。日本語 + 英語混在コンテンツでは `all-MiniLM-L6-v2` の類似度が全体的にやや低めに出るため、閾値も低めに設定する。

**チューニング方法:** 初回ビルド後に `similar_to` リンクの一覧を目視確認し、ノイズが多ければ 0.50 に上げ、拾い漏れが多ければ 0.40 に下げる。

---

## 6. レイヤー 3: 共起リンク（会話時記録）

### 6.1 概要

Claude が会話中に Wiki ページを参照して回答した際、**実際に役立ったページ群とその文脈を `co_references.jsonl` に記録する**。ビルド時にこのログを集計し、複数回共起したペアにリンクを生成する。

### 6.2 記録フロー（C 案の実装）

```
ユーザーが質問
  ↓
Claude が wiki_search("タスク計画") → 結果: [task-breakdown, plans-md, ...]
Claude が wiki_read(["topics/plans-md.md"]) → 内容を参照
  ↓
Claude が回答を生成
  ↓
★ Claude が wiki_log_co_reference() を呼び出す ★
  pages: 実際に回答に使ったページのパスリスト
  query_intent: "認知リソースが枯渇した状態での生活維持と仕事再開"
  ↓
co_references.jsonl に1行追記
```

### 6.3 記録 API: `wiki_log_co_reference()`

**ファイル:** `tools/llm_wiki/api.py` に追加

```python
def wiki_log_co_reference(
    pages: list[str],
    query_intent: str,
    conversation_id: str = "",
    root: Path | str | None = None,
) -> dict[str, str]:
    """会話中に共起参照されたページ群を記録する。

    Args:
        pages: 実際に回答に使用した wiki ページの path リスト（2件以上）
        query_intent: 何を解決しようとしたかの1行要約
        conversation_id: 会話識別子（省略時は timestamp から自動生成）

    Returns:
        {"status": "logged", "pages": N, "intent": "..."} or {"status": "skipped", "reason": "..."}
    """
    if len(pages) < 2:
        return {"status": "skipped", "reason": "2ページ以上の共起が必要"}

    from .coref_logger import log_co_reference
    return log_co_reference(
        pages=pages,
        query_intent=query_intent,
        conversation_id=conversation_id,
        root=Path(root) if root else None,
    )
```

### 6.4 新規ファイル: `tools/llm_wiki/coref_logger.py`

```python
"""L3: 共起参照の記録（append-only JSONL）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .models import CoReference
from .paths import DEFAULT_WIKI_ROOT

JST = timezone(timedelta(hours=9))
COREF_FILE = "co_references.jsonl"


def _coref_path(root: Path | None = None) -> Path:
    wiki_root = root or DEFAULT_WIKI_ROOT
    return wiki_root / "indexes" / COREF_FILE


def log_co_reference(
    pages: list[str],
    query_intent: str,
    conversation_id: str = "",
    root: Path | None = None,
) -> dict[str, str]:
    """共起参照を JSONL ファイルに1行追記する。"""
    now = datetime.now(JST)
    if not conversation_id:
        conversation_id = f"conv_{now.strftime('%Y%m%d_%H%M%S')}"

    record = CoReference(
        pages=sorted(set(pages)),
        query_intent=query_intent.strip(),
        timestamp=now.isoformat(),
        conversation_id=conversation_id,
    )

    path = _coref_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    return {
        "status": "logged",
        "pages": str(len(record.pages)),
        "intent": record.query_intent,
    }


def load_co_references(root: Path | None = None) -> list[CoReference]:
    """全共起記録を読み込む。"""
    path = _coref_path(root)
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if not line.strip():
            continue
        records.append(CoReference.from_dict(json.loads(line)))
    return records
```

### 6.5 新規ファイル: `tools/llm_wiki/linker_coref.py`

```python
"""L3: 共起参照ベースのリンク生成。"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

from .coref_logger import load_co_references
from .models import CoReference, WikiLink, WikiPage

# --- 設定 ---
MIN_CO_OCCURRENCES = 2    # リンク化に必要な最低共起回数
MAX_LINKS_PER_PAGE = 10   # 1ページあたりの co_referenced リンク上限


def _aggregate_pairs(
    co_refs: list[CoReference],
) -> tuple[Counter, dict[tuple[str, str], list[str]]]:
    """ページペアごとの共起回数と代表的な intent を集計する。"""
    pair_counts: Counter[tuple[str, str]] = Counter()
    pair_intents: dict[tuple[str, str], list[str]] = defaultdict(list)

    for ref in co_refs:
        for a, b in combinations(ref.pages, 2):
            pair = tuple(sorted([a, b]))
            pair_counts[pair] += 1
            pair_intents[pair].append(ref.query_intent)

    return pair_counts, pair_intents


def link_co_referenced(pages: list[WikiPage]) -> list[WikiPage]:
    """L3: co_references.jsonl を集計し、共起リンクを追加する。"""
    co_refs = load_co_references()
    if not co_refs:
        return pages

    pair_counts, pair_intents = _aggregate_pairs(co_refs)
    by_path: dict[str, WikiPage] = {p.path: p for p in pages}

    # 共起回数が多い順にソート
    sorted_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)

    # ページごとの追加リンク数を追跡
    added_count: dict[str, int] = defaultdict(int)

    for (path_a, path_b), count in sorted_pairs:
        if count < MIN_CO_OCCURRENCES:
            continue

        page_a = by_path.get(path_a)
        page_b = by_path.get(path_b)
        if page_a is None or page_b is None:
            continue

        # 代表 intent（最新のもの）
        representative_intent = pair_intents[(path_a, path_b)][-1]
        confidence = min(0.95, 0.3 + 0.1 * count)
        source_text = f"co_ref:{count}回, 代表: {representative_intent}"

        # A → B
        if added_count[path_a] < MAX_LINKS_PER_PAGE:
            existing_coref_targets = {
                link.target_path for link in page_a.links if link.relation == "co_referenced"
            }
            if path_b not in existing_coref_targets:
                page_a.links.append(
                    WikiLink(
                        relation="co_referenced",
                        target_page_id=page_b.page_id,
                        target_path=path_b,
                        confidence=confidence,
                        source=source_text,
                    )
                )
                added_count[path_a] += 1

        # B → A
        if added_count[path_b] < MAX_LINKS_PER_PAGE:
            existing_coref_targets = {
                link.target_path for link in page_b.links if link.relation == "co_referenced"
            }
            if path_a not in existing_coref_targets:
                page_b.links.append(
                    WikiLink(
                        relation="co_referenced",
                        target_page_id=page_a.page_id,
                        target_path=path_a,
                        confidence=confidence,
                        source=source_text,
                    )
                )
                added_count[path_b] += 1

    return pages
```

### 6.6 Claude への指示（スキル化）

L3 の記録を Claude が確実に行うために、以下のスキルを作成する。

**ファイル:** `.claude/skills/wiki-coref-logger/SKILL.md`

```markdown
---
name: wiki-coref-logger
description: LLMWiki のページを2つ以上参照して回答した後、共起参照を自動記録する。wiki_search や wiki_read で複数ページを参照した会話で、回答完了後にプロアクティブに発動する。
---

# Wiki Co-Reference Logger

## 目的

会話中に LLMWiki の複数ページを参照して回答した場合、
実際に役立ったページの組み合わせと文脈を記録する。

## 発動条件

以下の **すべて** を満たすとき、回答の最後に自動発動する:

1. 会話中に `wiki_search` / `wiki_read` / `search_wiki.py` で
   **2ページ以上** の Wiki ページを参照した
2. 参照したページの内容を実際に回答に使用した（検索しただけで使わなかったページは除外）

## 手順

1. 回答に実際に使用したページの `path` をリストアップする
2. ユーザーの質問意図を **1行（50文字以内）** で要約する
3. 以下を実行する:

\```python
from tools.llm_wiki.api import wiki_log_co_reference

wiki_log_co_reference(
    pages=["topics/task-breakdown.md", "topics/plans-md.md"],
    query_intent="大きな作業の分解と継続作業の再開",
)
\```

4. ログの成否をユーザーに通知する必要はない（サイレント実行）

## 除外条件

以下の場合は記録 **しない**:

- 参照ページが1つだけ
- wiki_search の結果を一覧表示しただけで、内容を深く使っていない
- ページの内容を引用・参照せず、一般知識だけで回答した

## 記録の例

| ユーザーの質問 | 参照ページ | query_intent |
|---|---|---|
| 「大きな作業をどう進めるか」 | task-breakdown, plans-md | タスク分解と継続作業の再開 |
| 「キャリアと学習の両方を考えたい」 | キャリア設計, 学習計画 | キャリアと学習計画の統合 |
| 「先週の振り返りをしたい」 | timeline-2026-06-week-26, people-self-facts | 週次振り返りの文脈把握 |
```

### 6.7 `co_references.jsonl` のデータ例

```jsonl
{"pages":["topics/task-breakdown.md","topics/plans-md.md"],"query_intent":"大きな作業の分解と継続作業の再開","timestamp":"2026-06-28T21:30:00+09:00","conversation_id":"conv_20260628_213000"}
{"pages":["topics/キャリア設計.md","topics/学習計画.md"],"query_intent":"キャリアと学習計画の統合","timestamp":"2026-06-29T09:15:00+09:00","conversation_id":"conv_20260629_091500"}
{"pages":["topics/task-breakdown.md","topics/plans-md.md"],"query_intent":"作業計画と再開メモ","timestamp":"2026-06-30T20:00:00+09:00","conversation_id":"conv_20260630_200000"}
```

---

## 7. レイヤー 4: セレンディピティリンク

### 7.1 概要

L3 の共起データと L2 の Embedding を組み合わせ、**異カテゴリ間の意外な接続** を LLM で言語化してリンクにする。

### 7.2 パイプライン

```
Step 1: 候補ペアの抽出
  - L3 の co_referenced ペアのうち、異なる page_type / 異なる tags を持つもの
  - L2 の Embedding で中距離（0.25〜0.50）にあり、かつ異カテゴリのペア
  ↓
Step 2: LLM による接続の言語化
  各候補ペアに対して LLM に問い合わせ
  「この2つのページに共通する抽象的な原理は何か？」
  ↓
Step 3: 有効な接続だけをリンク化
  LLM が "none" を返したペアは除外
```

### 7.3 新規ファイル: `tools/llm_wiki/linker_serendipity.py`

```python
"""L4: セレンディピティリンク — 異カテゴリ間の意外な接続。"""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from .coref_logger import load_co_references
from .embedder import build_embeddings, find_similar_pairs
from .models import WikiLink, WikiPage
from .paths import DEFAULT_WIKI_ROOT

# --- 設定 ---
MAX_CANDIDATES = 30        # LLM に投げる候補ペアの上限
MAX_LINKS_PER_PAGE = 5     # 1ページあたりのセレンディピティリンク上限
CACHE_FILE = "serendipity_cache.json"


def _is_cross_category(page_a: WikiPage, page_b: WikiPage) -> bool:
    """2ページが異なるカテゴリに属するか判定する。"""
    if page_a.page_type != page_b.page_type:
        return True
    tags_a = set(page_a.tags)
    tags_b = set(page_b.tags)
    if tags_a and tags_b and not tags_a & tags_b:
        return True
    return False


def _find_candidates(
    pages: list[WikiPage],
) -> list[tuple[WikiPage, WikiPage, str]]:
    """セレンディピティリンクの候補ペアを抽出する。

    Returns:
        [(page_a, page_b, reason), ...]
        reason は "co_ref" or "mid_distance_embedding"
    """
    by_path: dict[str, WikiPage] = {p.path: p for p in pages}
    candidates: list[tuple[WikiPage, WikiPage, str]] = []
    seen_pairs: set[tuple[str, str]] = set()

    # ソース1: L3 共起で異カテゴリのペア
    co_refs = load_co_references()
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    for ref in co_refs:
        for a, b in combinations(ref.pages, 2):
            pair = tuple(sorted([a, b]))
            pair_counts[pair] += 1

    for (path_a, path_b), count in sorted(pair_counts.items(), key=lambda x: x[1], reverse=True):
        page_a = by_path.get(path_a)
        page_b = by_path.get(path_b)
        if page_a is None or page_b is None:
            continue
        if not _is_cross_category(page_a, page_b):
            continue
        pair_key = tuple(sorted([page_a.page_id, page_b.page_id]))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        candidates.append((page_a, page_b, "co_ref"))
        if len(candidates) >= MAX_CANDIDATES:
            break

    # ソース2: similarity_cache.json から中距離ペアを抽出
    # L2 のビルド時に既に全ペアの類似度が計算・キャッシュ済み。
    # L4 は新たに FAISS 計算を行わず、キャッシュを参照するだけ。
    if len(candidates) < MAX_CANDIDATES:
        from .embedder import _load_similarity_cache
        sim_cache = _load_similarity_cache()
        by_id = {p.page_id: p for p in pages}
        for key, entry in sorted(sim_cache.items(), key=lambda x: x[1].get("similarity", 0), reverse=True):
            sim = entry.get("similarity", 0)
            if sim > 0.50 or sim < 0.25:
                continue  # 中距離（0.25〜0.50）のみ
            parts = key.split("||")
            if len(parts) != 2:
                continue
            id_a, id_b = parts
            pa = by_id.get(id_a)
            pb = by_id.get(id_b)
            if pa is None or pb is None:
                continue
            if not _is_cross_category(pa, pb):
                continue
            pair_key = tuple(sorted([id_a, id_b]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            candidates.append((pa, pb, "mid_distance_embedding"))
            if len(candidates) >= MAX_CANDIDATES:
                break

    return candidates


def _load_cache(root: Path | None = None) -> dict[str, str]:
    wiki_root = root or DEFAULT_WIKI_ROOT
    cache_path = wiki_root / "indexes" / CACHE_FILE
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict[str, str], root: Path | None = None) -> None:
    wiki_root = root or DEFAULT_WIKI_ROOT
    cache_path = wiki_root / "indexes" / CACHE_FILE
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _ask_llm_for_bridge(page_a: WikiPage, page_b: WikiPage) -> str | None:
    """LLM に2ページ間の抽象的な接続を問い合わせる。

    Returns:
        接続の説明文（1行）。接続がなければ None。
    """
    import anthropic

    client = anthropic.Anthropic()

    prompt = f"""以下の2つのページに共通する抽象的な原理、構造的な類似性、
または片方から他方に転用できるアイデアを1行（40文字以内）で述べてください。
共通点がなければ「none」とだけ答えてください。

## ページA: {page_a.title}
要約: {page_a.summary}
タグ: {', '.join(page_a.tags)}
Key Facts: {'; '.join(page_a.key_facts[:3])}

## ページB: {page_b.title}
要約: {page_b.summary}
タグ: {', '.join(page_b.tags)}
Key Facts: {'; '.join(page_b.key_facts[:3])}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = response.content[0].text.strip()
    if answer.lower() in ("none", "なし", "共通点なし"):
        return None
    return answer


def link_serendipity(
    pages: list[WikiPage],
    *,
    use_llm: bool = True,
    dry_run: bool = False,
) -> list[WikiPage]:
    """L4: 異カテゴリ間のセレンディピティリンクを生成する。

    Args:
        use_llm: True なら LLM API で接続を言語化。False ならスキップ。
        dry_run: True なら候補抽出のみでリンク追加しない。
    """
    candidates = _find_candidates(pages)
    if not candidates:
        return pages

    if not use_llm:
        return pages

    cache = _load_cache()
    by_id: dict[str, WikiPage] = {p.page_id: p for p in pages}
    added_count: dict[str, int] = defaultdict(int)

    for page_a, page_b, reason in candidates:
        pair_key = f"{page_a.page_id}||{page_b.page_id}"

        # キャッシュチェック
        if pair_key in cache:
            bridge = cache[pair_key] if cache[pair_key] != "__none__" else None
        else:
            bridge = _ask_llm_for_bridge(page_a, page_b)
            cache[pair_key] = bridge if bridge else "__none__"

        if bridge is None:
            continue
        if dry_run:
            continue

        confidence = 0.6 if reason == "co_ref" else 0.4
        source_text = f"abstract_bridge: {bridge}"

        # A → B
        if added_count[page_a.page_id] < MAX_LINKS_PER_PAGE:
            page_a.links.append(
                WikiLink(
                    relation="serendipity",
                    target_page_id=page_b.page_id,
                    target_path=page_b.path,
                    confidence=confidence,
                    source=source_text,
                )
            )
            added_count[page_a.page_id] += 1

        # B → A
        if added_count[page_b.page_id] < MAX_LINKS_PER_PAGE:
            page_b.links.append(
                WikiLink(
                    relation="serendipity",
                    target_page_id=page_a.page_id,
                    target_path=page_a.path,
                    confidence=confidence,
                    source=source_text,
                )
            )
            added_count[page_b.page_id] += 1

    _save_cache(cache)
    return pages
```

### 7.4 LLM プロンプトの設計意図

```
以下の2つのページに共通する抽象的な原理、構造的な類似性、
または片方から他方に転用できるアイデアを1行（40文字以内）で述べてください。
共通点がなければ「none」とだけ答えてください。
```

**設計判断:**
- **40 文字以内** — リンクの `source` フィールドに収まるサイズ。冗長な説明は不要
- **「抽象的な原理」「構造的な類似性」「転用できるアイデア」** — 3 つの観点を明示することで、表面的な共通点（「どちらも日本語で書かれている」等）を防ぐ
- **「none」を明示的に許可** — 強制的に接続を捻り出すのを防ぐ
- **Key Facts を 3 件に限定** — トークン節約。要約 + タグ + Key Facts 3 件で十分な文脈
- **モデル: `claude-sonnet-4-20250514`** — 高速・低コスト。接続の判定にはこのクラスで十分

**コスト見積もり:**
- 候補 30 ペア × 入力 ~200 tokens × 出力 ~30 tokens = ~6,900 tokens
- Claude Sonnet 4 の価格: 入力 $3/MTok, 出力 $15/MTok
- **1 回のビルドあたり約 $0.002（0.3 円未満）**

---

## 8. compiler.py の変更

### 8.1 変更箇所

`build_wiki()` 関数内の `link_pages()` 呼び出しを、4 層リンカーの逐次呼び出しに置き換える。

**ファイル:** `tools/llm_wiki/compiler.py`

**変更前（L198）:**
```python
    pages = link_pages(main_pages + index_pages)
```

**変更後:**
```python
    pages = main_pages + index_pages

    # L1: 構造リンク（既存ロジック）
    pages = link_structural(pages)

    # L2: 意味類似リンク（Embedding）
    if enable_semantic:
        from .linker_semantic import link_semantic
        pages = link_semantic(pages, force_embed=force_embed)

    # L3: 共起リンク（co_references.jsonl 集計）
    from .linker_coref import link_co_referenced
    pages = link_co_referenced(pages)

    # L4: セレンディピティリンク（LLM による抽象ブリッジ）
    if enable_serendipity:
        from .linker_serendipity import link_serendipity
        pages = link_serendipity(pages, use_llm=use_llm)
```

### 8.2 `build_wiki()` のシグネチャ変更

```python
def build_wiki(
    root: Path | str | None = None,
    *,
    include_issues: bool = False,
    refresh_issues: bool = False,
    issue_snapshot_path: Path | str | None = None,
    include_issue_comments: bool = False,
    # --- 新規パラメータ ---
    enable_semantic: bool = True,       # L2 を有効にするか
    force_embed: bool = False,          # Embedding キャッシュを無視して再計算
    enable_serendipity: bool = False,   # L4 を有効にするか（デフォルト無効）
    use_llm: bool = True,              # L4 で LLM API を使うか
) -> dict[str, int]:
```

### 8.3 CLI フラグの追加

**ファイル:** `scripts/build_llm_wiki.py`

```python
parser.add_argument("--no-semantic", action="store_true", help="L2 Embedding リンクを無効化")
parser.add_argument("--force-embed", action="store_true", help="Embedding キャッシュを無視して再計算")
parser.add_argument("--serendipity", action="store_true", help="L4 セレンディピティリンクを有効化")
parser.add_argument("--no-llm", action="store_true", help="L4 で LLM API を使わない")
```

呼び出し例:
```bash
# L1 + L2 + L3（デフォルト）
python scripts/build_llm_wiki.py --include-issues

# L1 のみ（現行と同じ動作）
python scripts/build_llm_wiki.py --include-issues --no-semantic

# L1 + L2 + L3 + L4（全レイヤー）
python scripts/build_llm_wiki.py --include-issues --serendipity

# Embedding 再計算 + L4
python scripts/build_llm_wiki.py --include-issues --force-embed --serendipity
```

### 8.4 戻り値の変更

```python
return {
    "topics": len(topic_pages),
    "people_self": len(people_pages),
    "timelines": len(timeline_pages),
    "issues": len(issue_pages),
    "projects": len(project_pages),
    "indexes": len(index_pages),
    "total_pages": len(pages),
    "validation_issues": len(report.issues),
    "auto_repairs": len(repaired),
    # --- 新規 ---
    "l2_similar_to_links": sum(
        1 for p in pages for l in p.links if l.relation == "similar_to"
    ),
    "l3_co_referenced_links": sum(
        1 for p in pages for l in p.links if l.relation == "co_referenced"
    ),
    "l4_serendipity_links": sum(
        1 for p in pages for l in p.links if l.relation == "serendipity"
    ),
}
```

---

## 9. import の整理

### 9.1 `linker.py` の import 変更

```python
# 変更前
from .linker import link_pages

# 変更後
from .linker import link_structural
```

### 9.2 `api.py` の import 追加

```python
# 既存 import に追加
from .coref_logger import log_co_reference  # wiki_log_co_reference 内で使用
```

### 9.3 `__init__.py` のエクスポート追加（必要な場合）

```python
from .api import wiki_log_co_reference
from .models import CoReference
```

---

## 10. validator.py の変更

### 10.1 新リレーションタイプの認識

`dangling_link` のチェック時に新しいリレーションタイプが来ても正常に処理されることを確認する。現在の validator は `relation` の値を見ていない（`target_path` の存在チェックのみ）ため、**変更不要**。

### 10.2 新バリデーションルールの追加（オプション）

```python
# L4 serendipity リンクの source に bridge 説明がないケースを検出
if link.relation == "serendipity" and not link.source.startswith("abstract_bridge:"):
    issues.append(
        ValidationIssue(
            code="malformed_serendipity_link",
            path=page.path,
            message=f"serendipity link missing bridge description: {link.target_path}",
        )
    )
```

---

## 11. graph.json と検索への影響

### 11.1 graph.json

変更不要。`graph.json` は `page.links` をそのまま JSON 化しているため、新しい `relation` タイプが自動的に含まれる。

### 11.2 `wiki_follow_links()` の活用

既存の `relation_types` フィルタがそのまま使える:

```python
# L2 リンクのみ表示
wiki_follow_links("topics/some-page.md", relation_types=["similar_to"])

# L3 リンクのみ表示
wiki_follow_links("topics/some-page.md", relation_types=["co_referenced"])

# L4 リンクのみ表示
wiki_follow_links("topics/some-page.md", relation_types=["serendipity"])

# 全インスピレーション系リンク
wiki_follow_links("topics/some-page.md", relation_types=["co_referenced", "serendipity", "similar_to"])
```

### 11.3 search.py の変更

Phase 1 では変更なし。将来的に Embedding ベースの検索に切り替える場合は、`_score_page()` を以下に置き換え可能（この SDD のスコープ外）:

```python
# 将来の改善案（この SDD では実装しない）
def _score_page_hybrid(page, query, query_embedding):
    keyword_score = _score_page(page, query)  # 既存
    semantic_score = cosine_similarity(query_embedding, page_embedding)
    return 0.5 * keyword_score + 0.5 * semantic_score
```

---

## 12. ページレンダリングの変更

### 12.1 Relations セクションのグルーピング

**ファイル:** `tools/llm_wiki/compiler.py` の `_render_page()` を変更

**変更前:**
```python
relation_lines = [
    f"- {link.relation}: [{link.target_page_id}]({link.target_path})"
    for link in page.links[:20]
] or ["- -"]
```

**変更後:**
```python
def _render_relations(links: list[WikiLink]) -> list[str]:
    """リンクをレイヤーごとにグルーピングして表示する。"""
    l1_relations = {"index_of", "relates_to", "mentions", "derived_from",
                    "references_issue", "relates_to_topic", "child_of",
                    "parent_of", "related_issue"}
    groups = {
        "Structure": [],     # L1
        "Similar": [],       # L2
        "Co-referenced": [], # L3
        "Serendipity": [],   # L4
    }
    for link in links[:30]:
        line = f"- {link.relation}: [{link.target_page_id}]({link.target_path})"
        if link.relation in l1_relations:
            groups["Structure"].append(line)
        elif link.relation == "similar_to":
            groups["Similar"].append(line)
        elif link.relation == "co_referenced":
            line += f"  <!-- {link.source} -->"
            groups["Co-referenced"].append(line)
        elif link.relation == "serendipity":
            line += f"\n  > {link.source.removeprefix('abstract_bridge: ')}"
            groups["Serendipity"].append(line)

    result = []
    for group_name, lines in groups.items():
        if lines:
            result.append(f"### {group_name}")
            result.extend(lines)
            result.append("")
    return result or ["- -"]
```

**レンダリング結果の例:**

```markdown
## Relations

### Structure
- derived_from: [sources/memories/facts.md](sources/memories/facts.md)
- relates_to_topic: [topic-キャリア設計](topics/キャリア設計.md)

### Similar
- similar_to: [topic-転職活動](topics/転職活動.md)

### Co-referenced
- co_referenced: [topic-plans-md](topics/plans-md.md)  <!-- co_ref:5回, 代表: 継続作業の再開 -->

### Serendipity
- serendipity: [topic-ci-cd-pipeline](topics/ci-cd-pipeline.md)
  > 反復プロセスの自動化による認知負荷の削減
```

---

## 13. 実装順序と依存関係

```
Phase A: 基盤整備（他に依存なし）
├── A-1: models.py に CoReference を追加
├── A-2: linker.py を link_structural() にリネーム
└── A-3: compiler.py の新パラメータ追加（L2/L3/L4 は空のパススルー）

Phase B: L2 Embedding リンク（A に依存）
├── B-1: embedder.py を新規作成
├── B-2: linker_semantic.py を新規作成
├── B-3: compiler.py から link_semantic() を呼び出し
└── B-4: build_llm_wiki.py に CLI フラグ追加

Phase C: L3 共起リンク（A に依存、B とは独立）
├── C-1: coref_logger.py を新規作成
├── C-2: linker_coref.py を新規作成
├── C-3: api.py に wiki_log_co_reference() を追加
├── C-4: compiler.py から link_co_referenced() を呼び出し
└── C-5: wiki-coref-logger スキルを作成

Phase D: L4 セレンディピティ（B, C に依存）
├── D-1: linker_serendipity.py を新規作成
├── D-2: compiler.py から link_serendipity() を呼び出し
└── D-3: build_llm_wiki.py に --serendipity フラグ追加

Phase E: レンダリング改善（A に依存、B/C/D とは独立）
└── E-1: compiler.py の _render_page() を変更
```

```
A-1 ──→ A-2 ──→ A-3
          ↓        ↓
      B-1→B-2→B-3→B-4    C-1→C-2→C-3→C-4→C-5
          ↓                    ↓
          └────→ D-1 → D-2 → D-3
                               ↓
A-3 ─────────────────────→ E-1
```

---

## 14. テスト戦略

### 14.1 各レイヤーのユニットテスト

```python
# tests/test_linker_semantic.py
def test_link_semantic_adds_similar_to_links():
    """L2: Embedding リンクが生成されることを確認。"""
    pages = [
        WikiPage(page_id="topic-a", page_type="topics", title="キャリア設計",
                 path="topics/career.md", summary="エンジニアのキャリアパスを考える"),
        WikiPage(page_id="topic-b", page_type="topics", title="転職活動の進め方",
                 path="topics/job-change.md", summary="転職の準備と面接対策"),
    ]
    result = link_semantic(pages)
    similar_links = [l for p in result for l in p.links if l.relation == "similar_to"]
    assert len(similar_links) > 0
    assert all(0.0 < l.confidence <= 1.0 for l in similar_links)


# tests/test_linker_coref.py
def test_link_co_referenced_requires_min_occurrences(tmp_path):
    """L3: 1回だけの共起はリンク化されないことを確認。"""
    ...


def test_link_co_referenced_creates_bidirectional_links(tmp_path):
    """L3: 共起リンクが双方向に生成されることを確認。"""
    ...


# tests/test_linker_serendipity.py
def test_find_candidates_filters_same_category():
    """L4: 同カテゴリのペアは候補に含まれないことを確認。"""
    ...


def test_link_serendipity_uses_cache():
    """L4: キャッシュ済みペアは LLM を呼ばないことを確認。"""
    ...
```

### 14.2 統合テスト

```python
# tests/test_build_with_layers.py
def test_build_wiki_with_all_layers(tmp_path):
    """全レイヤーが順番に実行され、graph.json に全リレーションタイプが含まれることを確認。"""
    result = build_wiki(
        root=tmp_path,
        enable_semantic=True,
        enable_serendipity=False,  # LLM API を使わない
    )
    assert result["l2_similar_to_links"] >= 0
    assert result["l3_co_referenced_links"] >= 0

    graph = json.loads((tmp_path / "indexes" / "graph.json").read_text())
    all_relations = {
        link["relation"]
        for links in graph.values()
        for link in links
    }
    # L1 の基本リレーションが含まれること
    assert "derived_from" in all_relations or "relates_to_topic" in all_relations
```

---

## 15. 運用上の注意

### 15.1 `.gitignore` への追加

```gitignore
# LLMWiki 生成物（既に ignore 済みの場合は不要）
data/llm_wiki/indexes/embeddings.npz
data/llm_wiki/indexes/embeddings_meta.json
data/llm_wiki/indexes/serendipity_cache.json

# co_references.jsonl は追跡する（使用データなので価値がある）
# !data/llm_wiki/indexes/co_references.jsonl
```

### 15.2 co_references.jsonl の管理

- **Git 追跡する**（使用パターンのデータとして価値がある）
- 肥大化したら古い記録を `co_references_archive/` に移動
- 目安: 1,000 行を超えたら古い半分をアーカイブ

### 15.3 Embedding キャッシュの管理

- `embeddings.npz` は Git 追跡しない（再生成可能 + バイナリ）
- ページ内容が変わらなければキャッシュが効く（content_hash で判定）
- `--force-embed` で強制再計算

### 15.4 L4 の LLM API コスト

- 候補 30 ペア/回 × 0.3 円未満 = **1 ビルドあたり 0.3 円以下**
- キャッシュが効くため、2 回目以降は既出ペアの API コールが不要
- `--no-llm` で API なしビルドも可能

---

## 16. docs/llm_wiki.md への反映事項

この SDD の内容が実装されたら、`docs/llm_wiki.md` の以下のセクションを更新する:

- **§8 リンク仕様:** 新リレーションタイプ（`similar_to`, `co_referenced`, `serendipity`）を追記
- **§5 ビルドフロー:** 4 層リンカーの呼び出しフローを追記
- **§9 検索・探索 API:** `wiki_log_co_reference()` を API 一覧に追記
- **§4 ディレクトリ構成:** `co_references.jsonl`, `embeddings.npz` を追記
- **§16 推奨する改善項目:** 「Embedding ベース検索」「セレンディピティリンク」を実装済みに変更
