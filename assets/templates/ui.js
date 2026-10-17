/* ══ topmind-presentation 公共 UI 脚本（assets/templates/ui.js）══
   由 scripts/sync_runtime.py 注入到 templates/*.html 的 __TOPPPT_UI__ 标记块 · 禁止在各模板手改。
   含：主题切换 / header 工具组（风格下拉·预览·帮助·全屏·折叠）/ 滚动显现 / PPT 翻页页码 /
       图表轻量动效 / PPTX 预览模态（WYSIWYG + 可复制 AI 提示词）/
       快捷键（T 主题 · P 预览 · H 帮助 · F 全屏 · B 收起/展开工具栏）。
   注：三模式为生成时确定的独立形态——此处无模式切换；风格为纯视觉皮肤可实时切换。
   页面不提供 PPTX 导出（浏览器端达不到 strict 硬门禁质量）；正式 PPTX 由
   本地智能体走精导通道生成，预览即"交付所见"（同一序列化引擎）+ 提示词引导后续补生成。
   主题记忆按文件隔离（report-theme:<pathname>）且系统偏好不覆盖模板出厂
        data-theme；
        翻页引擎：飞行期禁 scroll-snap / 连按直跳 / 滚轮打断 / 模态打开不翻页；
        header 全屏按钮（F）与折叠（B，收起成迷你工具条）。 */

/* ── 主题切换（记忆按文件隔离；出厂 data-theme 优先于系统偏好） ── */
(function(){var r=document.documentElement,b=document.getElementById('themeBtn'),
  K='report-theme:'+(location.pathname||'index');
if(!b)return;
function a(t){r.setAttribute('data-theme',t);try{localStorage.setItem(K,t)}catch(e){}
  /* 主题切换实时同步模型（预览与导出按当前主题出亮/暗版） */
  if(window.REPORT_MODEL)window.REPORT_MODEL.theme=t;}
var s=null;try{s=localStorage.getItem(K)}catch(e){}
if(s==='light'||s==='dark'){a(s)}
else if(!r.getAttribute('data-theme')&&window.matchMedia&&
window.matchMedia('(prefers-color-scheme: dark)').matches){a('dark')}
b.addEventListener('click',function(){a(r.getAttribute('data-theme')==='dark'?'light':'dark')})})();

/* ── header 全屏按钮（F 键同效） ── */
(function(){
  var b=document.getElementById('fsBtn');if(!b)return;
  function sync(){var on=!!(document.fullscreenElement||document.webkitFullscreenElement);
    document.documentElement.classList.toggle('is-fs',on);
    b.title=(on?'退出全屏':'全屏（F）')}
  b.addEventListener('click',function(){
    var d=document,el=d.documentElement;
    if(d.fullscreenElement||d.webkitFullscreenElement){
      var ex=d.exitFullscreen||d.webkitExitFullscreen;
      if(ex)ex.call(d)}
    else{var fn=el.requestFullscreen||el.webkitRequestFullscreen;
      if(fn){var p=fn.call(el);if(p&&p.catch)p.catch(function(){})}}
  });
  ['fullscreenchange','webkitfullscreenchange'].forEach(function(ev){
    document.addEventListener(ev,sync)});
  sync();
})();

/* ── header 折叠/展开（收起成迷你工具条 · B 键同效 · 记忆按文件隔离） ── */
(function(){
  var b=document.getElementById('barFold');if(!b)return;
  var K='report-bar-fold:'+(location.pathname||'index');
  function folded(){return document.documentElement.classList.contains('bar--fold')}
  function set(v){
    document.documentElement.classList.toggle('bar--fold',v);
    try{localStorage.setItem(K,v?'1':'0')}catch(e){}
    /* --bar-h 收紧会改变 band--fit 高度与锚点，动画结束后重算当前页 */
    setTimeout(function(){try{window.dispatchEvent(new Event('resize'))}catch(e){}},320);
  }
  b.addEventListener('click',function(){set(!folded())});
  try{if(localStorage.getItem(K)==='1')set(true)}catch(e){}
})();

