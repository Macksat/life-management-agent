#!/usr/bin/env bash
# GitHub MCP server launcher (stdio).
# - プロジェクトルートの .env から GITHUB_PERSONAL_ACCESS_TOKEN を読み込む。
# - .env はコミットしない。秘密情報はこのスクリプトにも設定ファイルにも書かない。
#
# 使い方: Claude Code の MCP 設定からこのスクリプトを command として呼ぶ。
# デバッグ: `scripts/github-mcp.sh --check` で認証情報の有無だけ確認(サーバは起動しない)。
#
# バイナリ: github/github-mcp-server (Go 製)
# https://github.com/github/github-mcp-server
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# .env を読み込む(存在すれば)。
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

# 環境変数チェック: .env → gh auth token の順にフォールバック
if [ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]; then
  if command -v gh &>/dev/null; then
    token="$(gh auth token 2>/dev/null || true)"
    if [ -n "$token" ]; then
      GITHUB_PERSONAL_ACCESS_TOKEN="$token"
    fi
    unset token
  fi
fi

if [ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]; then
  echo "[github-mcp] GITHUB_PERSONAL_ACCESS_TOKEN が見つかりません。" >&2
  echo "[github-mcp] 以下のいずれかで設定してください:" >&2
  echo "[github-mcp]   1. .env に GITHUB_PERSONAL_ACCESS_TOKEN=<your-token> を追加" >&2
  echo "[github-mcp]   2. gh auth login で GitHub CLI を認証" >&2
  exit 1
fi

export GITHUB_PERSONAL_ACCESS_TOKEN

if [ "${1:-}" = "--check" ]; then
  echo "[github-mcp] OK: GITHUB_PERSONAL_ACCESS_TOKEN is set (${GITHUB_PERSONAL_ACCESS_TOKEN:0:8}...redacted)"
  exit 0
fi

BINARY="$ROOT_DIR/bin/github-mcp-server"

if [ ! -x "$BINARY" ]; then
  echo "[github-mcp] バイナリが見つかりません: $BINARY" >&2
  echo "[github-mcp] セットアップ手順:" >&2
  echo "[github-mcp]   gh release download v1.1.2 --repo github/github-mcp-server --pattern 'github-mcp-server_Darwin_arm64.tar.gz' --dir /tmp" >&2
  echo "[github-mcp]   tar xzf /tmp/github-mcp-server_Darwin_arm64.tar.gz -C bin/" >&2
  echo "[github-mcp]   chmod +x bin/github-mcp-server" >&2
  exit 1
fi

# stdio トランスポートで起動。issues + labels ツールセットを有効化。
exec "$BINARY" stdio --toolsets issues,labels
