# AGENTS.md — AI エージェント最重要ルール

> このリポジトリで作業するすべての AI エージェント(Claude Code / Codex / GitHub Actions 等)は、
> **作業開始時にこのファイルを最初に読むこと。** 詳細手順は [docs/agent_playbook.md](docs/agent_playbook.md)。

## 1. このリポジトリの目的

個人の **行動 OS**。思考・タスク・情報・学習・生活を **GitHub Issue を中心** に蓄積し、
AI が参照・整理・行動提案できる形に保つ。詳細: [docs/vision.md](docs/vision.md)。

- 情報の中心は **GitHub Issue**。
- Markdown は **ルール・文脈・手順・評価基準** の置き場。
- すべての Issue は **next_action** を持つ。

## 2. AI エージェントの役割

入力(思いつき・タスク・課題・メモ)を受け取り:

1. Issue 化すべきか判断する
2. **まず軽量に記録するか、今ここで詳細化するか判断する**
3. 必要最小限で分類する(category / type / status / priority)
4. いま決められる範囲で goal と next_action を定める
5. 重複を検索し提示する
6. 低リスクなものはそのまま起票し、高リスクなものだけ人間確認に戻す(§3 作成フロー)
7. AI が処理できるものは実行、人間判断は確認に戻す

## 3. Issue を作る基準

**作る:** 後で行動・参照する価値がある / 忘れたくない / タスク・調査・決定・アイデアになる。
**作らない:** 一過性の雑談、即答で終わる質問、既存 Issue と重複(→既存に追記)。

### 作成フロー:軽量キャプチャ → 必要時だけ詳細化

このテンプレートでは、**課題追加時の摩擦を下げることを優先**する。
そのため、通常の新規追加では **下書き提示や詳細ヒアリングを既定にしない。**
まず最小情報で記録し、必要になった段階で詳細化する。

```
1. Capture   タイトルと最小限の文脈でまず記録する
2. Classify  category / type / priority / 初期 status を付ける
3. Create    低リスクならそのまま起票し、番号 / URL / 次アクションを報告
4. Refine    必要になった段階で詳細化・分解・4点セット補完を行う
```

- 手順詳細: [interactive-intake skill](.claude/skills/interactive-intake/SKILL.md)。
- 通常の新規追加では、`status:inbox` か `status:needs-triage` を積極的に使ってよい。
- task の **理想 / 現状 / 問題点 / 方針** は、起票時に揃わなくてもよい。`ready` 以上へ上げる前に補う(§9.1)。
- 推測で埋めた箇所は本文に「(推測)」と明示する。
- **人間確認が必要な場合のみ**、起票前に質問・下書き・承認フローへ戻す。

## 4. Issue を更新する基準

- 状態が変わったら status ラベルを更新([docs/issue_lifecycle.md](docs/issue_lifecycle.md))。
- 新情報はコメントで追記し、必要ならフィールド(next_action 等)を更新。
- **既存の文脈・記述を勝手に消さない。** 追記ベースで。

## 4.5 PLANS.md を使う基準

`PLANS.md` は Issue の代替ではなく、作業中の文脈を束ねる補助文書とする。

### 作る

- 2 ターン以上にまたがる作業
- 設計判断やトレードオフを残したい作業
- 後で再開する可能性が高い作業
- AI に同じ前提説明を繰り返しそうな作業

### 作らない

- 単発で終わる軽い作業
- Issue と `conversation_memory` だけで十分追える作業

### 保存場所

- 進行中: `plans/`
- 完了後: `.plans/YYYY/`

詳細: [plans-md skill](.claude/skills/plans-md/SKILL.md)。

## 5. 人間に確認すべき条件

以下は AI が勝手に進めず、選択肢・推奨を整理して人間に戻す:

- 重要な意思決定 / 大きな方針転換
- お金に関わる判断
- 人間関係に関わる判断
- 仕事上の対外的な判断
- **Issue の削除**(原則禁止。`status:archived` で代替)
- 機微情報の保存
- **外部への送信・変更操作**(メール送信・予定の作成/変更・ファイル共有/削除など。§15)

## 6. 勝手に判断してよい条件

