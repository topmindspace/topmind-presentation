#!/usr/bin/env bash
# TopPPT HTML · PPTX 轻量冒烟（Batch 2）
# extract_model → build_pptx → validate_pptx --strict --model=
# 用法: bash scripts/smoke_pptx.sh [example.html]
# CI（ci_skill_gates --with-pptx）必跑 business-blue + research-mckinsey（D13；后者覆盖 soWhat+footnote / D8）
# 失败时打印短摘要（错误码/页码/消息），完整 JSON 落盘到 TMPDIR。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
HTML="${1:-assets/examples/2026-09-09-presentation-business-blue.html}"
if [[ ! -f "$HTML" ]]; then
  echo "smoke_pptx: missing $HTML" >&2
  exit 2
fi
STEM="$(basename "$HTML" .html)"
OUT_DIR="${TMPDIR:-/tmp}/topmind-presentation-smoke"
mkdir -p "$OUT_DIR"
MODEL="$OUT_DIR/${STEM}.model.json"
PPTX="$OUT_DIR/${STEM}.pptx"
REPORT="$OUT_DIR/${STEM}.validate.json"

echo "== smoke_pptx =="
echo "HTML  $HTML"
python3 scripts/extract_model.py "$HTML" "$MODEL"
echo "MODEL $MODEL ($(wc -c < "$MODEL") bytes)"

# Prefer local node_modules pptxgenjs
export NODE_PATH="${ROOT}/node_modules${NODE_PATH:+:$NODE_PATH}"
node scripts/build_pptx.js "$PPTX" --model="$MODEL"
echo "PPTX  $PPTX ($(wc -c < "$PPTX") bytes)"

set +e
python3 scripts/validate_pptx.py "$PPTX" --strict --model="$MODEL" \
  --json-out="$REPORT" >"$OUT_DIR/${STEM}.validate.stdout.json"
rc=$?
set -e

if [[ "$rc" -ne 0 ]]; then
  echo "smoke_pptx: VALIDATE FAIL (exit $rc)" >&2
  python3 - "$REPORT" "$rc" <<'PY'
import json, sys
path, rc = sys.argv[1], sys.argv[2]
try:
    d = json.loads(open(path, encoding="utf-8").read())
except Exception as e:
    print(f"  (could not read report {path}: {e})", file=sys.stderr)
    sys.exit(int(rc))
errs = d.get("errors") or []
warns = d.get("warnings") or []
print(f"  summary: errors={len(errs)} warnings={len(warns)} slides={d.get('summary',{}).get('slide_count')}", file=sys.stderr)
seen = set()
for e in errs + warns:
    key = (e.get("code"), e.get("slide"), e.get("message"))
    if key in seen:
        continue
    seen.add(key)
    slide = e.get("slide")
    slide_s = f"slide={slide} " if slide is not None else ""
    msg = (e.get("message") or "")[:160]
    print(f"  [{e.get('code')}] {slide_s}{msg}", file=sys.stderr)
    if len(seen) >= 40:
        print(f"  … truncated ({len(errs)+len(warns)} total findings)", file=sys.stderr)
        break
print(f"  full JSON: {path}", file=sys.stderr)
sys.exit(int(rc))
PY
fi

echo "smoke_pptx: OK (0 errors / 0 warnings)"
exit 0
