#!/usr/bin/env node
/* topmind-presentation · 主题参考图生成器（维护工具，非交付依赖、非交付硬门禁）
 *
 * 用法：
 *   npm install playwright            # 或在任意位置安装 playwright 后设置 NODE_PATH
 *   npx playwright install chromium   # 首次需要下载浏览器
 *   node scripts/capture_theme_overview.js [--channel=msedge|chrome|chromium] [--scale=1.25]
 *
 * --scale = deviceScaleFactor（默认 1.25）。参考图只用于"让用户看见风格与主题"，
 * 1.25 在 1480px 视口下已足够清晰，同时把单张 PNG 控制在 ~1MB 内（便于在 IDE 里快速打开）。
 *
 * 浏览器通道自动探测：优先命令行 --channel=，其次环境变量 TOP_PPT_BROWSER_CHANNEL，
 * 最后回落到 Playwright 自带的 chromium（无本机浏览器依赖）。
 *
 * 产物（assets/，覆盖旧图）：
 *   theme-overview.png                      —— 默认（演示 Tab）整体参考图（= 演示态）
 *   theme-overview-research.png             —— 研究模式 Tab（咨询密排形态）
 *   theme-overview-architecture.png         —— 架构模式 Tab（图为王形态）
 *
 * 演示态与整体图内容相同，不再单独写 theme-overview-presentation.png。
 * 每次截图前断言当前 Tab 文案，防止 Tab 切换未生效导致产出雷同图。 */
const path = require('path');
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  console.error('未找到 playwright。请先安装：npm install playwright && npx playwright install chromium');
  console.error('（本脚本仅用于刷新 assets/theme-overview*.png 参考图，非技能交付依赖。）');
  process.exit(2);
}

const TAB_TEXT = { presentation: '演示汇报', research: '研究报告', architecture: '信息架构图' };
const channelArg = (process.argv.find((a) => a.startsWith('--channel=')) || '').split('=')[1];
const scaleArg = parseFloat((process.argv.find((a) => a.startsWith('--scale=')) || '').split('=')[1]);
const SCALE = Number.isFinite(scaleArg) && scaleArg > 0 ? scaleArg : 1.25;
const CHANNEL = channelArg || process.env.TOP_PPT_BROWSER_CHANNEL
  || process.env.TOP_PPT_BROWSER_CHANNEL || '';

(async () => {
  const gallery = 'file:///' + path.resolve(__dirname, '../assets/style-gallery.html').replace(/\\/g, '/');
  const outDir = path.resolve(__dirname, '../assets');
  /* channel 为空 → 用 Playwright 自带 chromium（不依赖本机已装浏览器） */
  const browser = await chromium.launch(CHANNEL ? { channel: CHANNEL } : {});
  const page = await browser.newPage({ viewport: { width: 1480, height: 1200 }, deviceScaleFactor: SCALE });
  await page.goto(gallery);
  await page.waitForSelector('.preset');

  const modes = ['presentation', 'research', 'architecture'];
  for (const m of modes) {
    const idx = modes.indexOf(m);
    await page.evaluate((i) => document.querySelectorAll('.mtab')[i].click(), idx);
    await page.waitForTimeout(500);
    const on = await page.evaluate(() =>
      (document.querySelector('.mtab.on .mtab__t') || {}).textContent || '');
    if (on !== TAB_TEXT[m]) {
      throw new Error(`Tab 切换断言失败：期望「${TAB_TEXT[m]}」实际「${on}」（防止雷同图回归）`);
    }
    /* 卡片数必须等于单源风格数（PRESETS 由 sync_runtime.py 从 layout-constants.json 注入），
     * 防止「扩了风格但画廊/参考图没跟上」的静默漂移（旧断言只查 n < 9，太弱）。 */
    const n = await page.evaluate(() => document.querySelectorAll('.preset').length);
    const expected = await page.evaluate(() =>
      (typeof PRESETS === 'object' && PRESETS) ? Object.keys(PRESETS).length : 0);
    if (expected && n !== expected) {
      throw new Error(`画廊卡片数 ${n} ≠ 单源风格数 ${expected}（画廊与 layout-constants.json 漂移）`);
    }
    if (n < 9) throw new Error(`卡片数异常：${n}`);
    // presentation tab → theme-overview.png only (no duplicate *-presentation.png)
    if (m === 'presentation') {
      await page.screenshot({ path: path.join(outDir, 'theme-overview.png'), fullPage: true });
      console.log(`captured: theme-overview.png  (tab=${on}, cards=${n}; presentation = overview)`);
    } else {
      await page.screenshot({ path: path.join(outDir, `theme-overview-${m}.png`), fullPage: true });
      console.log(`captured: theme-overview-${m}.png  (tab=${on}, cards=${n})`);
    }
  }

  await browser.close();
  console.log(`done: 3 张主题参考图已刷新（deviceScaleFactor=${SCALE}）`);
  /* 包体瘦身：256 色调色板量化（UI 截图无可见损失，单张约 1MB → ~350KB）；无 Python/Pillow 时保留原图 */
  try {
    require('child_process').execFileSync('python3', ['-c',
      "import sys;from PIL import Image\n" +
      "for f in sys.argv[1:]:\n" +
      "  Image.open(f).convert('RGB').quantize(colors=256,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).save(f,optimize=True)",
      ...['theme-overview.png', 'theme-overview-research.png', 'theme-overview-architecture.png'].map(f => path.join(outDir, f))],
      { stdio: 'inherit' });
    console.log('quantized: 256 色调色板');
  } catch (e) { console.warn('[capture] 量化跳过（需 python3 + Pillow）：' + (e && e.message)); }
})().catch((e) => { console.error(e); process.exit(1); });
