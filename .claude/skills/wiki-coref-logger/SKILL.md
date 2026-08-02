---
name: wiki-coref-logger
description: LLMWiki のページを2つ以上参照して回答した後、共起参照を記録する。
---

# Wiki Co-Reference Logger

## 発動条件

- `wiki_search` / `wiki_read` / `search_wiki.py` で 2 ページ以上参照した
- 参照内容を実際の回答に使った

## 手順

1. 回答に使ったページの `path` を列挙する
2. 質問意図を 1 行で要約する
3. `tools.llm_wiki.api.wiki_log_co_reference()` を呼ぶ

## 除外条件

- 参照ページが 1 件だけ
- 検索結果を並べただけ
- 実際の回答にページ内容を使っていない
