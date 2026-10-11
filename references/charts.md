# 图表全库（逻辑索引 · 纪律优先 · 按需取码）

> 本文件已拆分，**禁止整读**物理大文件。§编号跨文件稳定。取码：
> `python scripts/extract_snippet.py --file charts.md --section <编号>`
> 或 `--chart <类型>`（自动路由）。

## 读序（P1-3 facade · 不缩减 registry）

1. **先纪律**：`charts-discipline.md`（§64 合理性 · §66 误用与多样性）——选型与反模式。
2. **核图 8**（Mode A / Fast 默认池）：`bar` · `hbar` · `line` · `donut` · `progress` · `area` · `stack` · `dualline` → 代码在 `charts-basic.md`。
3. **基础扩展**：其余 basic 类型按意图取节（仍属 `charts-basic.md`）。
4. **高级 / extended**：waterfall、sankey 相关形状、boxplot… → **意图命中才读** `charts-extended.md`；勿预读。
5. **信息图页型**（非 `chart.type`）：`infographics.md` §71–§77。

**多样性地板不变**：`charts.variety.minTypes.presentation ≥ 4`（及 B/C 对应下限）；registry 36 种不删。  
**preferCoreFirst**：先拉开核图 8；advanced 使用时**计入** minTypes（不罚），但**禁止预读/默认选用** `charts-extended.md`——仅意图命中时 `extract_snippet.py --chart`；**禁**为凑下限垫冷门图。

| § 范围 | 物理文件 | 何时读 |
|--------|----------|--------|
| §64、§66 | `charts-discipline.md` | **默认先读**（误用/多样性） |
| §16–§31、§29b、§35 等 | `charts-basic.md` | 核图与常规图代码 |
| §52–§70（除纪律节） | `charts-extended.md` | advanced / 意图命中 |
