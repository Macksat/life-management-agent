---
name: task-breakdown
description: 抽象的で大きい Issue や project Issue を、30 分〜2 時間で終わる具体的な次アクションや子タスクに分解する。「大きすぎて着手できない」「project を子タスクに割りたい」などのときに使う。single issue の分解と project planning を一つにまとめて扱う。
---

# Task Breakdown

`single issue の分解` と `project planning` の統合版。

## モード

- `single`: 1 つの Issue を、すぐ動ける次アクション列に分解する
- `project`: `type:project` を、マイルストーンと子タスクへ分解する

## 共通ルール

- `type:task` は理想 / 現状 / 問題点 / 方針が揃っていることを前提にする。欠けていれば [interactive-intake](../interactive-intake/SKILL.md) に戻す。
- goal と acceptance_criteria から逆算する。
- 1 アクションは 30 分〜2 時間。
- 動詞で始まる、すぐ着手できる表現にする。
- 依存関係と順序を明示する。
- 必要に応じて、人間判断が必要な作業か AI が進められる作業かを本文やコメントで明示する。

## single

1. goal と完了条件を確認する。
2. 大きければ 2〜4 個の中間成果に割る。
3. 30 分〜2 時間のアクションへ分解する。
4. `next_action` とチェックリストに反映する。

## project

1. goal とスコープを確認する。
2. 2〜5 個のマイルストーンへ割る。
3. 各マイルストーンを 30 分〜2 時間の子タスクへ分解する。
4. 親子関係、依存、クリティカルパスを明示する。
5. 親 Issue にマイルストーン一覧とタスクリストを反映する。

## チェック

- 1 アクションが大きすぎないか
- 順序が自然か
- 依存関係が見えるか
- すぐ動ける表現か
- project の場合、親子接続が明確か

## 関連

[interactive-intake](../interactive-intake/SKILL.md) · [task_breakdown_eval](../../../evals/task_breakdown_eval.md)
