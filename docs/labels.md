# Labels — GitHub ラベル設計

4 つの軸を `prefix:` で名前空間化する。意味は [taxonomy.md](taxonomy.md) を参照。
このファイルは正本(source of truth)。色は HEX(GitHub の `#` なし表記)。

機械同期用の定義は [`.github/labels.yml`](../.github/labels.yml) にあり、
GitHub Actions(`.github/workflows/sync-labels.yml`)で同期できる。

## category(緑系)

| name | color | description |
|------|-------|-------------|
| `category:work` | `0E8A16` | 仕事・業務 |
| `category:personal-dev` | `1D76DB` | 個人開発・サイドプロジェクト |
| `category:second-brain` | `5319E7` | 第二の脳・知識管理 |
| `category:learning` | `0052CC` | 学習・スキル習得 |
| `category:career` | `B60205` | キャリア戦略 |
| `category:life-admin` | `C2E0C6` | 生活・事務 |
| `category:relationship` | `F9D0C4` | 人間関係 |
| `category:travel` | `BFD4F2` | 旅行 |
| `category:health` | `0E8A16` | 健康・運動・睡眠 |
| `category:hobby` | `D4C5F9` | 趣味 |
| `category:gadget` | `006B75` | ガジェット・ウェアラブル・周辺機器 |
| `category:thinking` | `BFDADC` | 思考整理・アイデア |
| `category:meta-system` | `333333` | リポジトリ・AI 運用の改善 |

## type(青系)

| name | color | description |
|------|-------|-------------|
| `type:task` | `1D76DB` | 実行タスク |
| `type:idea` | `C5DEF5` | アイデア |
| `type:research` | `0052CC` | 調査 |
| `type:project` | `5319E7` | 複数タスクを含むプロジェクト |
| `type:memo` | `BFDADC` | メモ・記録 |
| `type:decision` | `D93F0B` | 意思決定 |
| `type:habit` | `0E8A16` | 習慣・繰り返し |
| `type:bug` | `B60205` | 不具合 |
| `type:improvement` | `A2EEEF` | 改善 |

## status(灰〜黄系)

| name | color | description |
|------|-------|-------------|
| `status:inbox` | `EDEDED` | 未整理 |
| `status:needs-triage` | `FBCA04` | 整理待ち |
| `status:ready` | `0E8A16` | 着手可能 |
| `status:in-progress` | `1D76DB` | 進行中 |
| `status:waiting` | `D4C5F9` | 待ち |
| `status:blocked` | `B60205` | ブロック |
| `status:done` | `C2E0C6` | 完了 |
| `status:archived` | `666666` | 保管 |

## priority(赤→灰のグラデーション)

| name | color | description |
|------|-------|-------------|
| `priority:P0-critical` | `B60205` | 今すぐ。乱発しない |
| `priority:P1-high` | `D93F0B` | 重要。今週中 |
| `priority:P2-medium` | `FBCA04` | 通常(デフォルト) |
| `priority:P3-low` | `C2E0C6` | いつか / 余裕があれば |

## 運用ルール

- ラベルは上記定義のみ使用する。新しい軸・値が必要なら `meta-system` の system Issue で提案 → 合意後にこのファイルと `labels.yml` を更新。
- 1 Issue に最低限: `category:*` 1 つ、`type:*` 1 つ、`status:*` 1 つ、`priority:*` 1 つ。
- prefix で名前空間を分けているので、同一軸の複数付けは原則しない(category のみ例外可)。
