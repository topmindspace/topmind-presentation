# 信息图 · 结构图形族（flow/tree/sequence/loop）

> 由 `infographics.md` 拆出（§编号不变）。流程图/层级树/时序图/闭环规范与写法 §78–§82。
> PPTX 映射为 `diagram` / `steps` 页型，分支写 `note`；不新增页型。
> 取码：`--file infographics.md --section 78` 等。

### 78. 流程图 `flow`（分支 / 判断 / 汇合 / 异常路径）

**用途**：业务流程、审批链路、决策路径、故障处置、运营 SOP。**上限：节点 ≤20 / 判断 ≤4 / 分支层级 ≤3。**

**画法规则**：
1. **形状语义**：动作 = 圆角矩形 `rx="10"`；判断 = 菱形 `<polygon>`；起止 = 胶囊 `rx="22"`；异常/失败路径 = 虚线 + 中性色。
2. **路由**：主线水平推进；分支向下或向上引出，**正交折线**（`M…V…H…`），不画斜线。
3. **分支标签**：在分支线中点上方标条件（"是/否"、"≥80%"），字号 11、`f-txt3`。
4. **汇合**：多支路汇到同一节点时用一条竖向总线 + 逐支水平接入，避免斜线交叉。
5. **强调**：主路径 `f-acc` 实底 + `.t-on-inv` 文字；关键判断 `s-acc` 描边；异常路径 `f-s3` 底 + `s-txt3` 虚线。
6. **图例**：底部一行 chips 说明形状语义（动作 / 判断 / 异常）。

```html
<figure class="fig rv">
  <svg viewBox="0 0 900 300" style="width:100%">
    <!-- 主路径：起止 → 判断 → 动作 → 动作 → 完成 -->
    <rect x="20" y="112" width="96" height="44" rx="22" class="f-acc"/>
    <text x="68" y="139" text-anchor="middle" class="t-on-inv" font-size="13" font-weight="600">提交</text>
    <path d="M116 134 H148" class="s-acc" stroke-width="2"/>
    <polygon points="150,134 170,116 190,134 170,152" class="f-none s-acc" stroke-width="2"/>
    <text x="170" y="176" text-anchor="middle" class="f-txt3" font-size="11">口径校验</text>
    <path d="M190 134 H228" class="s-acc" stroke-width="2"/>
    <polygon points="220,129 230,134 220,139" class="f-acc"/>
    <text x="209" y="126" class="f-txt3" font-size="11">是</text>
    <rect x="230" y="112" width="120" height="44" rx="10" class="f-acc"/>
    <text x="290" y="139" text-anchor="middle" class="t-on-inv" font-size="13" font-weight="600">自动入湖</text>
    <path d="M350 134 H388" class="s-acc" stroke-width="2"/>
    <polygon points="380,129 390,134 380,139" class="f-acc"/>
    <rect x="390" y="112" width="120" height="44" rx="10" class="f-acc"/>
    <text x="450" y="139" text-anchor="middle" class="t-on-inv" font-size="13" font-weight="600">挂接契约</text>
    <path d="M510 134 H548" class="s-acc" stroke-width="2"/>
    <polygon points="540,129 550,134 540,139" class="f-acc"/>
    <rect x="550" y="112" width="110" height="44" rx="22" class="f-acc"/>
    <text x="605" y="139" text-anchor="middle" class="t-on-inv" font-size="13" font-weight="600">完成</text>
    <!-- 异常支路：判断「否」→ 人工复核 → 汇合回主线 -->
    <path d="M170 152 V240 H296" class="s-txt3" stroke-width="1.5" stroke-dasharray="5 4"/>
    <polygon points="288,235 298,240 288,245" class="f-txt3"/>
    <text x="178" y="200" class="f-txt3" font-size="11">否</text>
    <rect x="298" y="218" width="160" height="44" rx="10" class="f-s3 s-txt3"
          stroke-width="1.5" stroke-dasharray="5 4"/>
    <text x="378" y="245" text-anchor="middle" class="f-txt" font-size="13" font-weight="600">人工复核</text>
    <path d="M458 240 H540 V160" class="s-txt3" stroke-width="1.5" stroke-dasharray="5 4"/>
    <polygon points="535,168 540,158 545,168" class="f-txt3"/>
    <!-- 图例 -->
    <g font-size="11" class="f-txt3">
      <rect x="20" y="276" width="14" height="14" rx="4" class="f-acc"/>
      <text x="40" y="288">动作（主路径）</text>
      <polygon points="150,283 160,276 170,283 160,290" class="f-none s-acc" stroke-width="2"/>
      <text x="176" y="288">判断</text>
      <rect x="216" y="276" width="14" height="14" rx="4" class="f-s3"/>
      <text x="236" y="288">异常路径（需人工介入）</text>
    </g>
  </svg>
  <figcaption class="fig__cap" style="margin-top:var(--sp-4)">
    数据入湖流程：口径校验是唯一人工节点，异常路径自动转人工复核后回归主线
  </figcaption>
</figure>
```

