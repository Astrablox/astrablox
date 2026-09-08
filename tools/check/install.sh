#!/usr/bin/env bash
# Install luau-lsp (JohnnyMorganz) and the Roblox global type definitions next to this script.
# Linux/macOS. On Windows use install.ps1. Needs curl and unzip; GITHUB_TOKEN raises the API rate limit.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) ASSET=luau-lsp-linux-x86_64.zip ;;
  Linux-aarch64|Linux-arm64) ASSET=luau-lsp-linux-arm64.zip ;;
  Darwin-*) ASSET=luau-lsp-macos.zip ;;
  *) echo "unsupported platform" >&2; exit 1 ;;
esac
AUTH=()
[ -n "${GITHUB_TOKEN:-}" ] && AUTH=(-H "Authorization: token $GITHUB_TOKEN")
URL=$(curl -s "${AUTH[@]}" https://api.github.com/repos/JohnnyMorganz/luau-lsp/releases/latest | python3 -c "import json,sys; d=json.load(sys.stdin); print([a['browser_download_url'] for a in d['assets'] if a['name']=='$ASSET'][0])")
curl -sL "${AUTH[@]}" "$URL" -o luau-lsp.zip && unzip -q -o luau-lsp.zip && rm luau-lsp.zip && chmod +x luau-lsp
curl -sL -o globalTypes.d.luau https://raw.githubusercontent.com/JohnnyMorganz/luau-lsp/main/scripts/globalTypes.d.luau
./luau-lsp --version
echo "installed luau-lsp and globalTypes.d.luau in $HERE"