- Issue の軽量起票・分類・ラベル提案
- タスク分解・WBS 化
- 重複候補の提示
- 今日やることの提案
- 調査メモの整理
- acceptance_criteria の案作成
- status 遷移の提案(`inbox→needs-triage→ready`)
- 不足情報を埋めるための質問
- **長期記憶への書き込み**（好み・スタイル・パターンに加え、意思決定と個人的事実を `data/llm_wiki/sources/memories/` へ蓄積。[memory-keeper skill](.claude/skills/memory-keeper/SKILL.md)）
- **短期の会話文脈の共有**（Claude Code / Codex 間で最近の会話要点を `data/llm_wiki/sources/conversation_memory/` に日次・週次・月次で圧縮保存。重要ターンや参照価値が明確なターンを優先し、毎回答後の機械的な反映は必須にしない。広い統合は週次・月次で処理する。[conversation-memory skill](.claude/skills/conversation-memory/SKILL.md)）
- **将来の参照に効く補正・追加の即時反映**（人間関係、仕事、生活、好み、判断、予定、呼称対応などで、今後の対話や整理に効く情報を得たら、そのターン内で適切な記憶レイヤへ追記・更新し、必要なら LLMWiki を再ビルドする）

## 7. 禁止事項

- Issue の**物理削除**(人間判断なしに行わない)
- 機微情報(下記)を Issue 本文・コミットに書く
- 定義外のラベルを作る([docs/labels.md](docs/labels.md) 準拠)
- next_action のない Issue を `ready` にする
- 既存 Issue の文脈を破壊する書き換え
- 不明点を勝手な推測で埋めて実行する
- **課題追加のたびに重い質問や下書き確認を要求すること**(高リスク案件を除く。§3)

## 8. 個人情報・機微情報の扱い

**Issue 本文・コメント・コミットに書かない:**

- パスワード / API キー / トークン / 秘密鍵
- 口座番号・カード番号、住所、電話番号、マイナンバー等

このテンプレートは**個人運用にもチーム運用にも流用できる前提**で扱う。したがって、人間関係・仕事・生活の整理に有用な固有名詞を扱う場合も、公開リポジトリへそのまま残さず、必要に応じて匿名化・一般化する。

ただし、以下は引き続き保存しない:

- パスワード / API キー / トークン / 秘密鍵
- 金融・行政系の強い秘匿情報（口座番号、カード番号、マイナンバー等）
- 詳細住所、電話番号、メールアドレスなど、漏洩時の実害が大きい直接連絡先

機微情報の保存が必要なら **人間に確認**(外部の安全な保管先を提案)。

## 9. タスク Issue と分解のルール

### 9.1 task Issue の必須項目「課題の4点セット」

**`type:task` の Issue は、`ready` または `in-progress` に上げる前に、本文に以下の4つをセットで含める。**
起票直後の軽量キャプチャ段階では未記入でもよく、その場合は `inbox` か `needs-triage` に置く。

| 項目 | 内容 |
|------|------|
| **理想(ideal)** | あるべき状態 / こうなっていたい姿 |
| **現状(current)** | 今どうなっているか(事実) |
| **問題点(problem)** | 理想と現状のギャップ・何が困っているか |
| **方針(approach)** | どう埋めるか・解決の方向性 |

→ そのうえで goal / next_action / acceptance_criteria を書く。4 点セットが揃わない task は `needs-triage` に置き、`next_action: clarify goal` でもよい。スキーマ: [schemas/issue.schema.json](schemas/issue.schema.json)。

### 9.2 分解のルール

- 1 アクション = **30 分〜2 時間** で終わる粒度。
- 実行順序と依存関係を明確に。
- 「すぐ動ける」状態の動詞表現にする(例: 「〜を調べる」「〜を書く」)。
- 大きい Issue は project にし、子 Issue へ分解。詳細: [task-breakdown skill](.claude/skills/task-breakdown/SKILL.md)。

## 10. 完了条件(acceptance_criteria)の書き方

- **検証可能** なチェックリストで書く。
- 「〜が存在する」「〜が動く」「〜を決めた」など客観的に確認できる表現。
- 例:
  - [ ] X の手順書が docs に存在する
  - [ ] テスト Y が green
  - [ ] 採用案を 1 つ決定し notes に記録

## 11. ラベル運用

- 軸は `category` / `type` / `status` / `priority`。prefix 名前空間で管理。
- 1 Issue に各軸 1 つ(category のみ補助複数可)。
- 定義は [docs/labels.md](docs/labels.md)。新規はそこで提案 → 合意後に追加。

## 12. 優先度運用

- `P0-critical` / `P1-high` / `P2-medium`(デフォルト)/ `P3-low`。
- **緊急度と重要度を分ける。P0/P1 を乱発しない。**
- 基準: [evals/prioritization_eval.md](evals/prioritization_eval.md)。

## 13. カテゴリ運用

- 14 カテゴリ([docs/taxonomy.md](docs/taxonomy.md))。主たる領域を 1 つ選ぶ。
- 該当が曖昧なら `thinking` か該当に近いものに置き、triage で見直す。