**模型侧（PPTX 同源）**：`{"type":"diagram","layers":[["主线",[["提交","起止"],["口径校验","判断"],["自动入湖","动作"],["挂接契约","动作"],["完成","起止"]]]],"legend":["动作","判断","异常路径"],"note":"异常路径：判断为否 → 人工复核 → 回归主线"}`

### 79. 层级树 `tree`（组织 / 分解 / WBS）

**用途**：组织架构、能力分解、WBS、分类体系、因果分解（issue tree）。**上限：叶节点 ≤16 / 深度 ≤4。**

**画法规则**：
1. **正交连接**：父节点底部向下出线 → 水平总线 → 逐子节点垂直下落。**不画斜线、不画弧线**。
2. **同层等高**：同一层的节点框同高、同字号；叶节点用小一号。
3. **层级表达靠明度**：根 `f-acc`（反相文字）、中间层 `f-s2`、叶层 `f-s1`——**不引入第二色相**。
4. **宽度**：父节点框宽 ≥ 子节点之和的 60%（视觉上"撑得住"）。
5. **标签**：节点标签 ≤8 字；补充说明放图注，不塞进节点。

```html
<figure class="fig rv">
  <svg viewBox="0 0 900 300" style="width:100%">
    <!-- 根 -->
    <rect x="390" y="18" width="120" height="38" rx="8" class="f-acc"/>
    <text x="450" y="42" text-anchor="middle" class="t-on-inv" font-size="13" font-weight="600">数据平台</text>
    <!-- 主干 + 水平总线 + 垂直下落 -->
    <path d="M450 56 V86" class="s-bds" stroke-width="1.5"/>
    <path d="M140 86 H760" class="s-bds" stroke-width="1.5"/>
    <path d="M200 86 V110 M450 86 V110 M700 86 V110" class="s-bds" stroke-width="1.5"/>
    <!-- 中间层 -->
    <rect x="130" y="110" width="140" height="36" rx="8" class="f-s2"/>
    <text x="200" y="133" text-anchor="middle" class="f-txt" font-size="12" font-weight="600">数据层</text>
    <rect x="380" y="110" width="140" height="36" rx="8" class="f-s2"/>
    <text x="450" y="133" text-anchor="middle" class="f-txt" font-size="12" font-weight="600">服务层</text>
    <rect x="630" y="110" width="140" height="36" rx="8" class="f-s2"/>
    <text x="700" y="133" text-anchor="middle" class="f-txt" font-size="12" font-weight="600">应用层</text>
    <!-- 叶层连接（每组：下出 → 水平 → 两处下落） -->
    <path d="M200 146 V170 M140 170 H260 M140 170 V200 M260 170 V200" class="s-bds" stroke-width="1.5"/>
    <path d="M450 146 V170 M390 170 H510 M390 170 V200 M510 170 V200" class="s-bds" stroke-width="1.5"/>
    <path d="M700 146 V170 M640 170 H760 M640 170 V200 M760 170 V200" class="s-bds" stroke-width="1.5"/>
    <!-- 叶层 -->
    <rect x="85"  y="200" width="110" height="34" rx="6" class="f-s1"/>
    <text x="140" y="221" text-anchor="middle" class="f-txt2" font-size="11">数据湖</text>
    <rect x="205" y="200" width="110" height="34" rx="6" class="f-s1"/>
    <text x="260" y="221" text-anchor="middle" class="f-txt2" font-size="11">指标中心</text>
    <rect x="335" y="200" width="110" height="34" rx="6" class="f-s1"/>
    <text x="390" y="221" text-anchor="middle" class="f-txt2" font-size="11">数据契约</text>
    <rect x="455" y="200" width="110" height="34" rx="6" class="f-s1"/>
    <text x="510" y="221" text-anchor="middle" class="f-txt2" font-size="11">权限审计</text>
    <rect x="585" y="200" width="110" height="34" rx="6" class="f-s1"/>
    <text x="640" y="221" text-anchor="middle" class="f-txt2" font-size="11">问数入口</text>
    <rect x="705" y="200" width="110" height="34" rx="6" class="f-s1"/>
    <text x="760" y="221" text-anchor="middle" class="f-txt2" font-size="11">Agent 消费</text>
    <!-- 焦点标注 -->
    <path d="M335 262 V250" class="s-acc" stroke-width="2"/>
    <text x="390" y="278" text-anchor="middle" class="f-acc" font-size="11" font-weight="600">当前建设焦点</text>
  </svg>
  <figcaption class="fig__cap" style="margin-top:var(--sp-4)">平台能力分解：三层六项，契约与治理是当前焦点</figcaption>
</figure>
```

