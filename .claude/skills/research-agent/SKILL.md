---
name: research-agent
description: type:research の ready Issue を自動で深掘りする。Web 検索で情報収集し、findings をコメントに投稿し、next_action を更新する。「リサーチを進めて」「調査 Issue を消化して」と言われたとき、または定期スケジュールで発動する。
---

# Research Agent — AI 自律リサーチ実行

`type:research` + `status:ready` の Issue を検出し、Web 検索で調査を実行、
findings を Issue コメントに投稿して next_action を更新する。

## 目的

人間が手を動かさなくても、AI が得意な **情報収集・整理** を自動で進め、
人間は「レビューして判断するだけ」の状態にする。

## いつ使うか

- ユーザーが「リサーチ進めて」「調査 Issue を消化して」と言ったとき
- 定期スケジュールで ready な research Issue を消化したいとき
- 特定の research Issue 番号を指定されたとき

## 対象 Issue の検出

`mcp__github__list_issues`（owner: `<your-github-username>`, repo: `<your-repo-name>`, state: `OPEN`, labels: `["type:research", "status:ready"]`）

parent Issue（`type:project`）がある場合は、parent の Goal・Scope も参照して文脈を理解する。
GitHub Issue の**参照**は、速度優先で `gh` CLI / ローカルキャッシュ / GitHub MCP のいずれを使ってもよい。**更新**は GitHub MCP を使う。

## 手順

### 1. 対象 Issue を読む

- Issue の **Goal**、**Next Action**、**Acceptance Criteria** を確認する。
- parent Issue（`## Parent` セクション）があれば読み、全体文脈を把握する。
- 既存コメントがあれば読み、途中まで進んでいる調査を重複しない。

### 2. 調査計画を立てる

Next Action と Acceptance Criteria から、**調べるべき問い** を 3〜5 個に分解する。

例:
```
Issue: オフィスチェアの選び方を整理する
Next Action: 価格帯・素材・調整機構の違いを調べて要約する
→ 問い:
  1. 価格帯によって何が変わるのか？
  2. メッシュ素材と布張りの違いは？
  3. 昇降・リクライニング機構のメリットは？
  4. 選び方で失敗しやすいポイントは？
  5. 初心者が知るべき基本用語は？
```

### 3. Web 検索で情報収集する

WebSearch / WebFetch を使い、各問いについて信頼性の高い情報を集める。

- **日本語と英語の両方** で検索する(日本語の情報 + 海外の一次情報)。
- 情報源の信頼性を意識する(メーカー公式、専門メディア、Wikipedia > 個人ブログ)。
- 矛盾する情報があれば両論併記し、断定しない。

### 4. findings をコメントに投稿する

調査結果を **構造化されたコメント** として Issue に投稿する。

```markdown
## Research Findings — YYYY-MM-DD

### 調べた問い
1. ...
2. ...

### 1. [問い1のタイトル]
- ...
- ...

### 2. [問い2のタイトル]
- ...

### 参考情報源
- [タイトル](URL) — 概要
- ...

### Acceptance Criteria 進捗
- [x] 達成した基準
- [ ] まだ未達の基準

### 残課題・次に調べること
- ...
```

### 5. Issue を更新する

- **next_action を更新** — 残課題があれば次の調査ステップに。全て完了なら `review findings`。
- **status を更新** — Acceptance Criteria が全て埋まった場合:
  - `status:in-progress` のまま、コメントで「レビュー待ち」と記載。
  - **`status:done` にはしない**。人間がレビューして done にする。
- ラベル更新は GitHub MCP ツールで行う。

```
# findings をコメントに投稿
mcp__github__add_issue_comment（owner: <your-github-username>, repo: <your-repo-name>, issue_number: <number>, body: "..."）

# status ラベルを更新（現在のラベルから status:ready を除き status:in-progress を加えたリストを渡す）
mcp__github__issue_write（method: update, owner: <your-github-username>, repo: <your-repo-name>, issue_number: <number>, labels: [現在のラベル一覧から差分更新]）
```

## 複数 Issue の処理順

1. parent Issue がある場合は **子 Issue の番号順**（M1 → M2 → ...）。
2. parent がない場合は **priority 順 → 番号順**。
3. 1 回の実行で処理する件数は **最大 5 件**。多い場合はユーザーに確認。

## 品質チェックリスト

- [ ] 調査は Issue の Goal / Acceptance Criteria に沿っているか
- [ ] Web 検索を実際に行い、推測や学習データだけで書いていないか
- [ ] 情報源を明記したか（URL 付き）
- [ ] 矛盾する情報は両論併記したか
- [ ] Acceptance Criteria の進捗を明示したか
- [ ] next_action を具体的に更新したか
- [ ] 人間の判断が必要な点を明示したか（お金・購入判断など）
- [ ] GitHub Issue の参照・更新に `gh` ではなく GitHub MCP サーバーを使ったか

## NG 例

- 学習データだけで回答し、Web 検索をしない
- 情報源を示さずに「〜と言われている」と書く
- Acceptance Criteria を無視して関係ない情報を大量に書く
- 購入判断など人間の領域を勝手に決める
- `status:done` に勝手に変える

## 関連

[research-to-action](../research-to-action/SKILL.md) · [issue_quality_eval](../../../evals/issue_quality_eval.md)
