---
name: research-to-action
description: 調査メモ(research / memo Issue)を、分かったこと・決めること・残課題に分け、実行可能な意思決定と task Issue に変換する。調査が一段落したとき、または research Issue を閉じる前に使う。
---

# Research to Action

調査メモを、実行可能な意思決定・タスクに変換する手順。

## 目的

research / memo を「読んで終わり」にせず、**決定(decision)と次タスク(task)** に落とす。

## 手順

1. **調査メモを読む** — 対象の research / memo Issue。
2. **要点を抽出** — 分かったことを 3〜5 点に圧縮。
3. **3 分類に振り分け**
   - **分かったこと(facts)** — 事実・結論。
   - **決めること(decisions)** — 選択が必要。トレードオフを併記。
   - **残課題(open questions)** — まだ不明。
4. **意思決定を扱う** — 軽微: AI が推奨を提示。重要 / お金 / 対外: `status:waiting`・`type:decision` で人間に戻す。
5. **タスク化** — 実行可能なものを task Issue に。理想/現状/問題点/方針 と 30 分〜2 時間粒度を満たす([task-breakdown](../task-breakdown/SKILL.md))。
6. **元 Issue を更新** — 要点サマリをコメント、related_issues で接続、status を `done` 提案。

## 出力フォーマット

```
## Research Summary: <topic>
### 分かったこと
- …
### 決めること(要判断)
- [ ] (human) A 案 vs B 案 — トレードオフ: …(推奨: A)
### 残課題
- …
### 生成タスク
- #NN (task) … next: …
```

## チェックリスト

- [ ] facts / decisions / open questions を分けたか
- [ ] 重要な決定を人間に戻したか
- [ ] 少なくとも 1 つの実行可能タスクを作ったか
- [ ] 元 Issue にサマリを残し接続したか

## NG 例

- ❌ 調査結果を貼るだけで決定・タスクを作らない
- ❌ 重要な意思決定を AI が勝手に確定する
- ❌ 「もっと調べる」だけで終わる(具体タスクなし)

## 関連

[task-breakdown](../task-breakdown/SKILL.md) · [workflows](../../../docs/workflows.md)
