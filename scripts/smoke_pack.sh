#!/usr/bin/env bash
# 打包后安装冒烟：npm pack → 临时目录 npm install 该 tarball → 用装好的包跑 doctor --full
#   （实际渲染内置样张的 HTML + PPTX 并 strict 校验）。确保发出去的包是完整可用的。
#   bash scripts/smoke_pack.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
TGZ="$(npm pack --silent --pack-destination "$TMP" | tail -1)"
SIZE=$(wc -c < "$TMP/$TGZ")
echo "smoke_pack: $TGZ $((SIZE/1024)) KB"
if (( SIZE > 1400000 )); then echo "smoke_pack: 包体超过 1.4 MB 上限" >&2; exit 1; fi
mkdir -p "$TMP/app" && cd "$TMP/app"
npm init -y >/dev/null
npm install --silent --no-audit --no-fund "$TMP/$TGZ" >/dev/null
PKG="$TMP/app/node_modules/@topmindspace/topmind-presentation"
[[ -f "$PKG/SKILL.md" ]] || { echo "smoke_pack: 安装后缺 SKILL.md" >&2; exit 1; }
for f in recipes/generate.md recipes/beautify.md scripts/doctor.py; do
  [[ -f "$PKG/$f" ]] || { echo "smoke_pack: 安装后缺 $f" >&2; exit 1; }
done
[[ "$(npx --no-install topmind-presentation path)" == "$PKG" ]] || { echo "smoke_pack: bin 入口异常" >&2; exit 1; }
TOP_PPT_NODE_PATH="$TMP/app/node_modules" npx --no-install topmind-presentation doctor --full
echo "smoke_pack: OK"
