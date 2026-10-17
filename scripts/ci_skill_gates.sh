#!/usr/bin/env bash
# Shared skill-package gates for CI + Release (single source of truth).
# Usage (from repo root):
#   bash scripts/ci_skill_gates.sh
#   bash scripts/ci_skill_gates.sh --with-pptx   # regression fixture + smoke_pptx
# Env:
#   SKILL_GATES_WITH_PPTX=1  same as --with-pptx
#   PYTHON / NODE optional overrides
#   AGENTSKILLS   path to the skills-ref validator (default: agentskills on PATH)
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
  "$PY" scripts/check_repo.py

  # Agent Skills 官方校验器（skills-ref）。CI 里 pip 安装；本机没装时跳过并提示。
  local AS="${AGENTSKILLS:-$(command -v agentskills || true)}"
  if [[ -n "$AS" ]]; then
    "$AS" validate "$PWD"
  elif [[ "${CI:-}" == "true" ]]; then
    echo "ci_skill_gates: agentskills not found in CI (pip install skills-ref)" >&2
    exit 1
  else
    echo "ci_skill_gates: skip agentskills validate (pip install skills-ref)"
  fi
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
      node scripts/build_pptx.js "dist/regression/${STEM}.pptx" --strict \
        --model="assets/examples/${STEM}.model.json"
    else
      echo "ci_skill_gates: skip regression fixture (missing assets/examples/${STEM}.model.json)"
    fi
  fi

  "$PY" scripts/negative_tests.py

  # M1：布局求解器金样（10 页型族 × 3 模式；确定性 + 超载拆页不变量）
  node tests/solver/test_solver.js
  # M2：Python 端（HTML 渲染）与 JS 金样逐值一致——HTML/PPTX 拆页同源
  "$PY" tests/solver/test_solver_py.py
  # M3：版式库节奏 / 家族覆盖 / 反模式（全部示例硬门禁）
  for m in assets/examples/*.model.json tests/layouts/gallery-*.model.json; do "$PY" scripts/check_rhythm.py "$m" --strict || exit 1; done
  # M7 最低信息密度门禁（元素种类 / 文字量 / 数据点，三模式分档）+ 自测
  "$PY" scripts/check_density.py assets/examples/*.model.json --strict || { echo "ci_skill_gates: 信息密度门禁失败" >&2; exit 1; }
  "$PY" tests/density/test_density.py || { echo "ci_skill_gates: 信息密度自测失败" >&2; exit 1; }
  "$PY" tests/density/test_echo_eval.py || { echo "ci_skill_gates: 复述检测评测未达标（检出 ≥7/8、误报 ≤1/8）" >&2; exit 1; }
  "$PY" tests/m8/test_m8.py || { echo "ci_skill_gates: M8 回归自测失败" >&2; exit 1; }
  "$PY" tests/m10/test_m10.py || { echo "ci_skill_gates: M10 回归自测失败（风格气质 / 衬线回退链 / lang）" >&2; exit 1; }
  node tests/install/test_install.js || { echo "ci_skill_gates: 安装器三条规则自测失败（升级 / 拒绝降级 / 同名替换）" >&2; exit 1; }

  if [[ "$WITH_PPTX" == "1" ]]; then
    ensure_python_pptx
    export NODE_PATH="${PWD}/node_modules${NODE_PATH:+:$NODE_PATH}"
    # M4：已有 PPT 美化——3 份朴素样例逐字逐数核对 + 篡改负例
    "$PY" tests/beautify/test_beautify.py || { echo "ci_skill_gates: 美化核对失败" >&2; exit 1; }
    "$PY" tests/m11/test_m11.py || { echo "ci_skill_gates: M11 回归自测失败（美化 12 风格 / Exhibit 编号 / 复合承载件 / make_deck）" >&2; exit 1; }
    "$PY" tests/m12/test_m12.py || { echo "ci_skill_gates: M12 回归自测失败（行距 1.5/1.3 / 默认无眉标与注释 / 阶段卡时间线）" >&2; exit 1; }
    "$PY" tests/m13/test_m13.py || { echo "ci_skill_gates: M13 回归自测失败（高密度 / 简单页 / 图标 / 象形图 / 标题防孤字 / 拥挤门禁）" >&2; exit 1; }
  fi

  # M5：doctor 自检 + 打包后安装冒烟
  if [[ "$WITH_PPTX" == "1" ]]; then
    "$PY" scripts/doctor.py || { echo "ci_skill_gates: doctor 自检失败" >&2; exit 1; }
    bash scripts/smoke_pack.sh || { echo "ci_skill_gates: 打包安装冒烟失败" >&2; exit 1; }
  fi

  if [[ "$WITH_PPTX" == "1" && -f scripts/smoke_pptx.sh ]]; then
    ensure_python_pptx
    # D13: business-blue (default) + research-mckinsey (soWhat+footnote; catches D8)
    bash scripts/smoke_pptx.sh
    bash scripts/smoke_pptx.sh assets/examples/2026-09-09-research-mckinsey.html
    if [[ -f assets/examples/2026-09-09-architecture-graphite-dark.html ]]; then
      # M1：架构样张已适配求解器，冒烟转为硬门禁
      bash scripts/smoke_pptx.sh assets/examples/2026-09-09-architecture-graphite-dark.html
    fi
  elif [[ "$WITH_PPTX" == "1" ]]; then
    echo "ci_skill_gates: smoke_pptx.sh not present — skip"
  fi

  # 视觉填充率与重心门禁（渲染后看像素）。M1 起四份示例（演示 / 研究 / 架构 / 产品展示）全部硬门禁。
  if [[ "$WITH_PPTX" == "1" ]]; then
    if command -v soffice >/dev/null 2>&1 && command -v pdftoppm >/dev/null 2>&1; then
      "$PY" -c "import PIL, numpy" 2>/dev/null || "$PY" -m pip install --quiet pillow numpy
      mkdir -p dist/regression
      export NODE_PATH="${PWD}/node_modules${NODE_PATH:+:$NODE_PATH}"
      local VSTEM=2026-09-09-presentation-business-blue
      node scripts/build_pptx.js --out="dist/regression/${VSTEM}.vfill.pptx" --strict \
        --model="assets/examples/${VSTEM}.model.json"
      "$PY" scripts/check_visual_fill.py "dist/regression/${VSTEM}.vfill.pptx" \
        --model="assets/examples/${VSTEM}.model.json" --strict
      for RSTEM in 2026-09-09-research-mckinsey 2026-09-09-architecture-graphite-dark 2026-10-11-topmind-presentation-showcase; do
        [[ -f "assets/examples/${RSTEM}.model.json" ]] || continue
        node scripts/build_pptx.js --out="dist/regression/${RSTEM}.vfill.pptx" --strict \
          --model="assets/examples/${RSTEM}.model.json" >/dev/null
        "$PY" scripts/check_visual_fill.py "dist/regression/${RSTEM}.vfill.pptx" \
          --model="assets/examples/${RSTEM}.model.json" --strict | tail -1 | sed "s/^/  [${RSTEM}] /"
        [[ ${PIPESTATUS[0]} -eq 0 ]] || { echo "ci_skill_gates: 视觉填充门禁失败 ${RSTEM}" >&2; exit 1; }
      done
      # M2：行式图表原生化探针（gantt / progress / funnel / vsbar → 原生可编辑 chart part）
      node scripts/build_pptx.js --out="dist/regression/native-rows.pptx" --strict \
        --model="tests/charts/native-rows.model.json" >/dev/null
      # M3：版式库 golden（51 版式全覆盖 + PPTX 几何指纹）
      "$PY" tests/layouts/test_layouts.py || { echo "ci_skill_gates: 版式 golden 失败" >&2; exit 1; }
      # M5：PPTX 像素回归（三份黄金样张 → 48×27 灰度缩略图对比基线）
      "$PY" scripts/pixel_regression.py || { echo "ci_skill_gates: 像素回归失败" >&2; exit 1; }
      # M9：HTML ↔ PPTX 逐页保真门禁（配对率 / 字级层级 / 颜色 ΔE / 换行 / 位置 / 字体声明）
      [[ -d node_modules/playwright ]] || npm ci --no-audit --no-fund >/dev/null 2>&1 || npm install --no-audit --no-fund >/dev/null
      # M11：全新主题端到端试跑（研究模式 · warm-sand · 复合版式 / 瀑布 / 矩阵 / 示意图 / 图文混排），make_deck 六步全过
      "$PY" scripts/make_deck.py tests/trial/jiejiao.model.json --out dist/trial --fidelity || { echo "ci_skill_gates: 端到端试跑失败（tests/trial）" >&2; exit 1; }
      # M12：第二个全新主题（演示模式 · 社区养老：阶段卡时间线 / 主图 + 小图组 / 瀑布 / 表 + 解读卡 / 金句）
      "$PY" scripts/make_deck.py tests/trial/yanglao.model.json --out dist/trial --fidelity || { echo "ci_skill_gates: 端到端试跑失败（tests/trial/yanglao）" >&2; exit 1; }
      "$PY" scripts/check_fidelity.py --examples --strict || { echo "ci_skill_gates: HTML↔PPTX 保真门禁失败（逐条修复提示见上）" >&2; exit 1; }
      "$PY" scripts/validate_pptx.py "dist/regression/native-rows.pptx" --strict \
        --model="tests/charts/native-rows.model.json" >/dev/null || { echo "ci_skill_gates: 行式原生图表探针失败" >&2; exit 1; }
      "$PY" - "dist/regression/native-rows.pptx" <<'PYEOF'
import sys, zipfile
n = len([x for x in zipfile.ZipFile(sys.argv[1]).namelist() if x.startswith('ppt/charts/chart') and x.endswith('.xml')])
if n < 4:
    print(f'ci_skill_gates: 行式图表应有 4 个原生 chart part，实际 {n}'); sys.exit(1)
print(f'  [native-rows] {n} 个原生 chart part（gantt/progress/funnel/vsbar）')
PYEOF
      # M1：同一模型两次构建，幻灯片 XML 必须逐字节一致（求解器确定性）
      node scripts/build_pptx.js --out="dist/regression/${VSTEM}.det.pptx" --strict \
        --model="assets/examples/${VSTEM}.model.json" >/dev/null
      "$PY" - "dist/regression/${VSTEM}.vfill.pptx" "dist/regression/${VSTEM}.det.pptx" <<'PYEOF'
import sys, zipfile, hashlib
def h(p):
    z = zipfile.ZipFile(p)
    return {n: hashlib.sha1(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('ppt/slides/slide')}
a, b = h(sys.argv[1]), h(sys.argv[2])
diff = [n for n in a if a.get(n) != b.get(n)]
if diff or a.keys() != b.keys():
    print('ci_skill_gates: PPTX 构建不确定，差异页:', diff[:5]); sys.exit(1)
print(f'  [determinism] {len(a)} 页幻灯片 XML 两次构建一致')
PYEOF
    elif [[ "${CI:-}" == "true" ]]; then
      echo "ci_skill_gates: CI 缺 soffice/pdftoppm，视觉门禁不得跳过" >&2
      exit 1
    else
      echo "ci_skill_gates: skip visual fill gate (install libreoffice + poppler-utils)"
    fi
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
