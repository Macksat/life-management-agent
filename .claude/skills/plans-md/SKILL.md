---
name: plans-md
description: AI との継続作業を `plans/*.md` の PLANS.md に残し、再開しやすくする。2 ターン以上にまたがる作業、設計判断がある作業、後で再開する作業、`PLANS.md` や `.plans` を作りたいときに使う。
---

# PLANS.md

`PLANS.md` は Issue の代替ではなく、作業中の文脈を束ねるハブ文書。

## 目的

- AI と進めた作業の計画、判断、未解決事項、再開メモを 1 ファイルにまとめる
- 次回再開時に、Issue / conversation memory / long-term memory を横断せず必要文脈に到達しやすくする
- 完了後レビュー付きで `.plans/` に保存し、次の Skill や automation の材料にする

## いつ使うか

- 2 ターン以上にまたがる作業
- 設計判断やトレードオフがある作業
- 後で再開する可能性が高い作業
- AI に同じ前提説明を繰り返しそうな作業
- `PLANS.md` / `.plans` を明示的に求められたとき

単発作業や軽微な修正では、Issue や `conversation_memory` だけで済ませてよい。

## 手順

1. 対象作業を特定する。Issue 番号があればそれを起点にし、なければ日付ベース名で仮置きする。
2. `plans/_template.md` を基に `plans/<name>.md` を作る。
3. `Goal`、`Current State`、`Plan`、`Next Restart` を優先して埋める。
4. 重要な分岐は `Decision Log` に `decision / reason / impact` で残す。
5. 会話は全文ではなく、session 単位の `summary / changed / blockers` だけ残す。
6. 長期で効く好み・事実・判断基準は `memories/` に、セッション横断の短期共有は `conversation_memory` に分ける。
7. 完了時は `Completion Review` を書き、`.plans/YYYY/` に移す。

## 完了条件

- [ ] 作業中の文脈を 1 ファイルで再開できる
- [ ] 重要な判断が `Decision Log` に残っている
- [ ] 次回の最初の一手が `Next Restart` にある
- [ ] 完了時は `Completion Review` が書かれている
