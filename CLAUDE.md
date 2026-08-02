# CLAUDE.md — Claude Code 向け指示

> Claude Code で作業を始めるときに読む。詳細・共通ルールは [AGENTS.md](AGENTS.md) が正本。
> このファイルは Claude Code 固有の実務メモ。

## このリポジトリは何か

個人の **行動 OS**。GitHub Issue を中心に、思考・タスク・情報・学習・生活を蓄積し、
AI が整理・行動提案できる形に保つ。Markdown はルール・文脈・手順・評価の置き場。

## 最初に読む順番

1. [AGENTS.md](AGENTS.md)
2. [data/llm_wiki/sources/memories/user_context.md](data/llm_wiki/sources/memories/user_context.md)
3. [data/llm_wiki/sources/memories/preferences.md](data/llm_wiki/sources/memories/preferences.md)（長期記憶: 好み・スタイル・パターン）
4. 該当スキル（`.claude/skills/<name>/SKILL.md`。例: intake なら [interactive-intake](.claude/skills/interactive-intake/SKILL.md)）
5. [docs/agent_playbook.md](docs/agent_playbook.md)

> **Skills:** 手順は Claude Code の Agent Skills として `.claude/skills/` に配置済み。description に合致すると自動で参照される。一覧は [.claude/skills/](.claude/skills/)。

## Claude Code でよくやる操作

- **対話で Issue 化(標準):** [interactive-intake](.claude/skills/interactive-intake/SKILL.md) に従う。まず軽量に capture し、重要判断や外部変更が絡むときだけ Clarify / Approval に戻す。task は `ready` / `in-progress` に上げる前に理想/現状/問題点/方針を補う。
- **既存 Inbox の整理:** [interactive-intake](.claude/skills/interactive-intake/SKILL.md) に従い分類。
- **Issue 検索(重複確認):** `mcp__github__search_issues`（query: `repo:<your-github-username>/<your-repo-name> <keywords>`）
- **Issue 作成:** `mcp__github__issue_write`（method: `create`, owner: `<your-github-username>`, repo: `<your-repo-name>`, title, body, labels）
- **ラベル同期:** [docs/labels.md](docs/labels.md) / [.github/labels.yml](.github/labels.yml) が正本。
- **当日の予定・タスク確認:** [today-issue-brief](.claude/skills/today-issue-brief/SKILL.md) に従い、GitHub Issueから読む。
- **長期記憶の蓄積:** [memory-keeper](.claude/skills/memory-keeper/SKILL.md) に従い、会話中に観察した好み・スタイル・行動パターンを `data/llm_wiki/sources/memories/` に自動蓄積。承認不要でプロアクティブに発動。
- **LLMWiki 構築:** [llm-wiki-build](.claude/skills/llm-wiki-build/SKILL.md) に従い、ユーザーから渡されたファイルだけを取り込む。
- **A-MEM パイプライン:** `scripts/ingest_second_brain_digest.py` / `scripts/backfill_agentic_memory.py` で保存前判断と既存記憶リンクの再構築を行う。
- **過去の思考・会話の参照:** キャリア・目標・人生相談など深いトピック時は `python3 scripts/search_wiki.py "<query>" --top-k 5` で LLMWiki を検索し、関連する過去の会話ダイジェストや思考があれば踏まえて応答する。

## 絶対に守ること(要約)

- 対話起点の Issue 追加では、**低リスクは軽量 capture を優先**し、高リスク案件だけ確認に戻す(AGENTS.md §3)。
- すべての Issue に **next_action**(不明なら `next_action: clarify goal`)。
- 人間判断(お金 / 人間関係 / 対外 / 大方針 / 削除 / 機微情報)は**勝手に進めない**。
- 機微情報を Issue・コミットに**書かない**。
- 定義外ラベルを**作らない**([docs/labels.md](docs/labels.md))。
- Issue を**物理削除しない**(`status:archived` で代替)。

## 出力スタイル

- 見出し・箇条書き・チェックリスト中心。推測は推測と明示。
- Issue 操作後は「やったこと / 人間の次アクション」を 1 行で添える。
- 確認質問は 1〜3 個に絞る。

## このリポジトリで Claude Code に期待される振る舞い

[evals/agent_behavior_eval.md](evals/agent_behavior_eval.md) を self-check に使う:
方針を勝手に変えない / 不明を不明と扱う / 確認を人間に戻す / 文脈を壊さない / 実行可能な next_action に落とす。
