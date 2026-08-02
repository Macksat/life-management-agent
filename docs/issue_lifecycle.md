# Issue Lifecycle — Issue の状態遷移

ステータスの定義は [taxonomy.md](taxonomy.md)、ラベルは [labels.md](labels.md) を参照。

## 状態遷移図

```
inbox
  └─▶ needs-triage
        └─▶ ready
              └─▶ in-progress
                    ├─▶ waiting ──┐
                    ├─▶ blocked ──┤
                    │   (解消後) ◀┘ in-progress に戻る
                    └─▶ done
                          └─▶ archived
```

## 各遷移の条件

| From → To | 条件 / トリガー |
|-----------|-----------------|
| (新規) → `inbox` | 未整理の思いつき・メモを intake で起票 |
| `inbox` → `needs-triage` | triage 対象として拾われた |
| `needs-triage` → `ready` | category/type/priority/owner と **next_action** が確定 |
| `ready` → `in-progress` | 着手した |
| `in-progress` → `waiting` | 外部・他者の応答待ち(理由を notes に記載) |
| `in-progress` → `blocked` | 依存 Issue・障害でブロック(related_issues に記載) |
| `waiting`/`blocked` → `in-progress` | 待ち/ブロックが解消 |
| `in-progress` → `done` | acceptance_criteria を満たした |
| `done` → `archived` | レビュー後、保管(原則削除しない) |

## ルール

- **物理削除はしない。** クローズは `done`、不要は `archived` で表現。削除は人間判断([operating_principles.md](operating_principles.md))。
- `ready` 以降は **next_action が必須**。不明なら `needs-triage` に戻し `next_action: clarify goal`。
- `waiting` / `blocked` は **理由と解消条件** を notes / related_issues に必ず書く。
- GitHub の Issue close は `done` または `archived` に到達したときに行う。

## AI が自動で行ってよい遷移

- `inbox` → `needs-triage`
- `needs-triage` → `ready`(分類と next_action の提案を伴う)
- 完了報告を受けての `in-progress` → `done` の **提案**

## 人間確認が必要な遷移 / 操作

- `done` → `archived` の最終確定(まとめてレビュー時に)
- Issue の物理削除(原則禁止)
- 大きな方針転換に伴う status 変更