**模型侧**：`{"type":"diagram","layers":[["数据平台",[["数据层","数据湖 / 指标中心"],["服务层","数据契约 / 权限审计"],["应用层","问数入口 / Agent 消费"]]]],"legend":["当前建设焦点"],"note":"焦点项：数据契约（服务层）"}`

### 80. 时序图 `sequence`（参与者 × 消息 × 激活条）

**用途**：系统交互、接口调用链、多方协作时序、审批流转。**上限：参与者 ≤5 / 消息 ≤8。**

**画法规则**：
1. **参与者**：顶部横排圆角矩形（宽 140），下方引**虚线生命线**（`s-bds` + `stroke-dasharray="4 4"`）到底部。
2. **消息**：水平箭头，**右向 `f-acc`、返回 `s-txt3` 虚线**；标签写在线中段上方（字号 11）。
3. **激活条**：被调用期间在生命线上画窄条（宽 10，`f-acc`；返回后结束）——这是时序图区别于流程图的关键信息。
4. **编号**：消息可加序号（①②③）便于正文引用。
5. **文字退到图注级**：消息标签 ≤10 字，补充说明沉图注。

```html
<figure class="fig rv">
  <svg viewBox="0 0 900 300" style="width:100%">
    <!-- 参与者 -->
    <rect x="80"  y="20" width="140" height="34" rx="6" class="f-s2"/>
    <text x="150" y="42" text-anchor="middle" class="f-txt" font-size="12" font-weight="600">业务用户</text>
    <rect x="380" y="20" width="140" height="34" rx="6" class="f-acc"/>
    <text x="450" y="42" text-anchor="middle" class="t-on-inv" font-size="12" font-weight="600">智能体平台</text>
    <rect x="680" y="20" width="140" height="34" rx="6" class="f-s2"/>
    <text x="750" y="42" text-anchor="middle" class="f-txt" font-size="12" font-weight="600">指标服务</text>
    <!-- 生命线 -->
    <path d="M150 54 V280 M450 54 V280 M750 54 V280" class="s-bds" stroke-width="1"
          stroke-dasharray="4 4"/>
    <!-- 激活条 -->
    <rect x="445" y="90" width="10" height="150" rx="3" class="f-acc"/>
    <rect x="745" y="130" width="10" height="70" rx="3" class="f-accs2"/>
    <!-- 消息 -->
    <path d="M150 100 H440" class="s-acc" stroke-width="2"/>
    <polygon points="432,95 442,100 432,105" class="f-acc"/>
    <text x="295" y="92" text-anchor="middle" class="f-txt2" font-size="11">① 提问（自然语言）</text>
    <path d="M455 145 H740" class="s-acc" stroke-width="2"/>
    <polygon points="732,140 742,145 732,150" class="f-acc"/>
    <text x="597" y="137" text-anchor="middle" class="f-txt2" font-size="11">② 取指标（带口径）</text>
    <path d="M740 185 H465" class="s-txt3" stroke-width="1.5" stroke-dasharray="5 4"/>
    <polygon points="473,180 463,185 473,190" class="f-txt3"/>
    <text x="597" y="177" text-anchor="middle" class="f-txt3" font-size="11">③ 返回结果 + 来源</text>
    <path d="M440 225 H160" class="s-txt3" stroke-width="1.5" stroke-dasharray="5 4"/>
    <polygon points="168,220 158,225 168,230" class="f-txt3"/>
    <text x="295" y="217" text-anchor="middle" class="f-txt3" font-size="11">④ 回答 + 可追溯引用</text>
  </svg>
  <figcaption class="fig__cap" style="margin-top:var(--sp-4)">
    问数链路时序：平台作为编排层，指标服务返回带口径与来源的结果
  </figcaption>
</figure>
```

**模型侧**：`{"type":"steps","steps":[["① 提问","业务用户 → 智能体平台（自然语言）"],["② 取指标","平台 → 指标服务（带口径）"],["③ 返回","指标服务 → 平台（结果 + 来源）"],["④ 回答","平台 → 用户（可追溯引用）"]],"note":"激活条：平台全程激活；指标服务仅在②–③期间激活"}`

