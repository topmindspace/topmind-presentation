# 默认生成面（L1.5 · Mode A 主读 · ≤6KB）

> **Mode A / Fast 演示的首要读面**（正式场合 · 大气演讲）。完整决策见 `playbook.md`；工艺清单见 `presentation-craft.md`；插画/配图见 `illustration-layout.md`；代码用 `extract_snippet.py`。  
> Mode B/C 能力保留——**需要时**再读 modes / layouts-*；勿把密排/架构默认反向污染 A。

## A 默认三件套

1. **12 默认页型**（下表）  
2. **8 核心图**（核图池；advanced 按需）  
3. **V1–V4** 演讲构图（≈ P1–P4）

**骨架分层（A）**：**主力** P1–P4 + P6/P10；**扩展** P5；**次级** P7–P9、P11–P12（意图命中再用，勿默认轮换）。  
**图表**：**核图 8** 为默认池；`charts-extended.md` / advanced **仅意图命中才读/才用**（禁为凑多样性硬上）。  
**按需**：Mode B Exhibit/密表 · Mode C 全幅架构——意图命中再读 modes / layouts-*。

## 12 默认页型

| 意图 | pageType | A 主力 skel | 备注 |
|------|----------|-------------|------|
| 封面 | cover | **P1** | |
| 议程 | agenda | **P2** | |
| 大数/KPI | kpi | **P3** | V3 |
| 要点 | points | **P4** | |
| 卡片 | cards | P5 | 扩展（非默认轮换） |
| 指标带 | metrics | **P2** | |
| 对比 | comparison | **P4** | V4 |
| 表 | table / halftable | **P4** / P1 | A 少用次级 P8；密表意图才 P8 |
| 图证 | exhibit / bar | **P1** / P2 | A 演讲图文；P8 为 B 证据次级 |
| 双栏论述 | twocol | **P6** | 主力 |
| 结构/泳道 | diagram / lane | **P10** | 全幅结构次级 P9；一主两从次级 P11 |
| 收尾 | closing | **P1** | |

选型：`recommend_layout.py --mode A|B|C`；矩阵见 playbook §三/§四。演示优先 V1–V4 对应页。

## 8 核心图

`bar` · `hbar` · `line` · `donut` · `progress` · `area` · `stack` · `dualline`

极偏占比 → **禁 donut/pie**，改 KPI/进度/对比条（V3）。简单图禁全幅。  
**多样性**：先拉开核图 8；advanced 用了也计入 `minTypes`（不罚），但**只在内容需要时选**，绝不为凑下限垫冷门图。默认**不**预读 `charts-extended.md`。

## V1–V4（演示默认）

| V | 结构 | 何时 |
|---|------|------|
| V1 | 主视觉 + 右注解 | 默认图文 |
| V2 | 上图下带 | 总览→分解 |
| V3 | 大数 + 佐证 | 极偏/单点结论 |
| V4 | 双图对照 | 前后/方案 |

## 命令链（模型单写 · Mode A 含 layout-qa）

```
scaffold_report → 只填 REPORT_MODEL → render_from_model --inplace
→ validate_report --strict   # presentation 自动 --layout-qa
→ quality_gate --deliver →（用户要 PPTX 时）B 通道 build_pptx → validate_pptx
```

## 长文与密度（Mode A）

一屏一主张；证据用卡/列表或跟进页。**禁止**为稀疏 demo 感删实质。溢出顺序：重构 → 拆页 → 换 V/栅格 → 有限 fontShrink。详见 `presentation-craft.md`「长文与信息承载」。
配图/插画页：caption+so-what、安全边距、勿与大图双重心——`illustration-layout.md`。
