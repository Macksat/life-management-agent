# Integrations — 外部連携(MCP / ブラウザ)

Claude Code と Codex から Google Workspace とブラウザを操作できるようにする設定。
**秘密情報は `.env` のみに置き、コミットしない**(`.gitignore` 済み)。

## 何が入るか

| 連携 | 仕組み | Claude Code | Codex |
|------|--------|-------------|-------|
| **GitHub**(Issue / Label の CRUD) | `github-mcp-server`(Go バイナリ)を MCP サーバとして起動 | `.mcp.json` の `github` | `~/.codex/config.toml` の `[mcp_servers.github]` |
| **Google Workspace**(Gmail / Calendar / Drive / Docs / Sheets ほか) | `workspace-mcp`(常設コマンド優先、無ければ `uvx`)を MCP サーバとして起動 | `.mcp.json` の `google-workspace` | `~/.codex/config.toml` の `[mcp_servers.google-workspace]` |
| **ブラウザ操作** | Claude=Playwright MCP / Codex=既存の bundled プラグイン | `.mcp.json` の `playwright` | `browser-use` / `computer-use`(導入済み) |

認証情報はすべて `.env` から読み込む(設定ファイルに秘密を書かない)。
- GitHub: [`scripts/github-mcp.sh`](../scripts/github-mcp.sh) — `.env` の `GITHUB_PERSONAL_ACCESS_TOKEN`、または `gh auth token` にフォールバック。
- Google: [`scripts/google-workspace-mcp.sh`](../scripts/google-workspace-mcp.sh) — `.env` の `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`。

## 前提

- `uv` / `uvx`(Python 3.10+)— Google Workspace MCP のフォールバック起動に使用。
- `node` / `npx` — Playwright MCP のフォールバック起動に使用。
- `gh`(GitHub CLI)— GitHub MCP のトークンフォールバックに使用（任意。PAT を `.env` に設定する場合は不要）。
- いずれもインストール済みであることを確認: `uvx --version` / `npx --version` / `gh --version`。

## セットアップ手順

### 1. GitHub MCP サーバのセットアップ

1. バイナリをダウンロード:
   ```bash
   gh release download v1.1.2 --repo github/github-mcp-server \
     --pattern 'github-mcp-server_Darwin_arm64.tar.gz' --dir /tmp
   mkdir -p bin
   tar xzf /tmp/github-mcp-server_Darwin_arm64.tar.gz -C bin/
   chmod +x bin/github-mcp-server
   ```
2. 認証（以下のいずれか）:
   - **推奨:** `gh auth login` 済みなら追加設定不要（スクリプトが `gh auth token` を自動取得）。
  - **PAT 方式:** `.env` に `GITHUB_PERSONAL_ACCESS_TOKEN=<your-token>` を追加。スコープ: `repo`, `read:org`。
3. 確認: `scripts/github-mcp.sh --check`

### 1.1 GitHub 読み取りの軽量化

- 読み取り専用の検索・一覧・閲覧は、`gh` CLI を使ってよい。
- 推奨は `gh auth login` を済ませておき、MCP は書き込みや複雑操作に寄せる運用。
- 例:
  ```bash
  gh issue list --repo <your-github-username>/<your-repo-name> --state open --limit 20
  gh issue view 10 --repo <your-github-username>/<your-repo-name>
  gh issue list --repo <your-github-username>/<your-repo-name> --search 'due_date:2026-06-06'
  ```

### 2. Google Cloud で OAuth クライアントを用意

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成/選択。
2. **APIとサービス > ライブラリ** で使う API を有効化(Gmail API / Google Calendar API / Google Drive API / Docs / Sheets など)。
3. **OAuth 同意画面** を設定。テスト中は利用する Google アカウントを「テストユーザー」に追加。
4. **認証情報 > 認証情報を作成 > OAuth クライアント ID**。
   - 種類: **ウェブ アプリケーション**
   - **承認済みのリダイレクト URI** に `http://localhost:8000/oauth2callback` を追加。
5. 発行された **クライアント ID / シークレット** を控える。

### 3. `.env` に設定（Google）

```bash
cp .env.example .env   # 既にある場合は不要
# .env を編集して以下を設定(.env はコミットされない)
# GOOGLE_CLIENT_ID=...apps.googleusercontent.com
# GOOGLE_CLIENT_SECRET=...
```

確認(値は伏字で表示、サーバは起動しない):

