# Memory Search Spec

このテンプレートの `data/llm_wiki/sources/memories/` `data/llm_wiki/sources/second_brain/` `data/llm_wiki/sources/conversation_memory/` を、
AI エージェントが取りこぼし少なく検索・参照するための実装仕様。

## 1. 目的

現状の課題は、過去の記録があっても検索が弱く、応答時に取り出し漏れが起きること。

特に `data/llm_wiki/sources/second_brain/` は、`index.md` のタイトルとタグを人間が見て探す前提になっており、
言い換えや近い意味の相談に弱い。

この仕様の目的は以下。

- 過去の内省・判断・文脈を、ユーザーのクエリに応じて再利用できるようにする
- 記憶レイヤごとに適切な検索方式を分ける
- AI エージェントが「何をどこから拾ったか」を説明可能にする
- まずはローカル完結の MVP を作り、後から拡張できる構造にする

## 2. 解決したい問題

### 現状

- `second_brain` は `index.md` の目視検索に依存している
- `memories` はファイルを順に読む前提で、検索 API がない
- `conversation_memory` は新しさが重要だが、参照方法が明文化されているだけで検索器がない
- スキルごとに検索方法がばらつき、再利用可能な共通検索層がない

### 目指す状態

- クエリに対して、関連する記憶候補を自動で上位表示できる
- `second_brain` は意味検索できる
- `memories` は軽量かつ確実に引ける
- `conversation_memory` は直近文脈を優先して引ける
- 取得結果に `source / layer / reason` が付き、応答に織り込みやすい

## 3. 設計方針

全面ベクトル検索にはしない。記憶レイヤごとに方式を分ける。

### 3.1 レイヤ別方針

1. `data/llm_wiki/sources/second_brain/`
   意味検索を入れる。`BM25 + embedding + metadata filter` の hybrid search を採用する。

2. `data/llm_wiki/sources/memories/`
   まずは構造化キーワード検索にする。件数が少ないため、全面ベクトル化は不要。

3. `data/llm_wiki/sources/conversation_memory/`
   recency-first にする。`daily > weekly > monthly` を優先し、必要時だけキーワード検索する。
   加えて意味検索を入れる。`BM25 + embedding + metadata filter` の hybrid search を採用する。

4. `data/llm_wiki/sources/memories/rules.json`
   exact match のまま維持する。行動ルールは曖昧検索より明示トリガー一致を優先する。

### 3.2 非目標

- すべての会話ログを全文ベクトル化すること
- まず最初からクラウド DB や常駐サーバを前提にすること
- GitHub Issue まで含めた統合検索を MVP で完成させること
- 自動要約や自動判断までこの仕様で完結させること

## 4. 対象範囲

### MVP に含める

- `memories` の構造化検索
- `second_brain` の hybrid search
- `conversation_memory` の recency-first 検索と構造化検索
- 共通 retriever API
- ローカルインデックス生成
- CLI からの検索確認

### MVP に含めない

- GitHub Issue の統合検索
- Web UI
- 常駐 API サーバ
- 自動再ランキングの高度化
- ベクトル検索のオンライン更新

## 5. 想定ユースケース

1. キャリア相談で、過去の同種の内省を引きたい
2. 生活相談で、過去の判断基準や既知の事実を引きたい
3. 直近会話の続きをするとき、最近の約束や未解決論点を引きたい
4. スキル実行時に、都度ファイルを総当たりせず必要な記憶だけ引きたい

## 6. システム構成

MVP ではローカル実行の検索モジュールを作る。

### 6.1 構成要素

- `scripts/build_memory_index.py`
  インデックス生成スクリプト

- `scripts/search_memory.py`
  CLI 検索スクリプト

- `tools/memory_search/`
  検索ロジック本体

- `data/memory_index/`
  生成されたインデックス置き場

### 6.2 ストレージ

- 全文検索: SQLite FTS5
- ベクトル検索: SQLite
- MVP の推奨: SQLite 中心

理由:

- ローカル完結しやすい
- バックアップしやすい
- スクリプトから扱いやすい
- small data 前提では十分速い

## 7. データモデル

検索対象は「ファイル」ではなく「検索レコード」に正規化する。

### 7.1 共通レコード

各検索レコードは少なくとも以下を持つ。

- `id`
- `layer`
- `source_path`
- `title`
- `text`
- `summary`
- `tags`
- `section`
- `date`
- `recency_bucket`
- `metadata_json`

### 7.2 layer ごとの扱い

#### memories

1行または1項目を1レコードとして保存する。

追加メタデータ:

- `memory_type`: `facts | preferences | decisions | user_context`
- `section_name`

#### second_brain

1 digest を基本単位とし、必要なら見出し単位に分割する。

追加メタデータ:

- `digest_date`
- `theme_tags`
- `source_kind`: `digest`

#### conversation_memory

1セクションまたは1エントリを1レコードとして保存する。

追加メタデータ:

- `memory_span`: `daily | weekly | monthly`
- `entry_date`

## 8. 検索方式

### 8.1 rules

- JSON をそのまま読む
- `trigger / if / then / title` に対して単純な文字列照合を行う

### 8.2 memories

- SQLite FTS でキーワード検索
- `memory_type` と `section_name` の metadata filter を使えるようにする
- スコアは単純でよい

### 8.3 second_brain

hybrid search を採用する。