### 81. 闭环 / 飞轮 `loop`（循环增强）

**用途**：增长飞轮、PDCA、数据闭环、正反馈链路、DevOps 循环。**上限：环节 ≤6。**

**画法规则**：
1. **环状布局**：4 环节最稳（矩形四角 + 四边箭头）；6 环节沿圆周均布。
2. **箭头方向一致**（顺时针或逆时针），**箭头是主角**——它表达"闭环"而非"并列"。
3. **中心**放一句话结论（飞轮的名字 / 收益），字号大于节点。
4. **强调**：增强最快的一环用 `f-acc`，其余 `f-s2`；箭头 `s-acc`。
5. **不要用圆环本身代替箭头**：只画圆环会被读成"并列的 4 项"。

```html
<figure class="fig rv">
  <svg viewBox="0 0 900 300" style="width:100%">
    <!-- 四环节 -->
    <rect x="135" y="47"  width="150" height="46" rx="12" class="f-acc"/>
    <text x="210" y="75" text-anchor="middle" class="t-on-inv" font-size="12" font-weight="600">治理动作</text>
    <rect x="615" y="47"  width="150" height="46" rx="12" class="f-s2"/>
    <text x="690" y="75" text-anchor="middle" class="f-txt" font-size="12" font-weight="600">数据质量↑</text>
    <rect x="615" y="207" width="150" height="46" rx="12" class="f-s2"/>
    <text x="690" y="235" text-anchor="middle" class="f-txt" font-size="12" font-weight="600">业务结果↑</text>
    <rect x="135" y="207" width="150" height="46" rx="12" class="f-s2"/>
    <text x="210" y="235" text-anchor="middle" class="f-txt" font-size="12" font-weight="600">新数据沉淀</text>
    <!-- 顺时针箭头（箭头是主角） -->
    <path d="M285 70 H607" class="s-acc" stroke-width="2"/>
    <polygon points="599,64 611,70 599,76" class="f-acc"/>
    <path d="M690 93 V199" class="s-acc" stroke-width="2"/>
    <polygon points="684,191 690,203 696,191" class="f-acc"/>
    <path d="M615 230 H293" class="s-acc" stroke-width="2"/>
    <polygon points="301,224 289,230 301,236" class="f-acc"/>
    <path d="M210 207 V101" class="s-acc" stroke-width="2"/>
    <polygon points="204,109 210,97 216,109" class="f-acc"/>
    <!-- 中心结论 -->
    <text x="450" y="146" text-anchor="middle" class="f-txt" font-size="18" font-weight="700">数据增长飞轮</text>
    <text x="450" y="170" text-anchor="middle" class="f-txt3" font-size="11">治理投入 → 质量 → 结果 → 数据，逐圈增强</text>
  </svg>
  <figcaption class="fig__cap" style="margin-top:var(--sp-4)">数据增长飞轮：治理动作是起点，也是下一圈的输入</figcaption>
</figure>
```

**模型侧**：`{"type":"steps","steps":[["治理动作","起点：统一口径与契约"],["数据质量↑","可查、可信、可比"],["业务结果↑","用数决策带来收益"],["新数据沉淀","业务过程产生新数据"]],"note":"闭环：第 4 环回到第 1 环，逐圈增强"}`

### 82. 结构图形族 · 常见失败模式

| 失败 | 正确做法 |
|------|---------|
| 用 `.lane` 的文本 `→` 冒充流程图 | 真流程图用 `flow`（§78）：判断用菱形、分支标条件、异常用虚线 |
| 分支画成斜线导致交叉难读 | 正交折线（`M…V…H…`）+ 汇合总线 |
| 层级图用缩进列表代替连线 | 用 `tree`（§79）的正交连接 + 同层等高 |
| 时序图只有箭头没有激活条 | 补激活条（被调用区间），这是时序图的信息核心 |
| 闭环画成 4 个并列卡片 | 必须有**方向一致的箭头**，中心放飞轮名与收益（`loop` §81） |
| 结构图里塞整句正文 | 节点 ≤8 字；说明沉图注 / `note`（进演讲者备注） |
| 节点超上限靠缩字号硬塞 | 按上限**拆页**（铁律 11：宁拆勿挤） |
| 结构图用第二色相区分层级 | 层级靠**明度阶梯**（`f-acc → f-s2 → f-s1`），强调色只给主路径 / 焦点 |

