# 食谱 · 美化已有 PPTX

**什么时候用**：用户给了 .pptx，要「美化 / 重排 / 换风格」，文字内容不改。改写文字内容不归本技能。

| 输入 | 保留什么 | 产出 |
|---|---|---|
| 原稿 .pptx（只读）；可选风格、亮暗 | 每一个字、每一个数、页序、图片、演讲者备注；原稿文件不动 | 新目录下 `新稿.pptx`、`新稿.html`、`model.json`、`verify.json`、`report.md`、`compare.png` |

## 步骤

1. 跳过篇幅与大纲问询；只问风格和亮暗（不答就用 business-blue 浅色）。
2. 运行：`python3 scripts/beautify.py 原稿.pptx --out 输出目录 --style business-blue --theme light --compare`
   流程：解析 → 锁定原文（`contentLocked`）→ 逐页诊断 → 映射版式库 → 重排 → 逐字逐数核对。
3. 看 `verify.json`：文字差异、数字差异、图片数、备注回写必须全部通过，有一项不过就不交付。
4. 看 `compare.png`（左原稿、右新稿），逐页确认没有空页、字没有变小到难读、图片没有被裁。
5. 交付新目录，并附 `report.md`（改了哪些版式、为什么）。

契约细节与边界（不支持的元素、SmartArt、公式等的处理）：`references/beautify.md`。环境：python-pptx；对照图需 LibreOffice + poppler。
