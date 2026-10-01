#!/usr/bin/env bash
# Shared skill-package gates for CI + Release (single source of truth).
# Usage (from repo root):
#   bash scripts/ci_skill_gates.sh
#   bash scripts/ci_skill_gates.sh --with-pptx   # regression fixture + smoke_pptx
# Env:
#   SKILL_GATES_WITH_PPTX=1  same as --with-pptx
#   PYTHON / NODE optional overrides
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
WITH_PPTX="${SKILL_GATES_WITH_PPTX:-0}"
for arg in "$@"; do
  case "$arg" in
    --with-pptx) WITH_PPTX=1 ;;
    --no-pptx) WITH_PPTX=0 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
  esac
done

SKILLS=()
# 单技能仓库：技能即仓库根目录。固定跑根目录，不做 discover。
if [[ -f SKILL.md ]]; then
  SKILLS+=(".")
fi
if [[ ${#SKILLS[@]} -eq 0 ]]; then
  echo "ci_skill_gates: no skills discovered" >&2
  exit 1
fi
echo "ci_skill_gates: discovered ${SKILLS[*]} (with_pptx=${WITH_PPTX})"

PPTX_INSTALLED=0
ensure_python_pptx() {
  if [[ "$PPTX_INSTALLED" -eq 1 ]]; then
    return 0
  fi
  echo "ci_skill_gates: installing python-pptx (needed for PPTX fixture / smoke)"
  "$PY" -m pip install --quiet 'python-pptx>=0.6.21' \
    || pip3 install --quiet 'python-pptx>=0.6.21' \
    || "$PY" -m pip install --quiet --break-system-packages 'python-pptx>=0.6.21'
  PPTX_INSTALLED=1
}

run_one() {
  local skill="$1"
  echo "=== gates: ${skill} ==="
  pushd "$skill" >/dev/null

  if [[ -f package-lock.json ]]; then
    npm ci --omit=dev
  else
    npm install --omit=dev
  fi

  "$PY" scripts/package_skill.py --check
  "$PY" scripts/audit_styles.py
  "$PY" scripts/audit_docs.py
  "$PY" scripts/audit_skill.py
  "$PY" scripts/audit_css.py

  if [[ "$WITH_PPTX" == "1" ]]; then
    ensure_python_pptx
    mkdir -p dist/regression
    local STEM=2026-09-09-research-mckinsey
    if [[ -f "assets/examples/${STEM}.model.json" ]]; then
      export NODE_PATH="${PWD}/node_modules${NODE_PATH:+:$NODE_PATH}"
      node scripts/build_pptx.js "dist/regression/${STEM}.pptx" \
        --model="assets/examples/${STEM}.model.json"
    else
      echo "ci_skill_gates: skip regression fixture (missing assets/examples/${STEM}.model.json)"
    fi
  fi

  "$PY" scripts/negative_tests.py

  if [[ "$WITH_PPTX" == "1" && -f scripts/smoke_pptx.sh ]]; then
    ensure_python_pptx
    # D13: business-blue (default) + research-mckinsey (soWhat+footnote; catches D8)
    bash scripts/smoke_pptx.sh
    bash scripts/smoke_pptx.sh assets/examples/2026-09-09-research-mckinsey.html
    if [[ -f assets/examples/2026-09-09-architecture-graphite-dark.html ]]; then
      bash scripts/smoke_pptx.sh assets/examples/2026-09-09-architecture-graphite-dark.html || {
        echo "ci_skill_gates: graphite-dark smoke WARN (non-fatal)" >&2
      }
    fi
  elif [[ "$WITH_PPTX" == "1" ]]; then
    echo "ci_skill_gates: smoke_pptx.sh not present — skip"
  fi

  # Optional feedback-gate unit tests when present (fast; keep green)
  if [[ -f scripts/test_feedback_gates.py ]]; then
    "$PY" scripts/test_feedback_gates.py
  fi

  popd >/dev/null
  echo "=== gates OK: ${skill} ==="
}

for skill in "${SKILLS[@]}"; do
  run_one "$skill"
done

echo "ci_skill_gates: all skills green"
