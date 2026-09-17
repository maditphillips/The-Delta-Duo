/* Render each board to a PNG at 2x.
 *
 * The boards pull Righteous and Inter from Google Fonts, which a headless run
 * cannot reach - without them the export silently falls back to DejaVu and
 * stops matching the page. Install the two faces once before exporting:
 *
 *   ./fetch-fonts.sh
 *
 * Interactive chrome (the table button) is hidden for the still.
 */
const fs = require('fs');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const JOBS = [
  ['chains-per-carry.html', 'first-downs-per-carry-rate.png'],
  ['neutral-script-shotgun.html', 'neutral-script-shotgun-rate.png']
];

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  for (const [src, out] of JOBS) {
    const body = fs.readFileSync(src, 'utf8');
    const html = `<!doctype html><html><head><meta charset="utf-8">` +
      `<meta name="viewport" content="width=device-width,initial-scale=1">` +
      `<style>:root{color-scheme:light}body{margin:0;font:14px system-ui;background:#0c0e0d}` +
      `img{max-width:100%}[hidden]{display:none!important}.tools{display:none!important}</style>` +
      `</head><body>${body}</body></html>`;
    const tmp = 'export-' + src;
    fs.writeFileSync(tmp, html);

    const page = await browser.newPage({ viewport: { width: 940, height: 1000 }, deviceScaleFactor: 2 });
    await page.goto('file://' + process.cwd() + '/' + tmp);
    await page.evaluate(() => document.fonts.ready);
    const missing = await page.evaluate(() =>
      ['Righteous', 'Inter'].filter(f => !document.fonts.check(`16px "${f}"`)));
    if (missing.length) console.warn('  missing font, export will not match the page:', missing.join(', '));
    await page.waitForTimeout(400);

    const board = page.locator('main.board');
    await board.screenshot({ path: out });
    const { width, height } = await board.boundingBox();
    console.log(out, Math.round(width * 2) + 'x' + Math.round(height * 2), '(2x)');
    await page.close();
  }
  await browser.close();
})();