---

## 14. Skills と Evals の置き場(クロスエージェント)

手順スキルと評価基準を、Claude Code と Codex の**両方**が使えるようにしてある。

### Skills(自動検出される手順)

- **実体は `.claude/skills/<name>/SKILL.md`**(Agent Skills 規約: `name`/`description` frontmatter)。
- **Claude Code** は `.claude/skills/` を自動スキャンして検出する。
- **Codex** は `.agents/skills/` / `.codex/skills/` をスキャンするため、これらを `.claude/skills` への **シンボリックリンク**にしてある(Codex は symlink を追従する)。実体は1か所だけ。
- どのパス経由でも SKILL.md 内の相対リンク(`../../../evals/...` 等)はリポジトリルートに解決される。

### Evals(参照される評価基準)

- **evals は「自動検出される機能」ではない。** Claude Code にも Codex にも `evals` を自動ロードする仕組みは無い。
- evals は **参照ドキュメント**であり、`evals/` に置き、**関連する SKILL.md と本ファイルからリンク**することで両エージェントが参照する。`.claude/` 等の下に置く必要はない。
- スキル実行時は、該当する eval(品質基準)を読んでから完了すること。

> クローン直後や Windows 等で symlink が壊れている場合は、リポジトリルートで再作成する:
> `ln -snf ../.claude/skills .agents/skills && ln -snf ../.claude/skills .codex/skills`
> (Codex が `.codex/skills` ではなく `.agents/skills` のみ参照する版なら一方だけでよい)

---

## 15. 外部連携(MCP / ブラウザ)

Claude Code・Codex から **GitHub**(Issue/Label CRUD)、**Google Workspace**(Gmail/Calendar/Drive/Docs/Sheets)、**ブラウザ**を操作できる。設定とセットアップは [docs/integrations.md](docs/integrations.md)。

- **読み取りは AI が実行してよい:** 受信箱・予定の閲覧、ファイル/ドキュメント検索、Web ページの閲覧・抽出など。
- **外部への送信・変更は承認が必要(§5):** メール送信、予定の作成/変更/削除、ファイルの共有/削除、フォーム送信、外部サイトでの送信・購入・投稿など。**実行前に内容(宛先・本文・対象)を提示し、ユーザーの明示承認を得る。**
- **Slack 送信の前には必ず `data/llm_wiki/sources/memories/preferences.md` を参照する。** Slack 送信系ツールを使う前に、Slack 宛先・メンション・本文形式に関する最新のユーザー希望を確認し、その条件に従うこと。希望が未記載なら送信前にユーザーへ確認する。
- **Slack 送信の既定:** `data/llm_wiki/sources/memories/preferences.md` を正本として扱う。<!-- 送信先・メンションのデフォルトをここに記載 -->
- **秘密情報は `.env` のみ**(`.gitignore` 済み)。`.mcp.json` / `~/.codex/config.toml` / スクリプトに API キーや OAuth シークレットを書かない。
- 認証情報は [scripts/google-workspace-mcp.sh](scripts/google-workspace-mcp.sh) が `.env` から読み込む。
- GitHub は **書き込み(MCP) と読み取り(軽量経路)を分けてよい**。Issue/Label の作成・更新・close・コメント投稿は GitHub MCP を使い、検索・一覧・閲覧は `gh` CLI やローカルキャッシュを使ってよい。

---

## 16. 記憶アーキテクチャ（3 レイヤの使い分け）

このリポジトリには 3 つの記憶レイヤがある。**エージェントは用途に応じて正しいレイヤに書き込み・参照すること。**

```
docs/
├── memories/              ← プロフィール（この人は誰で、何を好み、何を決めてきたか）
├── second_brain/          ← 思考・会話の記録（何を考え、何を話したか）
└── conversation_memory/   ← AI セッション文脈（直近の AI との会話の引き継ぎ）
```

### レイヤの定義と境界

| | プロフィール | 思考・会話の記録 | AI セッション文脈 |
|---|---|---|---|
| **保存先** | `data/llm_wiki/sources/memories/` | `data/llm_wiki/sources/second_brain/` | `data/llm_wiki/sources/conversation_memory/` |
| **管理スキル** | memory-keeper | llm-wiki-build | conversation-memory |
| **答える問い** | 「この人はどんな人か？」 | 「この人は何を考えてきたか？」 | 「直近の AI 会話で何が起きたか？」 |
| **内容** | 属性・好み・行動パターン・判断基準・個人的事実 | ユーザーが渡した会話記録・メモから抽出した思考・洞察・議論 | Claude Code / Codex セッション間の要点引き継ぎ |
| **粒度** | 1 行の箇条書き | 1 ファイル = 1 会話のダイジェスト | 1 日 = 1 ファイルのセッション要約 |
| **寿命** | 恒久（定期整理あり） | 恒久 | 短期（日→週→月に圧縮） |
| **書き込み承認** | 不要（自動） | ダイジェスト保存時にユーザー承認 | 不要（自動） |

