# 插画 / 非数据配图 brief（L2 · ≤4KB）

> **何时读**：页含情绪图 / 产品图 / 截图 / 示意图 / `image.placeholder`；或 Mode A 需要 full-bleed 照片+主张叠字。  
> **何时不读**：纯数据图表选型（走 playbook §五 / `charts.md`）。  
> **取码**：`extract_snippet.py --task image-layout`（`components.md` §11c）；勿整读 `components-atoms.md`。

## 配图 vs 数据图（互斥优先）

| 意图 | 用什么 | 不要 |
|------|--------|------|
| 趋势 / 构成 / 对比 / 排名 | 数据图（核图 8 优先） | 用照片代替数据 |
| 氛围 / 品牌 / 产品外观 / UI 截图 | `<img>` / `.media` / `image.placeholder` | 硬画假图表 |
| 无素材但仍需图位 | `image.placeholder` + `.media--ph` | 留空或塞无关图 |

**一页一主视觉**：同页不要「大照片 + 大图表」双重心（FAIL 级审美风险）；icon 可点缀，chart 占主位时照片改小或拆页。

## 版式与安全边距

- **安全边距**：距版心边缘 ≥ 24px（演示投影更宽松）；文字不得压在图片关键焦点上。
- **图文共存**：半幅图（half）→ 图左/上 + 注右/下；注含 **caption（图注）+ so-what（含义一句）**。
- **不重叠**：标题 / 标签 / 图例不得与照片主体或 icon 碰撞；必要叠字用半透明底或高对比条。
- **icon + chart**：icon 在注释列或卡眉，不进 SVG 绘图区；每屏 icon 仍 3–8。

## Mode A · full-bleed 照片 + 主张叠字

1. 仅用于封面 / 章节幕 / 金句休止 / 收尾 —— **不做证据页**。  
2. 主张句叠在照片暗侧或统一遮罩条上；对比度满足 WCAG（正文感 ≥4.5:1）。  
3. `layout: bleed` + 安全区内 claim；勿在 bleed 页再塞密表/多卡。  
4. 必须有 **caption 或来源/版权**（可沉 `.fig__cap` / footnote）；证据含义用跟进页，不塞进 bleed。

## 清单（写模型前 10 秒）

- [ ] 这页是数据图还是插画？二者勿抢主位  
- [ ] 有 caption + so-what（或明确「氛围休止页无需 so-what」）  
- [ ] 无文字压焦点、无标签重叠、边距够  
- [ ] 无素材 → placeholder，不留空洞  
- [ ] 校验：`validate_report` 对缺 caption/so-what 的配图页 WARN  

> 详细几何与六版式（full/half/bleed/grid/compare/wall）→ `extract_snippet.py --task image-layout`。
