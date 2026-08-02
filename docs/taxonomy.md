# Taxonomy — 分類体系

Issue を分類する 5 つの軸: **category / type / status / priority / owner**。
ラベルの色・説明は [labels.md](labels.md)、機械可読定義は [schemas/](../schemas/) を参照。

## category(どの領域か)

| category | 説明 |
|----------|------|
| `work` | 仕事・業務 |
| `personal-dev` | 個人開発・サイドプロジェクト |
| `second-brain` | 第二の脳エージェント構想・知識管理 |
| `learning` | 学習・スキル習得 |
| `career` | キャリア戦略・転職・評価 |
| `life-admin` | 生活・事務手続き |
| `relationship` | 人間関係 |
| `travel` | 旅行 |
| `health` | 健康・運動・睡眠 |
| `hobby` | 趣味 |
| `gadget` | ガジェット・ウェアラブル・周辺機器 |
| `thinking` | 思考整理・アイデアメモ |
| `meta-system` | このリポジトリ・AI 運用自体の改善 |

> 1 Issue につき category は原則 1 つ(主たる領域)。補助的に複数付けてもよい。

## type(何の種類か)

| type | 説明 |
|------|------|
| `task` | 実行タスク |
| `idea` | アイデア |
| `research` | 調査 |
| `project` | 複数タスクを含むプロジェクト |
| `memo` | メモ・記録 |
| `decision` | 意思決定が必要 / 記録 |
| `habit` | 習慣・繰り返し |
| `bug` | 不具合(コードや運用の) |
| `improvement` | 改善 |

## status(進行状態)

| status | 説明 |
|--------|------|
| `inbox` | 未整理。Inbox に入った直後 |
| `needs-triage` | 整理待ち。分類・次アクション決定が必要 |
| `ready` | 着手可能。次アクションが明確 |
| `in-progress` | 進行中 |
| `waiting` | 他者・外部要因の待ち |
| `blocked` | 依存・障害でブロック |
| `done` | 完了 |
| `archived` | 保管。閉じたが削除しない |

状態遷移は [issue_lifecycle.md](issue_lifecycle.md) を参照。

## priority(優先度)

| priority | 説明 | 目安 |
|----------|------|------|
| `P0-critical` | 今すぐ。落とすと重大な損失 | 乱発しない |
| `P1-high` | 重要。今週中 | |
| `P2-medium` | 通常 | デフォルト |
| `P3-low` | いつか / 余裕があれば | |

> 緊急度と重要度を分けて考える。P0/P1 を乱発しない。([evals/prioritization_eval.md](../evals/prioritization_eval.md))

## owner(誰が動くか)

| owner | 説明 |
|-------|------|
| `owner-human` | 人間が判断・実行する |
| `owner-ai` | AI が処理できる |
| `owner-both` | 協働(AI が下書き→人間が判断 等) |

判断基準は [operating_principles.md](operating_principles.md) の「人間判断と AI 判断の分離」を参照。
