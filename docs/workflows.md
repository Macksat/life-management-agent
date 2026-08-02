# Workflows — ワークフロー

各ワークフローの詳細手順は [.claude/skills/](../.claude/skills/) の各 SKILL.md にある。ここは全体像と接続を示す。

```
対話 ──▶ [Quick Capture] ──▶ inbox / needs-triage ──▶ [Triage / Detail Up]
   │                                                    │
   └─(高リスク / 要判断)─▶ [Clarify + Approval] ────────┘
                                                        │
       ┌────────────────────────────────────────────────┤
       ▼                 ▼                 ▼            ▼
 [Today Issue Brief] [Task Breakdown] [Research→Action] [PLANS.md]
       │                                  │
       ▼                                  ▼
 GitHub Issues                    AI Execution / Human Decision
```

## 0. 課題追加 — Capture First

1. **Capture** — タイトルと最小限の文脈でまず記録する。
2. **Classify** — category / type / priority / 初期 status を付ける。
3. **Create** — 低リスクならそのまま起票する。
4. **Refine Later** — 詳細化は必要になった時点で行う。

→ 詳細: [interactive-intake](../.claude/skills/interactive-intake/SKILL.md)

## 1. ユーザー提供ファイルから LLMWiki を構築

1. ユーザーが添付またはパスで明示したファイルだけを読む。
2. 必要なら second brain の digest に整形して `sources/` に保存する。
3. A-MEM を通して登録し、LLMWiki を再構築する。
4. Issue 候補の抽出は行ってよいが、起票・更新は承認を得てから行う。

→ 詳細: [llm-wiki-build](../.claude/skills/llm-wiki-build/SKILL.md)

## 2. Issue 整理(Triage)

1. `status:inbox` / `status:needs-triage` を集める。
2. category / type / priority を判定する。
3. 重複候補を検索して提示する。
4. **next_action** を決める。不明なら `clarify goal` とする。
5. task なら必要に応じて 4 点セットを補う。

→ 詳細: [interactive-intake](../.claude/skills/interactive-intake/SKILL.md) の `triage` モード

## 3. 当日の予定・タスクを確認

1. 指定日（既定は今日）の期限、期限超過、進行中、P0/P1 Issue を読む。
2. Issue 本文の `next_action` を添えて、まずやることを最大3件に絞る。
3. Issueの作成・更新は行わない。

→ 詳細: [today-issue-brief](../.claude/skills/today-issue-brief/SKILL.md)

## 4. Research to Action

1. research / memo を読む。
2. 分かったこと・決めたこと・残課題を抽出する。
3. 意思決定と task に変換する。

→ 詳細: [research-to-action](../.claude/skills/research-to-action/SKILL.md)

## 5. Project Planning

1. project Issue の goal を確認する。
2. マイルストーンを WBS に分解する。
3. 各タスクを子 Issue にし `related_issues` で接続する。

→ 詳細: [task-breakdown](../.claude/skills/task-breakdown/SKILL.md) の `project` モード

## 6. PLANS.md

継続作業や設計判断のある作業では、Issue と別に `plans/*.md` の `PLANS.md` を置いてよい。

→ 詳細: [plans-md](../.claude/skills/plans-md/SKILL.md)

## 7. AI Agent Execution

1. next_action と acceptance_criteria を確認する。
2. AI が処理できる範囲か判定する。
3. 継続作業なら、必要に応じて `PLANS.md` に進捗・判断・再開メモを追記する。
4. 実行結果を Issue にコメントし、status 更新を提案する。
5. 範囲外・要判断は Human Decision へ戻す。

## 8. Human Decision Required

重要な意思決定、お金、人間関係、対外的判断、大方針転換、Issue削除、機微情報は人間の明示判断を得る。
