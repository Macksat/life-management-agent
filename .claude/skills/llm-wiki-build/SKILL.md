---
name: llm-wiki-build
description: ユーザーが渡した会話記録・メモ・Markdownファイルを LLMWiki のソースへ取り込み、Wikiを再構築する。「このファイルをWikiに入れて」「添付メモを取り込んで」「LLMWikiを更新して」などのときに使う。
---

# LLMWiki Build

ユーザーがこの会話で明示的に渡したファイルだけを取り込む。iCloud、外部デバイス、クラウドストレージを探索・取得しない。

## 手順

1. 渡されたファイルを読み、会話記録・メモ・既存digestのいずれかを判定する。
2. 会話記録・メモは、要点、事実、判断、アクション候補を含む Markdown digest に整形し、`data/llm_wiki/sources/second_brain/digests/` に保存する。元ファイルは変更しない。
3. `python3 scripts/ingest_second_brain_digest.py <digest-path>` で A-MEM の登録と索引更新を行う。
4. 必要なら `python3 scripts/extract_issue_candidates.py <digest-path>` で Issue 候補を抽出する。候補の起票・更新は別途ユーザー承認を得る。
5. `python3 scripts/build_llm_wiki.py --include-issues` を実行して Wiki を再構築する。
6. 取り込んだファイル、生成したdigest、更新結果を短く報告する。

## 制約

- ユーザーがファイルを渡していない場合、外部の場所を探さず添付またはパスの提示を依頼する。
- 機微情報はdigestやIssue候補へ保存しない。
- LLMWiki の `pages/` と `indexes/` は派生物であり、正本は `sources/` と GitHub Issue である。