```bash
scripts/google-workspace-mcp.sh --check
```

### 4. Claude Code

- [`.mcp.json.example`](../.mcp.json.example) を `.mcp.json` にコピーして使う。
- 必要なら `command` / `args` をローカル環境に合わせて調整する。
- プロジェクトルートで `claude` を起動 → 初回は MCP サーバの利用承認を求められる(承認する)。
- `/mcp` で稼働状況を確認できる。

### 5. Codex

- [`~/.codex/config.toml`](file://~/.codex/config.toml) に `[mcp_servers.google-workspace]` を追記済み。
- Codex を起動 → `/mcp` でサーバ一覧を確認。
- ブラウザ操作は導入済みの `browser-use` / `computer-use` プラグインを利用する(追加設定不要)。

### 6. 初回認証(Google)

- Google Workspace のツールを**初めて呼ぶと**、ブラウザが開いて Google のログイン/同意画面が表示される。
- 同意するとローカルにトークンが保存され、以降は再認証不要(期限切れ時は再度同意)。
- トークン等の保存先は `.gitignore` 済み(`token.json` / `credentials.json` / `.credentials/` など)。

## ブラウザ操作

- **Claude Code:** Playwright MCP(`@playwright/mcp`)。ページのナビゲート・クリック・入力・スクショ・抽出など。
  初回は Chromium が自動ダウンロードされることがある。
- **Codex:** 既存の `browser-use`(アプリ内ブラウザ)/ `computer-use`。

## セキュリティと運用ルール

- **秘密情報は `.env` のみ。** `.mcp.json` / `config.toml` / スクリプトには書かない。`.env` は `.gitignore` 済み。
- GitHub は **読み取り系を軽量経路に寄せてよい**。Issue/Label の書き込みだけ GitHub MCP を必須とする。
- 外部に影響する操作(**メール送信・予定の作成/変更・ファイル共有/削除・送信系**)は、
  AI が独断で実行せず**ユーザーの承認を得てから**行う([AGENTS.md](../AGENTS.md) §5・§15)。
- Slack の送信系 MCP を使う前には、必ず [data/llm_wiki/sources/memories/preferences.md](../data/llm_wiki/sources/memories/preferences.md) を読み、宛先・メンション・本文形式の最新ルールを確認する。
- Slack の送信系 MCP には `mcp__codex_apps__slack._slack_send_message`、draft、schedule を含む。送信前チェックを省略してはならない。
- 読み取り(受信箱の確認・予定の閲覧・ファイル検索)は AI が実行してよい。
- 最小権限を意識する。不要なら `--tool-tier core` のままにし、必要に応じてツールを絞る
  (`workspace-mcp --tools gmail calendar drive` や `uvx workspace-mcp --tools gmail calendar drive` 等)。`--read-only` で読み取り専用にもできる。

## 常設コマンド優先

- 起動時間短縮のため、MCP スクリプトは **ローカルにインストール済みのコマンド** を最優先で使う。
- 見つからない場合だけ `uvx` / `npx` にフォールバックする。
- 代表例:
  - Google Workspace: `workspace-mcp`
  - Playwright MCP: 必要なら `@playwright/mcp` のローカル常設化を検討
- カスタムの実行ファイルパスを固定したい場合は、環境変数で上書きする:
  - `GOOGLE_WORKSPACE_MCP_CMD`

## トラブルシューティング

- **MCP サーバが起動しない:** `scripts/google-workspace-mcp.sh --check` で認証情報を確認。`uvx --version` / `npx --version` を確認。
- **`redirect_uri_mismatch`:** Google Cloud のリダイレクト URI に `http://localhost:8000/oauth2callback` が登録されているか確認。
- **`access_denied` / テストユーザー:** OAuth 同意画面のテストユーザーに利用する Google アカウントを追加。
- **初回が遅い/タイムアウト:** `workspace-mcp --help` を常設コマンドで試し、未導入なら `uvx workspace-mcp --help` を一度実行してキャッシュする。
- **Codex 設定を戻したい:** `~/.codex/config.toml.bak.*` のバックアップから復元。

## 関連

- [.mcp.json.example](../.mcp.json.example) · [scripts/google-workspace-mcp.sh](../scripts/google-workspace-mcp.sh) · [.env.example](../.env.example)
- [AGENTS.md](../AGENTS.md)(外部操作の承認ルール)
