# plans/

進行中の作業ごとに `PLANS.md` を置くためのディレクトリ。

`PLANS.md` は Issue の代替ではなく、作業中の文脈を束ねるハブとして使う。

## 使い分け

- **Issue**: 正本の状態管理、分類、`next_action`
- **`plans/*.md`**: 作業の進め方、判断、セッション要点、再開メモ
- **`data/llm_wiki/sources/conversation_memory/`**: セッション横断で共有したい短期会話文脈
- **`data/llm_wiki/sources/memories/`**: 長期で効く好み・事実・判断基準
- **`.plans/`**: 完了した `PLANS.md` の保存先

## 命名規約

- Issue がある場合: `issue-123-short-slug.md`
- Issue がない軽量作業: `YYYY-MM-DD-short-slug.md`

軽い単発作業では作らない。完了時は `Completion Review` を追記して `.plans/YYYY/` に移す。
