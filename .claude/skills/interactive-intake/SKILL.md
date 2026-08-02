---
name: interactive-intake
description: ユーザーとの対話や未整理入力から GitHub Issue を整理・作成する。ユーザーが「整理して」「Issue にして」「タスク化して」「Inbox を捌いて」などと言ったときに使う。対話で作る dialog モードと、未整理項目を分類する triage モードを含む。
---

# Interactive Intake

`Issue 作成` と `triage` の統合版。実体フローは `dialog` と `triage` の 2 モードだけに整理する。

## モード

- `dialog`: 会話しながら不足情報を埋め、下書きを提示し、承認後に起票する
- `triage`: Inbox / 思いつき / `status:inbox` / `status:needs-triage` を分類し、`ready` に寄せる

## 共通ルール

- GitHub Issue の**作成・更新**は GitHub MCP サーバーを使う。**参照**は `gh` CLI やローカルキャッシュでもよい。
- 先に重複検索する。重複なら新規作成せず、既存 Issue への追記を提案する。
- `category / type / status / priority / owner` は、まず会話内容から AI が推定する。
- `status` の初期値は原則 `ready`。情報不足なら `needs-triage`。
- `priority` の初期値は原則 `P2-medium`。
- `type:task` は **理想 / 現状 / 問題点 / 方針** の 4 点セットが必須。
- 推測で埋めた箇所は `(推測)` と明示する。

## dialog

1. 何を Issue 化したいか把握する。
2. 重複を検索する。
3. 足りない情報だけを 1〜4 問ずつ聞く。
4. 下書きを全文提示する。
5. 明示的な承認を得る。
6. 承認後にのみ起票する。

## triage

1. 記録する価値があるか判断する。
2. 重複を検索する。
3. ラベルを先に推定する。
4. `goal / next_action / acceptance_criteria` を整える。
5. 情報不足なら `needs-triage`、十分なら `ready` にする。
6. 新規起票または既存 Issue 更新が必要なら、AGENTS.md の承認ルールに従う。

## task の最低条件

- 理想(ideal)
- 現状(current)
- 問題点(problem)
- 方針(approach)
- goal
- next_action

4 点セットが揃わない task は `ready` にしない。

## 関連

[task-breakdown](../task-breakdown/SKILL.md) · [AGENTS.md](../../../AGENTS.md)
