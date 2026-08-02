#!/usr/bin/env bash
# Google Workspace MCP server launcher (stdio).
# - プロジェクトルートの .env から認証情報を読み込む(.env はコミットしない)。
# - workspace-mcp が期待する GOOGLE_OAUTH_CLIENT_ID/SECRET に、.env の
#   GOOGLE_CLIENT_ID/SECRET をマッピングする。
# - 秘密情報はこのスクリプトにも設定ファイルにも書かない(.env が唯一のソース)。
#
# 使い方: Claude Code / Codex の MCP 設定からこのスクリプトを command として呼ぶ。
# デバッグ: `scripts/google-workspace-mcp.sh --check` で認証情報の有無だけ確認(サーバは起動しない)。
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

# .env の名前(GOOGLE_CLIENT_*)を workspace-mcp の名前(GOOGLE_OAUTH_CLIENT_*)へマッピング。
export GOOGLE_OAUTH_CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID:-${GOOGLE_CLIENT_ID:-}}"
export GOOGLE_OAUTH_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET:-${GOOGLE_CLIENT_SECRET:-}}"
# ローカルの http コールバックを許可(本番 https でないため)。
export OAUTHLIB_INSECURE_TRANSPORT="${OAUTHLIB_INSECURE_TRANSPORT:-1}"

if [ -z "${GOOGLE_OAUTH_CLIENT_ID}" ] || [ -z "${GOOGLE_OAUTH_CLIENT_SECRET}" ]; then
  echo "[google-workspace-mcp] GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET が .env に見つかりません。" >&2
  echo "[google-workspace-mcp] .env.example を参照して .env を作成してください。" >&2
  exit 1
fi

if [ "${1:-}" = "--check" ]; then
  echo "[google-workspace-mcp] OK: GOOGLE_OAUTH_CLIENT_ID is set (${GOOGLE_OAUTH_CLIENT_ID%%.*}...redacted)"
  exit 0
fi

# stdio トランスポートで起動。常設コマンドを優先し、見つからない場合だけ uvx にフォールバックする。
if [ -n "${GOOGLE_WORKSPACE_MCP_CMD:-}" ]; then
  exec "$GOOGLE_WORKSPACE_MCP_CMD" --tool-tier core
fi

if command -v workspace-mcp >/dev/null 2>&1; then
  exec workspace-mcp --tool-tier core
fi

exec uvx workspace-mcp --tool-tier core
