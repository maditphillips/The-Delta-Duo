const fs = require('fs');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const jobs = [
    ['chains-per-carry.html', 'first-downs-per-carry-rate.png'],
    ['neutral-script-shotgun.html', 'neutral-script-shotgun-rate.png']
  ];
  for (const [src, out] of jobs) {
    const body = fs.readFileSync(src, 'utf8');
    const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui;background:#0c0e0d}img{max-width:100%}[hidden]{display:none!important}</style></head><body>${body}</body></html>`;
    const tmp = 'export-' + src;
    fs.writeFileSync(tmp, html);
    // 2x for a crisp export; the board itself is the frame, so shoot that element
    const page = await browser.newPage({ viewport: { width: 940, height: 1000 }, deviceScaleFactor: 2 });
    await page.goto('file://' + process.cwd() + '/' + tmp);
    await page.waitForFunction(() => document.fonts.ready.then(() => true));
    await page.waitForTimeout(800);
    await page.locator('main.board').screenshot({ path: out });
    const { width, height } = await page.locator('main.board').boundingBox();
    console.log(out, Math.round(width) + 'x' + Math.round(height), '@2x');
    await page.close();
  }
  await browser.close();
})();