/* ── header 工具组：风格下拉 + 帮助模态 ── */
(function(){
  var STYLES=[
    ['business-blue','清新蓝白','#1a73e8'],['apple-mono','优雅黑白','#1d1d1f'],
    ['mckinsey','麦肯锡','#003a70'],['brand-red','品牌红','#d0021b'],
    ['warm-sand','暖沙金','#96681f'],['deep-teal','墨绿','#0f6b5c'],
    ['graphite-dark','石墨','#0369a1'],['indigo-violet','靛紫','#5b5bd6'],
    ['spectrum','彩色','#4563ef'],['ink-academic','学术墨蓝','#1f3a5f'],
    ['coral-launch','活力珊瑚','#c4402a'],['sky-airy','晴空课件','#0b7bc4']];
  /* M3 风格库：换风格同时换密度档（styleGrammar.density；layout-constants 单源，sync_runtime 校验一致） */
  var DENSITY={"business-blue":"normal","apple-mono":"airy","mckinsey":"dense","brand-red":"normal","warm-sand":"airy","deep-teal":"normal","graphite-dark":"dense","indigo-violet":"normal","spectrum":"dense","ink-academic":"dense","coral-launch":"airy","sky-airy":"airy"};
  var r=document.documentElement;
  function syncModel(){if(window.REPORT_MODEL){
    window.REPORT_MODEL.style=r.getAttribute('data-style')}}
  var seld=document.getElementById('styleSel');
  if(seld){
    var btn=document.getElementById('styleBtn'),list=document.getElementById('styleList');
    STYLES.forEach(function(s){
      var b=document.createElement('button');b.type='button';b.className='sitem';
      b.setAttribute('data-style',s[0]);b.title=s[1];
      b.innerHTML='<span class="swd" style="background:'+s[2]+'"></span>'+s[1];
      if(s[0]===r.getAttribute('data-style'))b.classList.add('on');
      b.addEventListener('click',function(){
        r.setAttribute('data-style',s[0]);r.setAttribute('data-density',DENSITY[s[0]]||'normal');
        list.querySelectorAll('.sitem').forEach(function(x){x.classList.remove('on')});
        b.classList.add('on');syncModel();
        seld.classList.remove('open')});   /* MD3 menu 惯例：选中即收起 */
      list.appendChild(b)});
    btn.addEventListener('click',function(e){e.stopPropagation();
      seld.classList.toggle('open')});
    document.addEventListener('click',function(e){
      if(!seld.contains(e.target))seld.classList.remove('open')});
  }
  /* 帮助模态（PPT 生成指引：双通道说明 + 可复制提示词） */
  var hmodal=document.getElementById('helpModal');
  if(hmodal){
    var hb=document.getElementById('helpBtn');
    var hclose=document.getElementById('helpClose');
    var hcopy=document.getElementById('helpCopy');
    if(hb)hb.addEventListener('click',function(){hmodal.classList.add('open')});
    if(hclose)hclose.addEventListener('click',function(){hmodal.classList.remove('open')});
    hmodal.addEventListener('click',function(e){if(e.target===hmodal)hmodal.classList.remove('open')});
    if(hcopy)hcopy.addEventListener('click',function(){
      var tx=document.getElementById('helpPrompt');
      var text=tx?tx.textContent:'';
      function done(){hcopy.textContent='已复制 ✓';
        setTimeout(function(){hcopy.textContent='复制 AI 提示词'},1600)}
      function fallback(){
        var ta=document.createElement('textarea');ta.value=text;
        document.body.appendChild(ta);ta.select();
        try{document.execCommand('copy');done()}catch(e){}ta.remove();}
      if(navigator.clipboard&&navigator.clipboard.writeText){
        navigator.clipboard.writeText(text).then(done,fallback)}
      else fallback();
    });
  }
})();

/* ── 滚动显现 ── */
(function(){var i=document.querySelectorAll('.rv');
if(!('IntersectionObserver' in window)){i.forEach(function(e){e.classList.add('in')});return}
var o=new IntersectionObserver(function(es){es.forEach(function(e){
if(e.isIntersecting){e.target.classList.add('in');o.unobserve(e.target)}})},
{threshold:.08,rootMargin:'0px 0px -48px 0px'});i.forEach(function(e){o.observe(e)})})();

/* ── PPT 翻页：方向键整屏翻页 + 页码指示
   翻页要点：① 飞行期临时禁用 scroll-snap（平滑滚动与吸附互相拉扯是卡顿/回弹根因）；
   ② 450ms 内连按直跳落位，不反复重启平滑滚动；③ 滚轮/触摸即打断飞行并恢复吸附；
   ④ 预览/帮助模态打开时不翻页；⑤ 空格不劫持聚焦中的按钮/链接。 ── */
