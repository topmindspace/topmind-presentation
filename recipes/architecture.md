# 食谱 · 架构图

**什么时候用**：要分层架构、系统拓扑、业务流程、泳道、方案图，且要多页或要 PPTX。单张长图不归本技能。

| 输入 | 保留什么 | 产出 |
|---|---|---|
| 系统描述、组件清单、流程或现有草图 | 组件名、层级、调用方向原样保留，不擅自增删组件 | `架构.html`（C 模式，1–8 页、图解优先）；要 PPTX 再加 `架构.pptx` |

## 步骤

1. Gate 0 + 六项问询照常（模式已定为 C，篇幅默认 6 页，风格推荐 graphite-dark / business-blue / spectrum）。
2. 先定每页一张主图：分层（layers）、泳道（lanes）、流程（steps）、拓扑（network）。一页只讲一张图，配一行结论。
3. 起骨架：`python3 scripts/scaffold_report.py --mode architecture --preset layered-arch --out 架构.html`（流程类用 `--preset flow-arch`）。
4. 模型单写 → `render_from_model.py --template architecture` → `validate_report.py --strict` 0/0；PPTX 同 `generate.md` 第 7 步。
5. 逐页看图：节点文字不溢出、连线不穿字、层次一眼能看清。

需要更多：`references/layouts-architecture.md`、`references/modes.md`。
