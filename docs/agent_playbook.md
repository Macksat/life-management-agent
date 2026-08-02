# Agent Playbook — AI エージェント実行プレイブック

AI エージェントが具体的にどう動くかの手順書。作業開始時に [AGENTS.md](../AGENTS.md) と合わせて読む。

## 起動時に読むもの(順番)

1. [AGENTS.md](../AGENTS.md) — 最重要ルール
2. 該当する [.claude/skills/](../.claude/skills/) の SKILL.md — 今回のタスクの手順
3. `python3 scripts/search_wiki.py "<query>" --top-k 3` — 長期目標や個人文脈が必要なときは、まず LLMWiki で候補を絞る
4. [docs/taxonomy.md](taxonomy.md) / [docs/labels.md](labels.md) — Issue 分類や更新が必要なときだけ読む
5. [docs/operating_principles.md](operating_principles.md) — 判断境界に迷うときだけ読む
6. 最近の会話文脈が必要なタスクでは、まず `timelines` や `topics` を LLMWiki で引く。圧縮や正本更新が必要なときだけ [data/llm_wiki/sources/conversation_memory/README.md](../data/llm_wiki/sources/conversation_memory/README.md) と該当する `daily` / `weekly` / `monthly` ファイルを読む
7. Slack の送信系操作では [data/llm_wiki/sources/memories/preferences.md](../data/llm_wiki/sources/memories/preferences.md) — 宛先・メンション・本文形式の最新ルール確認に必須
8. 個人文脈・過去の思考・最近の会話を参照したいときは、まず `python3 scripts/search_wiki.py "<query>" --top-k 3` で候補を絞る

## 軽量起動モード

- 通常ターンでは **`AGENTS.md` + 対象スキル + 直接必要な対象ファイル/Issue** だけで開始してよい。
- `user_context.md` は source-of-truth の更新が必要なときだけ読む。参照だけなら、まず LLMWiki の `people_self` / `topics` / `projects` / `issues` を使う。
- `conversation_memory` は、前ターンの続き・未解決論点・最近の約束事が必要なときだけ読む。
- 記憶参照が必要そうでも、最初から `data/llm_wiki/sources/memories/` や `data/llm_wiki/sources/second_brain/` を総読みせず、まず LLMWiki で候補を絞る。
- 事務作業・定型更新・単純実装では、記憶検索を省略してよい。
- 分類やラベル更新が無い単発回答では、taxonomy / labels の読込を省略してよい。
- 毎ターン同じ文書群を機械的に読み直さず、**今回の判断に必要な最小文脈**に絞る。

## 標準ループ(OODA 風)

```
1. Observe  : 入力 / 対象 Issue / 既存 Issue を読む
2. Orient   : category / type / status / priority を判定、重複を検索
3. Decide   : まず軽量に記録するか、その場で詳細化するかを決める
4. Act      : Issue 作成・更新 or 実行。結果をコメント
5. Verify   : acceptance_criteria と照合、status 遷移を提案
```

## 判断フローチャート

```
入力を受け取った
  ├─ 記録すべき? ──No──▶ 何もしない(理由を一言返す)
  │        │Yes
  │        ▼
  │   既存と重複? ──Yes──▶ 既存 Issue を提示し、追記を提案
  │        │No
  │        ▼
  │   高リスク案件? ──Yes──▶【質問】必要最小限だけ確認
  │        │No                    │
  │        ▼                      │
  │  【軽量起票】最小情報で作成 ◀──┘
  │        │
  │        ▼
  │  粗いままでよい? ──Yes──▶ inbox / needs-triage に置く
  │        │No
  │        ▼
  │  【整備】next_action と必要項目を補って ready へ
  │        ▼
  │   AI が実行可能? ──No──▶ status:waiting と判断メモで人間に戻す
  │        │Yes
  │        ▼
  │   実行 ──▶ コメント ──▶ status:done を提案(人間が確認)
```

> **既定フロー:** 対話起点の Issue 追加は「軽量起票 → 後で整備」を基本とする(AGENTS.md §3)。
> 重要判断・お金・人間関係・対外判断・機微情報のときだけ、質問や承認フローへ戻す。
> 手順詳細: [interactive-intake](../.claude/skills/interactive-intake/SKILL.md)。
>
> 当日の予定やタスクを確認するときは、[today-issue-brief](../.claude/skills/today-issue-brief/SKILL.md) を使い、GitHub Issueを読み取り専用で集約する。

## Issue を書くときの型

Issue には「軽量キャプチャ時の最低項目」と「ready へ上げるときの整備項目」がある。フィールド定義は [schemas/issue.schema.json](../schemas/issue.schema.json)。

