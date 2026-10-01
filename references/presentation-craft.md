# 演示工艺清单 · Presentation Craft（L2 · Mode A）

> **何时读**：Mode A / 正式演示 / 路演 / 演讲 / Fast 演示路径。与 `default-surface.md` 同级常读。  
> **何时不读**：Mode B 密排、Mode C 架构深读（能力保留，不反向污染 A）。  
> **定位**：优雅 · 美观 · 大气；正式场合演讲友好；版式/排版/色彩/内容组织优先；图标/图表克制配文——非 gadget deck、非咨询 dump。

## 铁律速查（Hard rules）

| 中文原则 | English | 可执行 |
|----------|---------|--------|
| 一屏一主张 | one idea per slide | 标题即结论；第二主张拆页 |
| 三秒可读 | 3-second / glance rule | 主信息 3 秒可抓；广告牌不是文档 |
| 留白即设计 | whitespace as design | 合法空：封面/章节幕/金句/收尾；内容页半空 = underfill |
| 最后一排 | back of the room | 投影正文宜大；少字号档（display/h1 · body · caption） |
| CRAP | Contrast / Repetition / Alignment / Proximity | 强焦点；跨页 chrome 锁死；左缘顶边齐；相关成组 |
| 行动标题 | action / claim title | 主张句，非「现状分析」式话题标签 |
| 少色单强调 | single accent | 2–3 主色 + 灰阶；1 accent；红仅警示 |
| 图表克制 | restrain / reduce / emphasize | 8 核图优先；简单图禁全幅；极偏禁 donut→V3 |
| 图标语义 | icons as meaning | 约 3–8/屏；固定 px 档；禁表内/图内乱插 |
| **默认无动画** | **motion = none** | 禁炫技转场/飞入作默认；HTML 翻页即可 |
| 无障碍对比 | WCAG AA | 正文 ≥4.5:1；大字/图形 ≥3:1；不靠颜色单独编码 |
| 舞台纪律 | 16:9 stage | 安全边距；一屏一重心；同页双大件 FAIL |

## 默认面（与 default-surface 对齐）

- **页型**：12 默认页型；**主力骨架 P1–P4 + P6/P10**（≈V1–V4）覆盖约 80% 页。
- **次级骨架 P7–P9 / P11–P12**：合法保留；A 下仅密表/全幅结构/一主两从等意图命中再用，**不进默认轮换**。P5 为常用扩展。
- **核图 8**：`bar` · `hbar` · `line` · `donut` · `progress` · `area` · `stack` · `dualline`。默认读面 = 纪律 + 核图；**不预读** `charts-extended.md`。
- **多样性**：先拉开核图；advanced **计入** `minTypes`（不罚）但**只按内容需要**选用，绝不为凑下限垫冷门图。

## 交付门禁（Mode A）

```
validate_report.py --strict   # presentation 自动隐含 --layout-qa
quality_gate.py … --deliver   # HTML/PPTX/evals 并行；同口径
# PPTX 交付仅 B 通道 build_pptx.js（A 通道不交付）
```

检查：V 契约 · 简单全幅 · 骨架连用 · 截断/溢出未拆页 · 半空卡 · 对齐节奏 · 主张标题 WARN · 核图多样性 · WCAG。

## 自检（上台前 30 秒）

- [ ] 标题是主张句，不是话题词  
- [ ] 眯眼可见：一条左线、一条顶线、一块重心  
- [ ] 休止页有意留白；内容页不无故半空  
- [ ] 无多强调色、无动画墙、无冷门图硬凑  
- [ ] `motion = none`；翻页靠内容节奏  


## 插画页（非数据配图）

- 情绪/产品/占位图与数据图**勿同页抢主位**；规则见 `illustration-layout.md`。
- **安全边距** ≥24px；文字不压照片焦点；标签/图例不重叠。
- **icon + chart**：icon 在注释列，不进绘图区。
- **full-bleed + 主张叠字**（Mode A）：仅封面/章节幕/金句/收尾；遮罩保对比度；必有 caption/来源；证据另页。
- 配图页写 **caption + so-what**（氛围休止页可免 so-what）；校验对缺项 WARN。

## 长文与信息承载（anti-truncation）

> **硬原则**：大量文字**不得**为了「看起来像稀疏演示样页」而被故意压缩或删除。留白是设计；**删掉证据 / so-what / 口径不是设计**。

**Mode A 仍主张一屏一主张**——但「一主张」可以带充分证据：次要卡、列表、表、跟进页。内容密时优先**加结构**，不砍实质。

### 溢出处置顺序（铁律 · 与 `containers.overflowRule` 同源）

1. **重构承载**：段落 → 列表 / 卡片 / 表 / 图 / 组合版式  
2. **拆页 / 分章**：议程→主张→证据卡→明细列表等多页序列；01a/01b；多部分章节  
3. **换布局形态**：V1–V4 · 多列 · 卡栅格 · `g-side` / `g-bento`  
4. **有限 `fontShrink`**（阶梯内、模式 floor 以上，最多 4 档）  
5. **禁止**静默截断、砍 so-what、砍证据、为审美稀疏而删决策必需信息

### 密度许可

- 卡片/列表页在主张清楚时可**偏密**（多卡、多条），仍须可读、对齐、一重心。  
- 单页字数预算是**溢出预警**，不是「字数太多就删」的许可证；超预算先走 1–3 步。  
- 校验：`overflow-without-split` / 截断迹象 → FAIL 或 WARN；**不为「字多」单独 FAIL**。

> *Hard rules protect the stage; adaptive choices serve the content.*
