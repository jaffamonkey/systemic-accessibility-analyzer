import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { check } from "@speca11y/core";

const JOB_DIR = process.argv[2];

if (!JOB_DIR) {
  throw new Error("Usage: node run_speca11y.js <job_dir>");
}

const URLS_FILE = path.join(JOB_DIR, "input", "urls.txt");
const OUT_DIR = path.join(JOB_DIR, "reports", "speca11y");

const urls = (await fs.readFile(URLS_FILE, "utf8"))
  .split(/\r?\n/)
  .map(line => line.trim())
  .filter(line => line && !line.startsWith("#"));

await fs.mkdir(OUT_DIR, { recursive: true });

const browser = await chromium.launch({
  headless: true
});

function safeName(input) {
  return String(input || "")
    .replace(/^https?:\/\//i, "")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

async function withTimeout(promise, ms, label) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms);
  });

  try {
    return await Promise.race([promise, timeout]);
  } finally {
    clearTimeout(timer);
  }
}

async function autoScroll(page, maxScrolls = 15) {
  await page.evaluate(async (max) => {
    await new Promise(resolve => {
      let total = 0;
      let scrolls = 0;
      const distance = 500;
      const timer = setInterval(() => {
        window.scrollBy(0, distance);
        total += distance;
        scrolls++;

        if (total >= document.body.scrollHeight || scrolls >= max) {
          clearInterval(timer);
          window.scrollTo(0, 0);
          resolve();
        }
      }, 100);
    });
  }, maxScrolls);
}

async function processUrl(url) {
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    reducedMotion: "reduce"
  });

  const page = await context.newPage();
  const name = safeName(url);
  const jsonPath = path.join(OUT_DIR, `${name}.json`);

  console.log(`Checking: ${url}`);

  try {
    await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: 60000
    });

    await page.waitForTimeout(1000);
    await withTimeout(autoScroll(page), 10000, `autoScroll for ${url}`);

    const report = await withTimeout(
      check(page, {
        level: "AAA",
        includePasses: false,
        ruleTimeout: 10000,
        versions: ["2.0", "2.1", "2.2"]
      }),
      60000,
      `SpecA11y check for ${url}`
    );

    await fs.writeFile(jsonPath, JSON.stringify(report, null, 2));
    console.log(`  Saved: ${name}.json`);
  } catch (error) {
    console.error(`  Failed: ${url} - ${error.message}`);
    
    // Write fallback error JSON so analyzer tracks the failed run explicitly
    await fs.writeFile(
      jsonPath,
      JSON.stringify({ analyzer_error: true, message: error.message, url }, null, 2)
    );
  } finally {
    await page.close();
    await context.close();
  }
}

// Process 4 URLs concurrently in chunks
const CONCURRENCY = 4;
for (let i = 0; i < urls.length; i += CONCURRENCY) {
  const chunk = urls.slice(i, i + CONCURRENCY);
  await Promise.all(chunk.map(url => processUrl(url)));
}

await browser.close();
console.log(`Done. Reports written to ${OUT_DIR}`);