### 軽量キャプチャ時の最低項目

```
title:               簡潔・具体的(動詞で始まると良い)
category:            taxonomy の category
type:                taxonomy の type
status:              taxonomy の status
priority:            P0/P1/P2/P3
goal:                いま分かる範囲で
next_action:         不明なら clarify goal
context/notes:       1〜数行の背景
```

### `ready` へ上げるときの整備項目

```
title:               簡潔・具体的(動詞で始めると良い)
category:            taxonomy の category
type:                taxonomy の type
status:              taxonomy の status
priority:            P0/P1/P2/P3
# --- type:task は以下「課題の4点セット」を必須 ---
ideal:               理想 / あるべき状態
current:             現状 / 今どうなっているか
problem:             問題点 / 理想と現状のギャップ
approach:            方針 / 解決の方向性
# ---------------------------------------------
context:             背景・なぜ(task 以外で使う補足。task は4点セットで代替可)
goal:                達成したい状態
next_action:         次の具体的な一手(必須)
acceptance_criteria: 完了条件(チェックリスト)
due_date:            あれば(YYYY-MM-DD)
related_links:       参考 URL
related_issues:      #123 等
notes:               補足・待ち理由など
```

> **task Issue は `ready` / `in-progress` に上げる前に「理想 / 現状 / 問題点 / 方針」を揃える。** 揃わなければ `needs-triage` で `next_action: clarify goal`。詳細: [AGENTS.md](../AGENTS.md) §9.1。

## やってよいこと / だめなこと(クイック)

| ✅ AI が自動で | ⛔ 人間に戻す |
|---------------|-------------|
| 下書き・分類・ラベル提案 | 重要な意思決定 |
| タスク分解・WBS 化 | お金の判断 |
| 重複候補の提示 | 人間関係の判断 |
| 今日やることの提案 | 対外的な仕事判断 |
| 調査メモの整理 | 大きな方針転換 |
| acceptance_criteria の案 | Issue の削除 |
| status の遷移提案 | 機微情報の保存 |

## 良い振る舞い(self-check)

実行前に自問する。詳細評価は [evals/agent_behavior_eval.md](../evals/agent_behavior_eval.md)。

- [ ] 勝手に大きな方針変更をしていないか
- [ ] 不明点を不明として扱っているか
- [ ] 必要な確認を人間に戻したか
- [ ] Issue の文脈を壊していないか
- [ ] 実行可能な next_action に落ちているか
- [ ] 機微情報を本文に書いていないか

## 出力スタイル

- 明確な見出し・箇条書き・チェックリストを使う。
- 推測は推測と明示する。確証がないときは確認質問を 1〜3 個に絞る。
- Issue 操作後は「何をしたか / 次に人間がやること」を 1 行で添える。

## Slack 送信前チェック

- `mcp__codex_apps__slack._slack_send_message` / draft / schedule など送信系ツールの前に、必ず [data/llm_wiki/sources/memories/preferences.md](../data/llm_wiki/sources/memories/preferences.md) を読む。
- Slack 送信時は、`preferences.md` に書かれた宛先ルール・メンションルール・本文ルールをそのまま適用する。
- ルールが曖昧または未記載なら、送信前にユーザーへ確認する。
- 送信承認を得るときは、「どの会話に」「どの形式で」送るかまで明示する。

## 会話記憶の扱い

- 最近の会話を前提に判断するタスクでは、まず LLMWiki の `timelines` を読む。
- 圧縮や source file 更新が必要なときだけ `data/llm_wiki/sources/conversation_memory/` の該当レイヤを読む。
- 直近 7 日は `daily`、同月の古い文脈は `weekly`、過去月は `monthly` を優先する。
- 長期で効く内容は `data/llm_wiki/sources/memories/` に昇格し、conversation memory だけに閉じ込めない。
- 会話に応答した後の `daily` 追記は、**重要ターン・未解決論点・次回参照価値が高いターンを優先**し、単純確認や雑談では省略してよい。広い統合や圧縮は週次・月次へ回す。

## GitHub 読み書きの方針

- **書き込み**: Issue/Label の作成・更新・close・コメント投稿は GitHub MCP を使う。
- **読み取り**: 検索・一覧・本文閲覧は、速度優先で `gh` CLI やローカルキャッシュを使ってよい。
- `gh` を使う場合も、判断根拠は Issue 本文・ラベル・コメントの事実に限定し、推測で補わない。
- タスク完了報告では、個別 Issue と Daily タスク管理 Issue のどちらか片方だけ更新して終えない。
