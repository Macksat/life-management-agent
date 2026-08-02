# CODEX.md — Codex 向け指示

> Codex で作業を始めるときに読む。詳細・共通ルールは [AGENTS.md](AGENTS.md) が正本。
> このファイルは Codex 固有の実務メモ。

## このリポジトリは何か

個人の **行動 OS**。GitHub Issue を中心に、思考・タスク・情報・学習・生活を蓄積し、
AI が整理・行動提案できる形に保つ。Markdown はルール・文脈・手順・評価の置き場。

## 最初に読む順番

1. [AGENTS.md](AGENTS.md)
2. [data/llm_wiki/sources/memories/user_context.md](data/llm_wiki/sources/memories/user_context.md)
3. 該当スキル（Codex は `.agents/skills/` から自動検出。一覧: [.agents/skills/](.agents/skills/)）
4. [docs/agent_playbook.md](docs/agent_playbook.md)

> **Skills:** Codex は `.agents/skills/`(および `.codex/skills/`)をスキャンして SKILL.md を自動検出する。これらは実体 `.claude/skills/` への symlink で、中身は同一(単一ソース)。description に合致すると自動で参照される。手動で読むなら一覧は [.agents/skills/](.agents/skills/)。
>
> **Evals:** evals は自動検出されない参照ドキュメント。スキル実行時に該当する [evals/](evals/) を明示的に読んで品質を確認する(AGENTS.md §14)。

## Codex での基本動作

- **対話で Issue 化(標準):** まず軽量に capture し、必要時だけ Clarify / Approval に戻す。高リスク案件以外は承認待ちを既定にしない。
  手順: [interactive-intake](.agents/skills/interactive-intake/SKILL.md)。task は `ready` / `in-progress` に上げる前に 理想/現状/問題点/方針 を補う。
- **second_brain 取り込み:** `scripts/ingest_second_brain_digest.py` と `scripts/extract_issue_candidates.py` を使い、A-MEM 判定を通して digest 登録と Issue 候補抽出を行う。
- 入力を受けたら: 記録要否 → 軽量 capture or 詳細化 → 重複確認 → 分類 → 起票 / 更新 → 必要なら後で refine。
  (フローチャート: [docs/agent_playbook.md](docs/agent_playbook.md))
- Issue は GitHub Issue として起票・更新する。本文フォーマットはテンプレート / [schemas/issue.schema.json](schemas/issue.schema.json) 準拠。
- コードを書くフェーズではないことが多い。**ハーネス(ルール・文書・テンプレート)整備を優先**。

## 絶対に守ること(要約)

- すべての Issue に **next_action**(不明なら `next_action: clarify goal`)。
- 人間判断(お金 / 人間関係 / 対外 / 大方針 / 削除 / 機微情報)は**勝手に進めない**。
- 機微情報を Issue・コミットに**書かない**。
- 定義外ラベルを**作らない**([docs/labels.md](docs/labels.md))。
- Issue を**物理削除しない**(`status:archived` で代替)。
- 対話起点の Issue 追加では、**低リスクは軽量 capture を優先**し、高リスク案件だけ確認に戻す。
- **task Issue は 理想 / 現状 / 問題点 / 方針 の4点セットを必須**にする。
- タスクは **30 分〜2 時間** 粒度に分解([task-breakdown](.claude/skills/task-breakdown/SKILL.md))。

## 出力スタイル

- 構造化(見出し・箇条書き・チェックリスト)。NG 例・入出力例を意識。
- 推測と事実を区別。不明点は確認質問にする。

## self-check

実行前に [evals/agent_behavior_eval.md](evals/agent_behavior_eval.md) で振る舞いを確認する。