1. BM25 で上位候補を取る
2. embedding 類似度で上位候補を取る
3. 両方を正規化して混合スコアを作る
4. タグや日付で filter できるようにする
5. 上位 N 件を返す

初期の混合式:

`final_score = 0.45 * bm25 + 0.45 * vector + 0.10 * recency`

数値は固定で始め、運用で見直す。

### 8.4 conversation_memory

hybrid search + recency 重み付けを採用する。

1. BM25 で上位候補を取る
2. embedding 類似度で上位候補を取る
3. 両方を正規化し、recency を加味した混合スコアを作る
4. `memory_span` と `entry_date` で filter できるようにする
5. 上位 N 件を返す

初期の混合式:

`final_score = 0.30 * bm25 + 0.30 * vector + 0.40 * recency`

recency 重みを `second_brain`（0.10）より大きくし、`daily > weekly > monthly` の優先順を反映する。
数値は固定で始め、運用で見直す。

## 9. Retriever API

検索ロジックはスキルから共通で使える形にする。

### 9.1 Python API

```python
search_memories(
    query: str,
    layers: list[str] | None = None,
    top_k: int = 5,
    filters: dict | None = None,
) -> list[SearchResult]
```

`SearchResult` は少なくとも以下を返す。

- `id`
- `layer`
- `score`
- `title`
- `snippet`
- `source_path`
- `reason`
- `metadata`

### 9.2 CLI

```bash
python scripts/search_memory.py "習慣化のコツ"
python scripts/search_memory.py "新しいツールの使い方" --layer second_brain
python scripts/search_memory.py "今日の約束" --layer conversation_memory --top-k 3
```

## 10. インデックス更新

### 10.1 MVP 方針

- オンデマンド再生成でよい
- 差分更新は後回し

### 10.2 build の責務

- 対象ファイルを走査する
- レコードへ正規化する
- SQLite FTS を更新する
- ベクトル埋め込みを生成する
- 生成日時を記録する

### 10.3 実行タイミング

- 手動実行
- 週次レビュー後
- `second_brain` 取り込み後
- memory 更新後に必要なら再生成

## 11. スキル統合方針

以下のスキルは、既存の「ファイルを直接読む」手順に加えて retriever を優先利用する形へ変える。

- `interactive-intake`
- `research-to-action`
- `llm-wiki-build`

### 統合ルール

1. 過去の深い思考が関係するなら `second_brain` を検索する
2. 個人事実や判断基準は `memories` を検索する
4. 直近文脈は `conversation_memory` を検索する
5. 正本が Issue なら GitHub Issue を別途確認する

## 12. 技術選定

### 必須条件

- ローカル完結
- 日本語のクエリで使える
- small data で過剰設計にしない
- スクリプトから扱いやすい

### 採用スタック

- Python
- SQLite FTS5
- **OpenAI `text-embedding-3-small`**（1536 次元・日本語対応・低コスト）
- SQLite 系ベクトルストア

### 不採用

- ChromaDB — 依存が増える。SQLite 中心で十分なデータ規模のため不採用。

## 13. 失敗時の挙動

- インデックス未生成なら、明示的にその旨を返す
- ベクトル検索が失敗したら、`second_brain` は BM25 のみで fallback する
- 該当結果がなければ、無理に捏造せず空結果を返す
- 返答側では「未検出」と「存在しない」を混同しない

## 14. 評価指標

MVP では厳密な機械評価より、実用性の確認を優先する。

### 見る指標

- 取りこぼしが減ったか
- 言い換えクエリで `second_brain` を引けるか
- 関係ない結果が上位に出すぎないか
- 応答時に出典を示せるか
- build 時間が実用範囲か

### 手動評価例

- `習慣化`
- `振り返り`
- `第二の脳`
- `新しいツールの使い方`
- `最近決めた家計方針`
- `直近の会話で約束したこと`

## 15. 受け入れ条件

- [x] `memories` をキーワード検索できる
- [x] `second_brain` を hybrid search できる
- [x] `conversation_memory` を hybrid search + recency 重み付けで検索できる
- [x] CLI から各 layer を個別検索できる
- [x] 共通 Python API から検索できる
- [x] 検索結果に `layer / source_path / snippet / reason` が含まれる
- [x] ベクトル検索が失敗しても `second_brain` / `conversation_memory` が全文検索で fallback する
- [ ] 主要スキルの仕様書から retriever 利用方針を参照できる

## 16. 実装フェーズ

### Phase 1

- データモデル確定
- build スクリプト作成
- `memories` の FTS 検索

### Phase 2

- `second_brain` の hybrid search
- CLI 検索確認

### Phase 3

- `conversation_memory` の hybrid search + recency 重み付け検索
- 共通 retriever API

### Phase 4

- スキル統合
- 評価ケース整備

## 17. オープン項目

- ~~埋め込みモデルを何にするか~~ → **決定: OpenAI `text-embedding-3-small`（利用時は `.env` にOPENAI_API_KEYを設定）**
- ~~SQLite 系ベクトル実装にするか Chroma にするか~~ → **決定: SQLite 中心（Chroma 不採用）**
- `second_brain` を digest 単位で持つか見出し分割するか
- GitHub Issue 検索を Phase 5 で統合するか

## 18. 次アクション

この仕様書を正本として、次に以下を行う。

1. インデックススキーマ詳細を決める
2. `build_memory_index.py` の I/O 仕様を決める
3. `search_memory.py` の CLI 仕様を決める
4. 実装タスクへ分解する
