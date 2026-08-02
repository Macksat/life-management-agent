# Vision — このリポジトリの思想と目的

## 一言で

これは「個人の行動 OS」である。
思考・タスク・情報・学習・生活を **GitHub Issue を中心** に蓄積し、
**AI エージェントが参照・整理・行動提案できる形** に保つための基盤。

## 解決したい課題

- 思いつきやタスクが散らばり、行動につながらない
- メモは溜まるが、次に何をすればいいか分からなくなる
- 仕事・個人開発・生活・学習・趣味が別々のツールに分散している
- AI エージェントに渡しても、文脈・ルールがなく毎回ブレる

## 目指す状態

1. 思いついたことを AI に渡すと、適切に分類され Issue になる
2. すべての Issue が「次アクション」を持つ
3. Issue を見れば、人間でも AI でも次の一手が分かる
4. AI が処理してよいものと、人間が判断すべきものが明確に分かれている
5. 未整理情報は Inbox に入り、定期レビューで前に進む

## 設計原則(要約)

- **GitHub Issue が中心。** Markdown はルール・文脈・手順・評価基準の置き場。
- **AI が読む前提で書く。** 明確な見出し・箇条書き・判断基準・入出力例・NG例・チェックリスト。
- **完璧主義にしない。** まず運用できる MVP。分類の精度より継続運用。
- **人間判断と AI 判断を分離する。** ([operating_principles.md](operating_principles.md) 参照)
- **next_action を必須にする。** 不明なら `next_action: clarify goal` と明示。

## 非目標(やらないこと)

- Issue をただ大量に貯めること
- 巨大で複雑なアプリケーションを最初から作ること
- すべてを自動化すること(重要な意思決定は人間が握る)

## 関連ドキュメント

- 運用原則: [operating_principles.md](operating_principles.md)
- ユーザー文脈: [user_context.md](../data/llm_wiki/sources/memories/user_context.md)
- 分類体系: [taxonomy.md](taxonomy.md)
- ワークフロー: [workflows.md](workflows.md)
- Issue ライフサイクル: [issue_lifecycle.md](issue_lifecycle.md)
- エージェント運用: [agent_playbook.md](agent_playbook.md)
- LLMWiki 連携仕様: [llm_wiki.md](llm_wiki.md)
