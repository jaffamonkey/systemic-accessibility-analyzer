import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { check, buildSarifReport } from "@speca11y/core";


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

const allReports = [];

async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise(resolve => {
      let total = 0;
      const distance = 500;
      const timer = setInterval(() => {
        window.scrollBy(0, distance);
        total += distance;

        if (total >= document.body.scrollHeight) {
          clearInterval(timer);
          window.scrollTo(0, 0);
          resolve();
        }
      }, 100);
    });
  });
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

function safeName(input) {
  return String(input || "")
    .replace(/^https?:\/\//i, "")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

for (const url of urls) {
  const page = await browser.newPage({
    viewport: { width: 1366, height: 900 },
    reducedMotion: "reduce"
  });

  console.log(`Checking: ${url}`);

  try {
    await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: 120000
    });

    await page.waitForTimeout(2000);

    // Helps expose lazy-loaded content before the accessibility run.
    await autoScroll(page);

    const report = await withTimeout(
      check(page, {
        level: "AAA",
        includePasses: false,
        ruleTimeout: 10000,
        versions: ["2.0", "2.1", "2.2"]
      }),
      90000,
      `SpecA11y check for ${url}`
    );

    const name = safeName(url);
    const jsonPath = path.join(OUT_DIR, `${name}.json`);
    const sarifPath = path.join(OUT_DIR, `${name}.sarif`);

    await fs.writeFile(jsonPath, JSON.stringify(report, null, 2));
    await fs.writeFile(
      sarifPath,
      JSON.stringify(buildSarifReport(report), null, 2)
    );

    allReports.push({
      url,
      ok: true,
      violations: report.summary?.counts?.violations ?? 0,
      warnings: report.summary?.counts?.warnings ?? 0,
      json: jsonPath,
      sarif: sarifPath
    });

    console.log(
      `  Violations: ${report.summary?.counts?.violations ?? 0}, warnings: ${report.summary?.counts?.warnings ?? 0}`
    );
  } catch (error) {
    allReports.push({
      url,
      ok: false,
      error: error.message
    });

    console.error(`  Failed: ${error.message}`);
  } finally {
    await page.close();
  }
}

await browser.close();

await fs.writeFile(
  path.join(OUT_DIR, "summary.json"),
  JSON.stringify(allReports, null, 2)
);

console.log(`Done. Reports written to ${OUT_DIR}`);