(function(){
  var pages=[].slice.call(document.querySelectorAll('section.band'));
  var dots=document.getElementById('pagerDots');
  var count=document.getElementById('pagerCount');
  if(!pages.length||!dots)return;
  var flying=false,pending=-1,lastGo=0,restoreTO=null;
  var dotEls=pages.map(function(sec,i){
    var d=document.createElement('button');
    d.className='pager__dot';d.type='button';
    d.setAttribute('aria-label','第 '+(i+1)+' 页');
    d.addEventListener('click',function(){go(i)});
    dots.appendChild(d);return d;
  });
  function modalOpen(){return !!document.querySelector('.pmodal.open')}
  function pageTop(i){return pages[i].getBoundingClientRect().top+window.scrollY}
  function idx(){
    var y=window.scrollY+window.innerHeight*0.4,best=0,bd=1e9;
    pages.forEach(function(sec,i){
      var d=Math.abs(pageTop(i)-y);
      if(d<bd){bd=d;best=i}
    });
    return best;
  }
  function mark(c){
    dotEls.forEach(function(d,i){d.classList.toggle('on',i===c)});
    if(count)count.textContent=(c+1)+' / '+pages.length;
  }
  function snap(on){document.documentElement.style.scrollSnapType=on?'':'none'}
  function land(){flying=false;pending=-1;snap(true);mark(idx())}
  function interrupt(){if(flying){flying=false;pending=-1;clearTimeout(restoreTO);snap(true)}}
  function go(i){
    i=Math.max(0,Math.min(pages.length-1,i));
    if(flying&&i===pending)return;
    var now=Date.now(),instant=(now-lastGo)<450;   /* 连按直跳：防平滑滚动反复重启打架 */
    lastGo=now;pending=i;flying=true;
    mark(i);snap(false);clearTimeout(restoreTO);
    try{pages[i].scrollIntoView({behavior:instant?'auto':'smooth',block:'start'})}
    catch(e){pages[i].scrollIntoView()}
    restoreTO=setTimeout(land,instant?150:900);
  }
  function paint(){if(flying)return;mark(idx())}
  var KEY_NEXT=['ArrowRight','ArrowDown','PageDown',' '];
  var KEY_PREV=['ArrowLeft','ArrowUp','PageUp'];
  document.addEventListener('keydown',function(e){
    var tag=(e.target&&e.target.tagName)||'';
    if(/INPUT|TEXTAREA|SELECT/.test(tag))return;
    if(e.key===' '&&tag!=='BODY')return;          /* 空格留给聚焦中的按钮/链接 */
    if(modalOpen())return;                        /* 预览/帮助模态打开时不翻页 */
    var base=(flying&&pending>-1)?pending:idx();  /* 飞行中按基准页继续翻，不回跳 */
    if(KEY_NEXT.indexOf(e.key)>-1){e.preventDefault();go(base+1)}
    else if(KEY_PREV.indexOf(e.key)>-1){e.preventDefault();go(base-1)}
    else if(e.key==='Home'){e.preventDefault();go(0)}
    else if(e.key==='End'){e.preventDefault();go(pages.length-1)}
  });
  /* 用户主动滚动（滚轮/触摸）→ 立即打断飞行并恢复吸附 */
  ['wheel','touchstart'].forEach(function(ev){
    window.addEventListener(ev,function(){interrupt();paint()},{passive:true});
  });
  if('onscrollend' in window)window.addEventListener('scrollend',function(){
    if(flying)land()});
  var raf=null;
  window.addEventListener('scroll',function(){
    if(raf)return;
    raf=requestAnimationFrame(function(){paint();raf=null});
  },{passive:true});
  window.addEventListener('resize',paint);
  paint();
})();

