---
name: conversation-memory
description: Claude Code と Codex の会話で出た短期文脈を、日次・週次・月次に圧縮して `data/llm_wiki/sources/conversation_memory/` へ残す。「会話履歴を残して」「最近の会話を共有したい」「週次で会話をまとめて」「月次に圧縮して」など、会話の共有記憶を運用するときに使う。
---

# Conversation Memory

会話の全文ではなく、**次回参照に必要な要点だけ**を短期記憶として残す手順。デフォルトでは毎回答後に追記を**検討**するが、処理コストが高い場合は **skip を許容**し、必要なターンだけ記録する。

## 目的

- Claude Code と Codex の間で最近の会話文脈を共有する
- 長期記憶 (`data/llm_wiki/sources/memories/`) に上げる前の短期記憶を保つ
- 古い会話を圧縮し、容量を制御する

## 参照先

- ルール: [data/llm_wiki/sources/conversation_memory/README.md](../../../data/llm_wiki/sources/conversation_memory/README.md)
- 長期記憶: [memory-keeper](../memory-keeper/SKILL.md)
- 参照時の第一候補: LLMWiki の `timelines` / `topics`

## 手順

1. **対象期間を特定** — 今日の会話を足すのか、日次を週次に畳むのか、週次を月次に畳むのかを決める。
2. **既存文脈を確認** — 参照だけなら、まず LLMWiki の `timelines` を読む。source file の更新が必要なときだけ当日の `daily` から、**必要な session だけ**を見る。
3. **そのターンを要約** — ユーザー入力と AI の結論を 1 つの短い session 要約へ圧縮する。
4. **残す価値を判定** — 雑談や単発のやり取りは**skip 可**とし、次回参照価値がある要点だけ抽出する。
5. **重複を簡易判定** — 直近 1-2 session と同じ話題なら追記ではなく短い更新で済ませる。
6. **適切なレイヤへ記録** — 通常は `daily` にだけ記録する。`weekly` / `monthly` 更新は定例圧縮時に行う。
7. **昇格対象を分離** — 長期で効く好み・決定・事実だけ `data/llm_wiki/sources/memories/` 側へ移す。
8. **重い整理は後段へ送る** — 広い統合や圧縮は週次・月次の処理に任せる。

## レイヤ選択ルール

- **直近 7 日**: `data/llm_wiki/sources/conversation_memory/daily/YYYY/YYYY-MM-DD.md`
- **当月のうち、直近 7 日より前**: `data/llm_wiki/sources/conversation_memory/weekly/YYYY/YYYY-Www.md`
- **過去月**: `data/llm_wiki/sources/conversation_memory/monthly/YYYY/YYYY-MM.md`

## 抽出基準

### 残す

- 今後の提案や判断に効く話題
- その場で決まった方針
- 未解決の論点
- Issue や `data/llm_wiki/sources/memories/` に反映した内容
- 毎ターンの進行ログとして最低限必要な短い要約

### 残さない

- 単なる相槌や雑談
- 全文引用
- 既に他ファイルへ十分に反映済みで、短期記憶としての価値が薄いもの
- 機微情報
- 直前 session と実質同じ内容の新規追加

## 毎ターンのデフォルト運用

- ユーザーに応答するたびに、このスキルの観点で `daily` 更新を検討する
- 原則として「**重要なターンだけ記録する**」。雑談や単発確認は skip してよい
- 重要度が低いターンは 1 行要約でよい
- 同一話題が続く場合は、新規 session を増やさず既存 session を更新する
- 保存と同時に、不要部分の除外と簡易な重複確認だけを行う
- 広い重複統合や圧縮は週次・月次に回す
- 長期記憶への昇格は、価値が明確なものだけに絞る
- `## Day Summary` は**毎ターン更新しない**。日末または週次圧縮時だけ更新してよい

## 軽量モード

- 読む範囲は当日の `daily` に限定する
- 参照だけなら `daily` 直読より LLMWiki の `timelines` を優先する
- ただし機械的に末尾だけを見るのではなく、**今回の話題に関係する session だけ**を拾う
- 書く内容は `summary` 中心で、`decisions` / `open_loops` は必要時のみ更新する
- session を増やしすぎない。迷ったら既存 session の短い更新を優先する
- 既存 session 更新が面倒なら、`### HH:MM Notes` を1つ足すだけでよい
- `Day Summary` と既存 session の再整理はその場ではやらない
- 処理が重くなりそうなら、その場で完璧に整理せず週次に送る

## Fast Path

最優先は**追記処理そのものを軽くすること**。毎ターンは次の順で判断する。

1. そのターンが後で参照しそうかを 1 回だけ判定する
2. 参照価値が薄ければ **記録しない**
3. 参照価値があるが軽く済ませたいなら、関連する session があるかだけ見て、無ければ `summary` 1 行だけ追加する
4. `decisions` / `open_loops` / `linked_issues` は本当に必要なときだけ書く
5. `Day Summary` は触らない

次のようなターンは原則 skip でよい。

- 完了済み内容の単純確認
- あいづち
- すぐ流れる軽い依頼
- 既存 session を見れば十分な言い換え

## 参照の絞り方

軽量化は「読む行数を固定で減らす」ことではなく、**今回の話題に関係する記録だけ読む**ことで行う。

優先順位:

1. 今回の話題と同じキーワードを含む session
2. 同じ Issue 番号を含む session
3. 同じ日の直近 session
4. それでも無ければ新規 session を追加

つまり、`Swift` の話なら `Swift` を含む session を見に行き、`#10` の話なら `#10` を含む session を見に行く。末尾にあるかどうかは本質ではない。

## 圧縮ルール

- `daily` は 1 日 1 ファイルを基本とする
- 8 日目に入った `daily` は、同月なら `weekly` に統合する
- 月をまたいだ `weekly` は、翌月の整理時に `monthly` に統合する
- 同じ論点が複数ある場合は、追記せずに要約更新する

## チェックリスト

- [ ] 全文ではなく要点だけになっているか
- [ ] レイヤ選択が期間ルールに合っているか
- [ ] 同じ話題を無駄に増やさず、更新で済ませられているか
- [ ] 毎ターン処理で不要に広い読み込みや統合をしていないか
- [ ] `data/llm_wiki/sources/memories/` に上げるべき内容を混同していないか
- [ ] 機微情報を含めていないか
- [ ] 圧縮後の元ファイル整理が必要か確認したか

## NG 例

- ❌ 会話を丸ごとコピペして保存する
- ❌ 直近 7 日の詳細をいきなり月次に落とす
- ❌ 長期記憶にすべき内容を conversation memory だけに閉じ込める

## 関連

[data/llm_wiki/sources/conversation_memory/README.md](../../../data/llm_wiki/sources/conversation_memory/README.md) · [memory-keeper](../memory-keeper/SKILL.md)
