# Eval: Issue Quality

Issue が「良い Issue」になっているかを評価する基準。triage 後・作成時の self-check に使う。

## 評価項目とスコア

各項目 0(不可)/ 1(一部)/ 2(良い)で採点。**合計 12 以上 かつ 0 が無い** で合格。

| # | 項目 | 0 | 1 | 2 |
|---|------|---|---|---|
| 1 | 背景(context)が明確 | なし | 一言だけ | なぜ必要かが分かる |
| 2 | 目的(goal)が明確 | なし | 曖昧 | 達成状態が 1 文で言える |
| 3 | 次アクションが具体的 | なし | 抽象的 | 動詞で始まりすぐ動ける |
| 4 | 完了条件がある | なし | 主観的 | 検証可能なチェックリスト |
| 5 | ラベルが適切 | 欠落 | 一部不適 | 4 軸が妥当 |
| 6 | 人間/AI 境界が明確 | 境界なし | 曖昧 | 本文や status で正しく判断分離 |
| 7 | 抽象的すぎない | 抽象的 | やや | 具体的 |
| 8 | 重複でない | 未確認 | 類似あり | 確認済み・重複なし |

## チェックリスト(簡易版)

- [ ] context がある(なぜ)
- [ ] goal が 1 文で言える
- [ ] next_action が動詞で始まり具体的(不明なら `clarify goal`)
- [ ] acceptance_criteria が検証可能
- [ ] category / type / status / priority が揃っている
- [ ] **type:task の場合、理想 / 現状 / 問題点 / 方針 の4点セットが揃っている**
- [ ] 人間/AI 境界([docs/operating_principles.md](../docs/operating_principles.md))が本文や status に反映されている
- [ ] 重複を検索した
- [ ] 機微情報が本文にない

## 良い例

```
title: FastAPI の依存性注入でDBセッションを共通化する
category: work / type: improvement / status: ready / priority: P2
context: 各エンドポイントでセッション生成が重複し保守しづらい
goal: Depends で DB セッションを一元管理できている
next_action: get_db 依存関数を作り 1 エンドポイントで置換する
acceptance_criteria:
  - [ ] get_db 依存関数が存在
  - [ ] 既存テストが green
```
→ 合格(具体・検証可能・境界明確)。

## NG 例

```
title: コードを綺麗にする
goal: (なし)  next_action: 頑張る  acceptance: (なし)
```
→ 不合格(項目 1〜6 が 0)。

## 関連

[interactive-intake](../.claude/skills/interactive-intake/SKILL.md) · [schemas/issue.schema.json](../schemas/issue.schema.json)