/* ── 图表轻量动效：进入视口触发 生长/描边/扫入/计数 ── */
(function(){
  if(!('IntersectionObserver' in window))return;
  function countUp(el){var t=parseFloat(el.dataset.count),s=el.dataset.suffix||'',
    d=(el.dataset.count.split('.')[1]||'').length,t0=null;
    (function st(ts){if(!t0)t0=ts;var p=Math.min(1,(ts-t0)/900);
      el.textContent=(t*p).toFixed(d)+s;if(p<1)requestAnimationFrame(st)})(performance.now());}
  var EASE='stroke-dashoffset 1s cubic-bezier(.05,.7,.1,1)';
  function all(g,sel){return [].slice.call(g.querySelectorAll(sel))}
  var io=new IntersectionObserver(function(es){
    var hit=[],draws=[],sweeps=[],counts=[];
    es.forEach(function(e){if(!e.isIntersecting)return;
      var g=e.target;io.unobserve(g);hit.push(g);
      draws=draws.concat(all(g,'[data-draw]'));
      sweeps=sweeps.concat(all(g,'[data-sweep]'));
      counts=counts.concat(all(g,'[data-count]'));});
    if(!hit.length)return;
    /* 先集中量（读），再集中写：逐条 getTotalLength 与改样式交替会反复触发强制回流 */
    var lens=draws.map(function(p){return p.getTotalLength()});
    hit.forEach(function(g){g.classList.add('in')});
    draws.forEach(function(p,i){p.style.willChange='stroke-dashoffset';
      p.style.strokeDasharray=lens[i];p.style.strokeDashoffset=lens[i]});
    sweeps.forEach(function(c){var L=+c.dataset.circ;c.style.willChange='stroke-dashoffset';
      c.style.strokeDasharray=L;c.style.strokeDashoffset=L});
    counts.forEach(countUp);
    requestAnimationFrame(function(){
      draws.forEach(function(p){p.style.transition=EASE;p.style.strokeDashoffset=0});
      sweeps.forEach(function(c){c.style.transition=EASE;
        c.style.strokeDashoffset=(+c.dataset.circ)*(1-(+c.dataset.p))});
    });
    /* will-change 长期驻留会占用合成层内存，动画结束即撤下 */
    setTimeout(function(){draws.concat(sweeps).forEach(function(el){el.style.willChange=''})},1200);
  },{threshold:.3});
  document.querySelectorAll('.chart,[data-chart]').forEach(function(el){io.observe(el)});
})();

/* ── research 导航轨高亮（滚动跟随；rail 默认注释不启用，启用后自动生效） ── */
(function(){
  var rail=document.getElementById('rail');if(!rail)return;
  var as=[].slice.call(rail.querySelectorAll('.rail__a'));
  if(!as.length)return;
  var raf=null,tops=[];
  /* 章节位置缓存：长报告里每帧对每个锚点做 querySelector + 读 offsetTop 会反复触发同步布局 */
  function measure(){tops=as.map(function(a){
    var s=document.querySelector(a.getAttribute('href'));return s?s.offsetTop:null})}
  function paint(){var y=window.scrollY+window.innerHeight*0.4,best=0,bd=1e9;
    tops.forEach(function(t,i){if(t==null)return;
      var d=Math.abs(t-y);if(d<bd){bd=d;best=i}});
    as.forEach(function(a,i){a.classList.toggle('on',i===best)});raf=null}
  window.addEventListener('scroll',function(){if(raf)return;
    raf=requestAnimationFrame(paint)},{passive:true});
  window.addEventListener('resize',function(){measure();paint()});
  measure();paint();
})();

/* ══ PPTX 页序预览 / 提示词复制 / 快捷键
   M2：页序由运行时 pagePlan()（与 build_pptx.js 同一求解器）给出，缩略图克隆页面幻灯片；
   版式几何只在精导通道 build_pptx.js 实现一次。 ══ */
