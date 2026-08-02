# Personal Action OS — GitHub Issue + AI エージェントで動く個人行動基盤テンプレート

> 思考・タスク・情報・学習・生活を **GitHub Issue を中心** に蓄積し、
> **AI エージェントが参照・整理・行動提案できる形** に保つための個人基盤テンプレート。

このリポジトリは「貯めるための場所」ではなく、**行動 OS** です。
すべての Issue は「次に何をするか(next_action)」を持ちます。

---

## このテンプレートでできること

- **低リスクな課題を軽量キャプチャできる** -- 思いつき・タスク・悩みをまず `inbox` / `needs-triage` に記録し、必要なものだけ後で詳細化
- **LLMWiki + A-MEM の記憶基盤** -- `sources/` を正本として保ちながら、A-MEM で保存前の更新判断を行い、LLMWiki で探索しやすい読み取り面へ変換
- **3 層メモリアーキテクチャ** -- プロフィール(長期)、思考・会話記録(恒久)、セッション文脈(短期)を使い分け、AI が「あなた」を理解し続ける
- **second_brain から Issue 候補を起こせる** -- 会話ダイジェストから action 候補を抽出し、重複確認を通して GitHub Issue に落とせる
- **渡したファイルからLLMWikiを構築できる** -- 添付・指定された会話記録やメモだけを取り込み、外部クラウドは探索しない
- **継続作業を再開しやすい** -- `PLANS.md` に作業計画・判断・再開メモをまとめ、完了後もアーカイブできる
- **Claude Code / Codex 両対応** -- Skills は `.claude/skills/` に一元管理し、symlink で Codex からも自動検出

## クイックスタート

### 1. リポジトリをフォークまたはクローン

```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
```

### 2. 初期設定

1. **AGENTS.md** を読む -- AI エージェントの全ルールが書かれた正本
2. **CLAUDE.md** / **CODEX.md** の `<your-github-username>` と `<your-repo-name>` を自分のものに置換
3. `data/llm_wiki/sources/memories/user_context.md` に自分のプロフィールを記入
4. `data/llm_wiki/sources/memories/preferences.md` に好み・スタイルを記入
5. `.env.example` をコピーして `.env` を作成し、必要な API キーを設定

### 3. AI と対話を始める

Claude Code または Codex を起動し、こう言うだけ:

```
「来週までにやりたいことを整理して」
「この悩みを Issue にして」
「今日やることを教えて」
```

AI がまず軽量に記録し、必要に応じて詳細化・承認・起票まで進めます。

## 基本運用フロー

```
対話 ─▶ Quick Capture ─▶ inbox / needs-triage ─▶ Triage / Detail Up
                                                     │
                         高リスク / 要判断 ──────────┤
                                                     ▼
                                              Clarify + Approval
                                                     │
                                                     ▼
                                                 Issue 作成 / 更新
```

**中心は「Capture First」。** まず摩擦なく記録し、重要判断や外部変更が絡むときだけ確認ゲートに戻します。

## Issue 分類(4 軸)

| 軸 | 値の例 |
|----|--------|
| **category** | work / personal-dev / second-brain / learning / career / life-admin / relationship / travel / health / hobby / gadget / thinking / meta-system |
| **type** | task / idea / research / project / memo / decision / habit / bug / improvement |
| **status** | inbox → needs-triage → ready → in-progress → waiting / blocked → done → archived |
| **priority** | P0-critical / P1-high / P2-medium / P3-low |

## 3 層メモリアーキテクチャ

| レイヤ | 保存先 | 答える問い | 寿命 |
|--------|--------|------------|------|
| **プロフィール** | `data/llm_wiki/sources/memories/` | 「この人はどんな人か？」 | 恒久 |
| **思考・会話記録** | `data/llm_wiki/sources/second_brain/` | 「何を考えてきたか？」 | 恒久 |
| **セッション文脈** | `data/llm_wiki/sources/conversation_memory/` | 「直近の AI 会話で何が起きたか？」 | 短期(圧縮) |

## LLMWiki / A-MEM

- **LLMWiki** は `data/llm_wiki/pages/` と `indexes/` を生成し、`search / read / follow-links` で段階的に探索できるようにします。
- **A-MEM** は `tools/agentic_memory/` にあり、`preferences / facts / decisions / second_brain / conversation_memory` の保存前に `add_new / update_existing / skip_duplicate / strengthen_link` を判定します。
- **監査ログとメタデータ** は `data/llm_wiki/indexes/agentic_memory_decisions.jsonl` と `agentic_memory_store.json` に保存されます。
- **Issue 候補化** は `scripts/extract_issue_candidates.py` と `scripts/create_issues_from_candidates.py` で行います。

## ディレクトリ構成

```
.
├── README.md                  このファイル
├── LICENSE                    MIT License
├── AGENTS.md                  AI 最重要ルール(正本。Claude / Codex 共通)
├── CLAUDE.md / CODEX.md       各 AI 向け実務メモ
├── .claude/skills/            Agent Skills の実体(11 スキル)
├── .agents/skills → symlink   Codex 用(実体を共有)
├── docs/                      思想・原則・文脈・分類・手順
├── evals/                     出力品質の評価基準
├── schemas/                   Issue / category / review / issue_candidate の JSON Schema
├── scripts/                   build/search/A-MEM/issue candidate 用スクリプト
├── tools/agentic_memory/      A-MEM 風の保存前判断・監査ログ
├── data/llm_wiki/             3 層メモリの実体
├── plans/                     進行中の作業単位 PLANS.md
├── .plans/                    完了済み PLANS.md アーカイブ
├── tests/                     LLMWiki / A-MEM のユニットテスト
└── .github/ISSUE_TEMPLATE/    Issue テンプレート群
```

## カスタマイズのポイント

- **Skills の追加・編集:** `.claude/skills/<name>/SKILL.md` を追加するだけで AI が自動検出
- **カテゴリの追加:** `docs/taxonomy.md` と `docs/labels.md` を編集
- **記憶の蓄積:** 使い続けるだけで AI が自動的に `memories/` に好み・パターンを蓄積
- **A-MEM 判定の再実行:** `python3 scripts/backfill_agentic_memory.py` で既存ソースからリンク・進化メタデータを再構築
- **second_brain の取り込み:** `python3 scripts/ingest_second_brain_digest.py <digest-path>` で A-MEM パイプラインを通して登録
- **外部連携:** GitHub、Google Workspace、Playwright(ブラウザ操作)に対応。設定は `docs/integrations.md`

## ドキュメント

- **ルール正本:** [AGENTS.md](AGENTS.md) -- AI エージェントの全ルール
- **思想:** [docs/vision.md](docs/vision.md)
- **手順:** [docs/workflows.md](docs/workflows.md) / [.claude/skills/](.claude/skills/)
- **LLMWiki / A-MEM:** [docs/specs/llm_wiki.md](docs/specs/llm_wiki.md)
- **分類:** [docs/taxonomy.md](docs/taxonomy.md) / [docs/labels.md](docs/labels.md)
- **連携:** [docs/integrations.md](docs/integrations.md)

## ライセンス

[MIT License](LICENSE)。フォークして自由にカスタマイズしてください。
