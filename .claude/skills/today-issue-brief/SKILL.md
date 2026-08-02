---
name: today-issue-brief
description: GitHub Issue から、指定日（既定は今日）の予定・期限・進行中タスクを読み取り、実行順を短く報告する。「今日の予定は？」「今日のタスクを見せて」「今日やることは？」などのときに使う。
---

# Today Issue Brief

GitHub Issue を正本として、指定日の予定とタスクを**読み取り専用**でまとめるスキル。

## 取得対象

- `due_date` が対象日の open Issue
- 期限超過の open Issue
- `status:in-progress` の open Issue
- `priority:P0-critical` / `priority:P1-high` の open Issue

Issue本文に `next_action` があれば併記し、なければ「next_action 未設定」と明示する。

## 手順

1. 日付指定がなければローカルの今日を `YYYY-MM-DD` で確定する。
2. GitHub MCP または `gh` CLI で対象リポジトリの open Issue を取得する。
3. 対象日の期限、期限超過、進行中、P0/P1 の順に重複を除いて並べる。
4. 最大3件の「まずやること」を、期限・優先度・`next_action` を根拠に提示する。
5. Issueの作成・更新や外部カレンダーの参照は行わない。必要なら別途ユーザー承認を得る。

## 出力形式

```markdown
## YYYY-MM-DD の予定とタスク

### まずやること
1. #123 タイトル — next: ...

### 期限超過
- #...

### 今日期限
- #...

### 進行中 / 高優先度
- #...
```