(function(){
  var modal=document.getElementById('pptModal');
  var body=document.getElementById('pptBody'),meta=document.getElementById('pptMeta'),
      issues=document.getElementById('pptIssues'),
      copy=document.getElementById('pptCopy'),closeBtn=document.getElementById('pptClose');
  var helpModal=document.getElementById('helpModal');

  var PROMPT=[
'请为这份 HTML 报告生成可编辑 PPTX 并交付：',
'1) 阅读 references/pptx-export.md 与 references/modes.md（三模式独立规则）；',
'2) 核对/补全 window.REPORT_MODEL 为与正文严格一致的内容（含 mode/style/theme/title/agenda/sections/closing；theme 为 light 或 dark、与页面 data-theme 一致——PPTX 按此导出亮色版或深色版；29 种页型字段与 30 类 chart.type 见 scripts/model-schema.json；research 关键图表页用 type:"exhibit" 并填 exhibitNo/soWhat(结论条)/footnote）；',
'3) 运行 python scripts/validate_report.py <报告.html> 直到全 PASS（含模型一致性检查）；',
'4) 智能体精导并质检（0/0 才交付）：python scripts/extract_model.py <报告.html> → NODE_PATH=<pptxgenjs 所在 node_modules> node scripts/build_pptx.js <报告.pptx> --model=<报告.model.json>（如需覆盖模型主题可加 --theme=light|dark） → python scripts/validate_pptx.py <报告.pptx> --strict --model=<报告.model.json>。',
'报告文件：<请填写报告.html 的路径>'
  ].join('\n');
  var promptEl=document.getElementById('helpPrompt');
  if(promptEl)promptEl.textContent=PROMPT;

  function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

  /* ── 页序预览（M2 同源）：页序来自运行时 pagePlan()（与 build_pptx.js 同一求解器拆页），
     缩略图直接克隆页面上对应的 HTML 幻灯片——不再有第二套浏览器端几何引擎。 ── */
  function pageSections(){
    return [].slice.call(document.querySelectorAll('main section, body > section')).filter(function(x){
      return !x.closest('.pmodal')&&x.offsetHeight>0});
  }
  function norm(t){return String(t||'').replace(/\s+/g,'').replace(/（续）$/,'')}
  function findSection(pg,i,n,secs){
    if(pg.kind==='cover')return secs[0]||null;
    if(pg.kind==='closing')return secs[secs.length-1]||null;
    if(pg.kind==='agenda')return secs.filter(function(x){return x.querySelector('.agenda')})[0]||null;
    var key=norm(pg.title).slice(0,14);
    if(!key)return null;
    for(var k=0;k<secs.length;k++){
      var h=secs[k].querySelector('h1,h2,.slide__title,.sec__title');
      if(h&&norm(h.textContent).indexOf(key)>=0)return secs[k];
    }
    return null;
  }
  var TYPE_CN={cover:'封面',agenda:'大纲',closing:'收尾'};
  function renderPage(pg,i,secs){
    var card=document.createElement('div');card.className='pslide';
    var src=findSection(pg,i,0,secs);
    if(src){
      var stage=document.createElement('div');stage.className='pslide__stage';
      var clone=src.cloneNode(true);
      clone.removeAttribute('id');[].forEach.call(clone.querySelectorAll('[id]'),function(e){e.removeAttribute('id')});
      clone.classList.add('pslide__clone');
      clone.style.width=src.offsetWidth+'px';clone.style.height=src.offsetHeight+'px';
      clone.setAttribute('data-w',src.offsetWidth);
      stage.appendChild(clone);card.appendChild(stage);
    }else{
      var ph=document.createElement('div');ph.className='pslide__ph';
      ph.textContent=pg.title||'（无标题）';card.appendChild(ph);
    }
    var cap=document.createElement('div');cap.className='pslide__cap';
    cap.innerHTML='<b>'+(i+1)+'</b> · '+escHtml(TYPE_CN[pg.kind]||pg.type)+(pg.cont?' · 续页':'')
      +'<span>'+escHtml(pg.title||'')+'</span>';
    card.appendChild(cap);
    return card;
  }
  function fitSlides(){
    [].forEach.call(body.querySelectorAll('.pslide__clone'),function(c){
      var st=c.parentNode,w=+c.getAttribute('data-w')||1;
      var k=st.clientWidth/w;c.style.transform='scale('+k+')';
    });
  }
  function currentModel(){
    var m=window.REPORT_MODEL;
    if(m){var r=document.documentElement;
      m.style=r.getAttribute('data-style')||m.style;
      m.theme=r.getAttribute('data-theme')||m.theme||'light';}
    return m;
  }

  /* ── 打开模态：WYSIWYG 预览（与通道 B 同一序列化输出）+ 自检结果 + 常显可复制提示词 ── */
  function open(){
    if(!modal||!body||!meta||!issues)return;   /* 预览骨架缺失时优雅降级（不影响其它快捷键） */
    var m=currentModel();
    var chk=(window.TopPptHtml&&window.TopPptHtml.validateModel)
      ?window.TopPptHtml.validateModel(m)
      :{ok:false,missing:['预览运行时缺失'],warnings:[],pages:0};
    meta.textContent=(m&&m.title?m.title:'未命名报告')+' · '+(m&&m.style||'business-blue')
      +' · '+((m&&m.theme)==='dark'?'深色':(m&&m.theme)==='light'?'浅色':'浅色')
      +' · '+(m&&m.mode||'presentation')+' · '+(chk.pages||0)+' 页';
    body.innerHTML='';
    if(window.TopPptHtml&&m&&m.sections){
      try{
        var secs=pageSections();
        window.TopPptHtml.pagePlan(m).forEach(function(pg,i){body.appendChild(renderPage(pg,i,secs))});
      }catch(e){body.innerHTML='<div class="t-sm">预览渲染失败：'+escHtml(e.message)+'</div>'}
    }else if(!m){
      body.innerHTML='<div class="t-sm">报告未内嵌 window.REPORT_MODEL 内容模型，无法预览。请按下方提示词回到 AI 对话补全。</div>';
    }
    if(chk.ok){
      issues.innerHTML='<b>模型自检通过</b>：内容完整（'+chk.pages+' 页）。页序与精导 PPTX 一致（同一布局求解器拆页）；'
        +'缩略图为本页面对应幻灯片，交付 PPTX 中核心图表为原生可编辑图表（双击即可改数据）。'
        +(chk.warnings.length?'<br>· '+chk.warnings.map(escHtml).join('<br>· '):'')
        +'<br>本页面不直接导出 PPTX——复制下方提示词交给 AI，由智能体精导通道生成并过 strict 校验（0/0）后交付。'
        +'<div class="pmodal__prompt">'+escHtml(PROMPT)+'</div>';
    }else{
      issues.innerHTML='<b>模型不完整</b>：'
        +chk.missing.map(escHtml).join('、')
        +'<br>预览为尽力渲染；复制下方提示词回到 AI 对话补全模型并由智能体精导交付。'
        +'<div class="pmodal__prompt">'+escHtml(PROMPT)+'</div>';
    }
    if(copy)copy.style.display='';
    modal.classList.add('open');
    requestAnimationFrame(fitSlides);
  }
  function close(){if(modal)modal.classList.remove('open')}

  /* 按钮 wiring（header 预览 / 帮助） */
  var previewBtn=document.getElementById('pptPreviewBtn');
  if(previewBtn)previewBtn.addEventListener('click',open);
  if(closeBtn)closeBtn.addEventListener('click',close);
  if(modal)modal.addEventListener('click',function(e){if(e.target===modal)close()});
  if(copy)copy.addEventListener('click',function(){
    function done(){copy.textContent='已复制 ✓';
      setTimeout(function(){copy.textContent='复制 AI 提示词'},1600)}
    function fallback(){
      var ta=document.createElement('textarea');ta.value=PROMPT;
      document.body.appendChild(ta);ta.select();
      try{document.execCommand('copy');done()}catch(e){}ta.remove();}
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(PROMPT).then(done,fallback)}
    else fallback();
  });

  /* 快捷键：T 主题 / F 全屏 / B 收起工具栏 / P 预览 / H 帮助 / Esc 关闭 */
  document.addEventListener('keydown',function(e){
    var tag=(e.target&&e.target.tagName)||'';
    if(/INPUT|TEXTAREA|SELECT/.test(tag))return;
    if(e.key==='Escape'){
      close();
      if(helpModal)helpModal.classList.remove('open');
      var seld=document.getElementById('styleSel');
      if(seld)seld.classList.remove('open');
      return;
    }
    if(e.altKey||e.ctrlKey||e.metaKey)return;
    /* 模态打开时屏蔽内容快捷键：预览态整页锁定；帮助态仅 Esc（上方已处理）可用 */
    if((modal&&modal.classList.contains('open'))||
       (helpModal&&helpModal.classList.contains('open')))return;
    var k=e.key.toLowerCase();
    if(k==='t'){e.preventDefault();
      var tb=document.getElementById('themeBtn');if(tb)tb.click()}
    else if(k==='f'){e.preventDefault();        /* 全屏 */
      var fb=document.getElementById('fsBtn');if(fb)fb.click()}
    else if(k==='b'){e.preventDefault();        /* 收起/展开工具栏 */
      var bb=document.getElementById('barFold');if(bb)bb.click()}
    else if(k==='p'){e.preventDefault();open()}
    else if(k==='h'){e.preventDefault();
      if(helpModal)helpModal.classList.add('open')}
  });

  window.addEventListener('resize',function(){
    if(modal&&modal.classList.contains('open'))fitSlides()},{passive:true});
})();

/* ── M12 行距回退（containers.lineSpacing）：正文默认 1.5；某页内容高于一屏时给该页加 lh-tight 降到 1.3，不再更低 ── */
(function(){
  function fit(){
    [].forEach.call(document.querySelectorAll('section.band'),function(b){
      b.classList.remove('lh-tight');
      if(b.classList.contains('band--cover'))return;
      var lim=parseFloat(getComputedStyle(b).minHeight)||window.innerHeight;
      if(b.scrollHeight>lim+2)b.classList.add('lh-tight');
    });
  }
  var t;function later(){clearTimeout(t);t=setTimeout(fit,120)}
  if(document.readyState==='complete')fit();else window.addEventListener('load',fit);
  window.addEventListener('resize',later,{passive:true});
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);
})();
