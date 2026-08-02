# Operating Principles — 運用原則

このリポジトリを運用するうえでの不変のルール。人間も AI も従う。

## 基本原則

1. **GitHub は単なるタスク置き場ではなく、AI が参照できる行動 OS である。**
2. **すべての Issue は次アクション(next_action)に落とす。** 不明なら `next_action: clarify goal`。
3. **未整理情報は Inbox に入れてよいが、放置しない。** 定期レビューで必ず棚卸しする。
4. **AI に任せるものと人間が判断するものを分ける。** (下記)
5. **完璧な分類より、継続運用を優先する。** 迷ったら `needs-triage` に置いて先へ進む。
6. **抽象的な Issue を放置しない。** 抽象的なら分解するか、次アクションを `clarify goal` にする。
7. **重複を避ける。** Issue 作成前に既存を検索し、重複候補は提示する。

## 人間判断と AI 判断の分離

### AI が自動でやってよいこと

- Issue の下書き
- 分類(category / type)
- ラベル提案
- タスク分解
- 重複候補の提示
- 今日やることの提案
- 調査メモの整理
- 完了条件(acceptance_criteria)の案作成

### 人間確認が必要なこと

- 重要な意思決定
- お金に関わる判断
- 人間関係に関わる判断
- 仕事上の対外的な判断
- 大きな方針転換
- **Issue の削除**(原則 `archived` ラベルで代替。物理削除はしない)
- 機微情報の保存

判断に迷ったら、**AI は実行せず人間に戻す。** 不明点は不明として扱う。

## 情報の扱い

- **機微情報(パスワード・API キー・口座番号・住所・他者の個人情報など)を Issue 本文に書かない。**
- 金額や家計は概算・カテゴリ単位にとどめ、口座詳細は書かない。
- 他者が関わる人間関係の記述は、本人が特定できる形で残さない。
- 詳細は [AGENTS.md](../AGENTS.md) の「個人情報・機微情報の扱い」を参照。

## レビューのリズム

- **Today Issue Brief:** その日やることを GitHub Issue から読み取る。([today-issue-brief](../.claude/skills/today-issue-brief/SKILL.md))
- **Inbox Triage:** Inbox / `inbox` ラベルを Issue 化・分類する。([interactive-intake](../.claude/skills/interactive-intake/SKILL.md) の `triage` モード)

## 一貫性のための約束

- ラベルは [labels.md](labels.md) の定義のみ使う。新規軸が必要なら system Issue で提案。
- 状態遷移は [issue_lifecycle.md](issue_lifecycle.md) に従う。
- Issue の構造化フィールドは [schemas/issue.schema.json](../schemas/issue.schema.json) に従う。