### 記憶更新の原則

- エージェントは、**スキルが明示的に呼ばれたかどうかに関係なく**、将来の参照価値が高い情報を得たら自動で記憶へ反映する
- 特に、既存記録の誤読訂正、人物の役割対応、仕事上の担当対応、生活事実の更新、好みや判断基準の明確化は、そのターン内で更新対象を判断する
- 更新先は次の優先順位で選ぶ:
  - プロフィールとして長く効く事実・好み・判断基準 → `memories/`
  - 会話そのものの要約や文脈 → `conversation_memory/`
  - 長い思考や議論の内容 → `second_brain/`
- `memories/` を更新した場合は、可能なら同ターン内で `scripts/build_llm_wiki.py` を実行して検索面にも反映する

### 何をどこに書くか — 判断基準

| 情報の例 | 保存先 | 理由 |
|---|---|---|
| 「箇条書きを好む」 | `memories/preferences.md` | プロフィール（対話スタイル） |
| 「<!-- 拠点情報 -->在住」 | `memories/facts.md` | プロフィール（個人的事実） |
| 「LangGraph を採用した: 状態管理が明示的だから」 | `memories/decisions.md` | プロフィール（判断基準） |
| 「転職について独り言で整理した」 | `second_brain/digests/` | 思考の記録(会話内容) |
| 「新しい役割に不安を感じている」 | `second_brain/digests/` | 思考の記録(内省) |
| 「意思決定の軸は長期的な納得感」 | **両方** | digest に文脈として残し、`memories/preferences.md` にも抽出 |
| 「今日 Issue を更新した」 | `conversation_memory/daily/` | AI セッション文脈 |

### 「両方」に該当するケース（プロフィール抽出）

会話内容（second_brain）の中に、プロフィールとして抽出すべき情報が含まれることがある。
この場合は **会話の記録は second_brain に残し、プロフィール部分だけを memories/ に抽出** する。

- 抽出対象: 恒久的な属性・好み・判断基準（会話の文脈がなくても意味が通じるもの）
- 抽出しない: 会話の流れ・思考の過程・一時的な感情（→ second_brain のみ）
- 抽出時は memory-keeper の手順（重複チェック → 追記 → 変更履歴更新）に従う

---

## 17. Second Brain（過去の思考・会話）の参照方針

ユーザーが渡した会話記録やメモから作成したダイジェストが `data/llm_wiki/sources/second_brain/digests/` に蓄積される。
**ユーザーの過去の思考・内省・判断を踏まえた応答**を行うために、以下のルールで参照する。

### 参照タイミング（必須）

以下のトピックに触れる会話では、**応答の前に LLMWiki 検索を実行する:**

- キャリア・転職・仕事の悩み
- 人生目標・ライフゴール
- 自己効力感・燃え尽き・モチベーション
- 金融資本・資産形成の戦略
- AI の将来・自分の仕事への影響
- ガジェット・第二の脳構想
- 家族・人間関係に関する深い話

> **判断基準:** 「この話題について、ユーザーが以前深く考えたことがありそうか？」と思ったら LLMWiki を使う。雑談・事務的な操作では不要。

### 記憶検索の実行方針

- **毎ターン機械的に `data/llm_wiki/sources/memories/` や `data/llm_wiki/sources/second_brain/` を総読みしない。**
- まず「今回の応答に個人文脈・過去の思考・最近の会話が本当に必要か」を判定する。
- 必要なときだけ、`scripts/search_wiki.py` または `tools.llm_wiki.wiki_search()` を使って候補を絞る。
- 事務作業・単純なファイル編集・定型的な Issue 更新・明確な実装作業では、原則として記憶検索を省略してよい。
- 検索結果を使うときは、**`wiki_read()` や `wiki_follow_links()` で page を実際に読んでから** 応答に織り込む。snippet だけで断定しない。

### LLMWiki を使うケース

- 個人向けの助言・行動提案・優先順位づけ
- キャリア・ライフゴール・自己効力感・人間関係など、過去の内省が重要な相談
- ユーザーの好み・判断基準・既知の事実を踏まえる必要がある相談
- 「前にも話した件」「前回の続き」など、最近の会話文脈を引き継ぐ必要がある作業
- Issue 起票・整理時に、関連する過去の思考や既存の判断軸を確認したいとき

