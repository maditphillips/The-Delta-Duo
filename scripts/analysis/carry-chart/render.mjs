// Screenshot a built carry-chart HTML file to PNG.
//   node scripts/analysis/carry-chart/render.mjs <in.html> <out.png>
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch {
  ({ chromium } = require("playwright-core"));
}

const [src, out] = process.argv.slice(2);
const browser = await chromium.launch(
  process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {},
);
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 2 });
await page.goto("file://" + path.resolve(src));
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log("wrote", out);
