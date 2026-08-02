# Inbox — 未整理メモの一時置き場

ここは **まだ Issue にしていない思いつき・メモ** の一時置き場です。
最終的な情報の中心は GitHub Issue([README.md](../README.md))。Inbox は「捕まえて忘れない」ための前段です。

## 使い方

1. 思いついたら、ここに 1 ファイル(または下の running notes)で雑にメモする。
2. 形式は問わない。1 行でも OK。「何を / なぜ」が少しでもあると後が楽。
3. **放置しない。** Triage(下記)で Issue 化し、メモは消す。

## 書き方の目安

```
## <一言タイトル>
- 何を: …
- なぜ / 文脈: …
- (任意)次にやりたそうなこと: …
```

ファイル名は自由(例: `2026-05-31-langgraph-idea.md`)。雑でよい。

## Triage(Issue 化)

定期的に(Daily / Weekly Review)、ここのメモを Issue にする:

1. [interactive-intake](../.claude/skills/interactive-intake/SKILL.md) に従って整理する。
2. 重複を確認 → 分類 → goal / next_action 決定 → `gh issue create`。
3. **Issue 化したらメモを削除**(Inbox は空に近い状態を保つ)。

## ルール

- **機微情報を書かない**(パスワード・口座・住所・他者の個人情報など。[AGENTS.md](../AGENTS.md))。
- Inbox は溜める場所ではなく **通過点**。Weekly Review で必ず消化する。
- GitHub Issue の `status:inbox` ラベルと役割は同じ(どちらも「未整理の入口」)。
  - 口頭/チャットで AI に渡す → AI が `status:inbox` の Issue を作る。
  - 自分で書き留める → この `inbox/` に置く。
