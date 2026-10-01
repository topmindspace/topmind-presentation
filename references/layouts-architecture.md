# 结构组件与锁定版式 · layouts-architecture.md

> 由 `components.md` 拆出（§编号保持不变，跨文件稳定引用）。
> 取码：`python scripts/extract_snippet.py --file components.md --section <编号>`
> 或直接 `--file layouts-architecture.md --section <编号>`。整读大文件视为违规。

## 37. architecture 模式 · 分层架构带（模式 C 专属）



```html
<section class="band band--fit" id="arch">
  <div class="wrap">
    <div class="shead rv">
      <div class="t-eyebrow">02 · 总体架构</div>
      <h2 class="t-h1 shead__title">四层一驱：治理嵌入每一层</h2>
    </div>
    <div class="arch rv">
      <!-- 每层：层名 + 节点网格；焦点层加 --focus -->
      <div class="arch__layer arch__layer--focus">
        <div class="arch__lname">应用层</div>
        <div class="arch__nodes">
          <div class="arch__node arch__node--accent">
            <div class="arch__nt">ChatBI 问数</div>
            <div class="arch__nd">对话式取数</div>
          </div>
          <div class="arch__node">
            <div class="arch__nt">Agent 消费</div>
            <div class="arch__nd">护栏内调用</div>
          </div>
        </div>
      </div>
      <div class="arch__layer">
        <div class="arch__lname">服务层</div>
        <div class="arch__nodes">
          <div class="arch__node"><div class="arch__nt">数据契约</div><div class="arch__nd">SLA 保障</div></div>
        </div>
      </div>
      <!-- …语义层 / 底座层同构… -->
    </div>
    <div class="arch__legend">
      <span class="chip chip--accent">当前建设焦点</span>
      <span class="chip">已有能力</span>
    </div>
  </div>
</section>
```

---

## 38. architecture 模式 · 流程管线（SVG，图为王）

```html
<figure class="fig rv">
  <svg class="chart" data-chart="gantt" viewBox="0 0 900 240" style="width:100%">
    <!-- 五段管线：圆角横条 + 节点标签 + 流向箭头 -->
    <rect data-anim="fade" x="20"  y="80" width="150" height="52" rx="10" class="f-s2"/>
    <text x="95" y="103" text-anchor="middle" class="f-txt" font-size="14" font-weight="600">采集</text>
    <text x="95" y="122" text-anchor="middle" class="f-txt3" font-size="11">多源接入</text>
    <path d="M170 106 L200 106" class="s-txt3" stroke-width="2" stroke-dasharray="4 4"/>
    <polygon points="200,101 210,106 200,111" class="f-txt3"/>
    <rect data-anim="fade" x="210" y="80" width="150" height="52" rx="10" class="f-acc"/>
    <text x="285" y="103" text-anchor="middle" class="t-on-inv" font-size="14" font-weight="600">入湖</text>
    <text x="285" y="122" text-anchor="middle" class="t-on-inv" font-size="11">统一底座</text>
    <!-- …注册 → 治理 → 消费 同构… -->
  </svg>
  <figcaption class="fig__cap" style="margin-top:var(--sp-4)">数据全链路：五段管线，治理内嵌</figcaption>
</figure>
```

> architecture 模式规则（每页一图、节点 ≤24、文字退到图注级）见 `modes.md` 模式 C；PPTX 导出用 `diagram` 页型。

---

## 38b. architecture 模式 · 泳道 + 层间连接件（锁定版式 A2 / A1 配件）

```html
<!-- 泳道：行 = 角色/阶段；步骤横排 + CSS 正交箭头（.lane__arr 线段+箭头，禁裸文字 →） -->
<div class="stack rv gap-3">
  <div class="lane">
    <div class="lane__hd">业务域</div>
    <div class="lane__body">
      <span class="lane__step">提需求</span><span class="lane__arr" aria-hidden="true"></span>
      <span class="lane__step">确认口径</span><span class="lane__arr" aria-hidden="true"></span>
      <span class="lane__step lane__step--a">Agent 取数</span><span class="lane__arr" aria-hidden="true"></span>
      <span class="lane__step">验收结果</span>
    </div>
  </div>
  <div class="lane">
    <div class="lane__hd">数据平台</div>
    <div class="lane__body">
      <span class="lane__step">契约校验</span><span class="lane__arr" aria-hidden="true"></span>
      <span class="lane__step">指标服务</span><span class="lane__arr" aria-hidden="true"></span>
      <span class="lane__step">审计留痕</span>
    </div>
  </div>
</div>

<!-- 层间连接：A1 分层带两层之间插一行（主链路 accent、次链路中性） -->
<div class="arch__conn"><svg width="16" height="20" viewBox="0 0 16 20" fill="none"
  stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M8 1v14M3 11l5 5 5-5"/></svg></div>
```

> 泳道每行 ≤6 步；`lane__step--a` 高亮关键节点（每行最多 1 个）；跨行依赖用右侧图例或 SVG 正交箭头表达，不斜穿泳道。
> **PPTX 映射**：A2 泳道页 → `lane` 页型（`lanes=[[行头,[步骤…]…]…]`，步骤 str 或 `{t,accent}`）；A3 管线页 → 单泳道 `lane`（五步管线）；A1 分层带 → `diagram` 页型（architecture 模式自动走全幅几何）。

---