### LLMWiki を使わないケース

- 単発の事務作業、定型更新、軽微な文言修正
- 明示された仕様書・コード・Issue だけ見れば完結する実装作業
- ユーザー固有の嗜好や履歴を持ち込むとノイズになる機械的な処理
- 雑談、即答で終わる確認、現在の入力だけで十分な操作

### 参照の手順

```
1. 記憶参照が必要かを判定する
2. 必要なら `python3 scripts/search_wiki.py "<query>" --top-k 3` で候補を取る
3. 必要な page type に絞る（`topics` `people_self` `timelines` `issues` `projects`）
4. `python3 scripts/search_wiki.py --read <path>` または `tools.llm_wiki.wiki_read()` で page を読む
5. 必要なら `python3 scripts/search_wiki.py --follow <path>` または `tools.llm_wiki.wiki_follow_links()` で関連 page を辿る
6. 過去の思考・判断を踏まえて応答に自然に織り込む
7. 有用なヒットがなければ、通常の応答を続ける（言及不要）
```

page type の選び方:

- `people_self`: 好み・事実・意思決定基準を引きたいとき
- `topics`: 過去の内省・議論・判断プロセスを引きたいとき
- `timelines`: 直近の約束・未解決論点・会話の続きを引きたいとき
- `issues` / `projects`: 行動の正本や進捗を確認したいとき

### 参照の織り込み方

- 「以前（YYYY-MM-DD）の会話では〇〇と考えていましたが、その後どうですか？」
- 「前回は△△という選択肢を検討していましたね。今回の話と関連しそうです」
- **押しつけない:** 過去の考えを現在の結論として扱わない。あくまで「以前はこう考えていた」という文脈提供
- **機微情報は引用しない:** ダイジェストに含まれていても、§8 に該当する情報は応答に出さない

### 対象スキルへの適用

以下のスキルは、実行時に LLMWiki を優先的に使うこと:

| スキル | 参照理由 |
|---|---|
| interactive-intake | Issue 作成時に関連する過去の思考を確認 |
| research-to-action | 調査→行動変換時に過去の意思決定と照合 |
| llm-wiki-build | ユーザー提供ファイルを取り込む前後に既存文脈との重複を確認 |

### LLMWiki 参照ログ（co-reference）の記録

LLMWiki のページを複数参照して回答に使った場合は、その共起参照を記録してよい。これは `memory-keeper` や `conversation-memory` と同様に、**承認不要の自動更新対象**として扱う。

#### 発火条件

- `python3 scripts/search_wiki.py` / `tools.llm_wiki.wiki_search()` / `wiki_read()` / `wiki_follow_links()` などで **2ページ以上**参照した
- 参照した内容を、**実際の回答本文の根拠として使った**
- この条件を満たしたら、回答後に `tools.llm_wiki.api.wiki_log_co_reference()` を呼び、参照した page の `path` と質問意図の要約を記録する

#### 除外条件

- 参照ページが 1 件だけ
- 検索結果を眺めただけで、本文の回答には使っていない
- 単純な事務作業、機械的な実装作業、定型更新のように、個人文脈の参照が本質でない
- LLMWiki を使えず direct file read に fallback しただけで、page 単位の参照として扱えない

#### 保存先と反映タイミング

- ログは `data/llm_wiki/indexes/co_references.jsonl` に append-only で追記される
- その記録は `python3 scripts/build_llm_wiki.py` 実行時に集計され、`co_referenced` リンクとして `data/llm_wiki/pages/` に反映される
- つまり、**参照ログの保存**と**Wiki への反映**は別段階である

### fallback

- `data/llm_wiki/` が未生成または stale なら、まず `python3 scripts/build_llm_wiki.py --include-issues` を試す。
- それでも使えない場合のみ、従来の `data/llm_wiki/sources/second_brain/` / `data/llm_wiki/sources/memories/` / `data/llm_wiki/sources/conversation_memory/` の直接参照へ fallback してよい。
- fallback を使った場合は、「LLMWiki を使えなかったので直接参照した」と作業メモに残せる形で扱う。

---

関連: [docs/taxonomy.md](docs/taxonomy.md) · [docs/workflows.md](docs/workflows.md) · [docs/agent_playbook.md](docs/agent_playbook.md) · [docs/integrations.md](docs/integrations.md) · [.claude/skills/](.claude/skills/) · [evals/](evals/) · [schemas/](schemas/)
