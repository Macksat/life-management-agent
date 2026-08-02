# Conversation Memory Sources

`data/llm_wiki/sources/conversation_memory/` は、Claude Code / Codex 間で共有する短期会話文脈の正本。

## レイヤ

- `daily/YYYY/YYYY-MM-DD.md`: 直近 7 日の会話要約
- `weekly/YYYY/YYYY-Www.md`: 当月の週次圧縮
- `monthly/YYYY/YYYY-MM.md`: 過去月の月次圧縮
- `templates/`: 各レイヤのテンプレート

## ルール

- 長期で効く内容は `memories/` へ昇格する
- まずは LLMWiki の `timelines` / `topics` を優先し、source file を直接読むのは更新時や圧縮時だけにする
- 雑談や単発確認は無理に保存しない
- 機微情報は書かない
