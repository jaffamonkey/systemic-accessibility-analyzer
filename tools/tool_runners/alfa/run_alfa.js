import fs from "fs";
import path from "path";
import { chromium } from "playwright";
import { Audit } from "@siteimprove/alfa-test-utils";
import { Playwright } from "@siteimprove/alfa-playwright";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { safeSlug, ensureJob, preparePage } = require("../common/job_utils.cjs");

function writeJson(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf8");
}

function buildContextOptions(storageStatePath) {
  const options = { ignoreHTTPSErrors: true };
  if (storageStatePath && fs.existsSync(storageStatePath)) {
    options.storageState = storageStatePath;
  }
  return options;
}

function toPlain(value, depth = 0) {
  if (depth > 8) return String(value);
  if (value == null) return value;
  if (Array.isArray(value)) {
    return value.map((item) => toPlain(item, depth + 1));
  }
  if (typeof value !== "object") return value;
  if (typeof value.toJSON === "function") {
    try { return toPlain(value.toJSON(), depth + 1); } catch {}
  }
  if (typeof value.toString === "function" && value.constructor?.name !== "Object") {
    try {
      const text = value.toString();
      if (text && text !== "[object Object]") return text;
    } catch {}
  }

  const out = {};
  for (const key of Object.keys(value)) {
    try {
      out[key] = toPlain(value[key], depth + 1);
    } catch {
      out[key] = "[unserializable]";
    }
  }
  return out;
}

async function runAlfaForUrl(context, url, reportsDir) {
  const page = await context.newPage();
  const outPath = path.join(reportsDir, `${safeSlug(url)}.json`);

  // Declare heavy objects outside the try block so we can explicitly nullify them
  let documentHandle = null;
  let alfaPage = null;
  let alfaResult = null;

  try {
    await preparePage(page, url);

    documentHandle = await page.evaluateHandle(() => window.document);
    alfaPage = await Playwright.toPage(documentHandle);
    alfaResult = await Audit.run(alfaPage);

    writeJson(outPath, {
      tool: "alfa",
      url,
      scanned_at: new Date().toISOString(),
      result: toPlain(alfaResult)
    });
  } catch (err) {
    writeJson(outPath, {
      tool: "alfa",
      url,
      scanned_at: new Date().toISOString(),
      error: err?.message || String(err),
      stack: err?.stack || null
    });
  } finally {
    // Explicitly release large objects for aggressive garbage collection
    if (documentHandle) await documentHandle.dispose().catch(() => {});
    alfaPage = null;
    alfaResult = null;
    
    await page.close();
  }
}

async function main() {
  const jobDir = process.argv[2];
  if (!jobDir) throw new Error("Usage: node run_alfa.js <job_dir>");

  const { urls, storageStatePath, reportsDir } = ensureJob(jobDir, "alfa");

  const browser = await chromium.launch({ headless: true });

  try {
    for (const url of urls) {
      console.log(`Alfa scanning ${url}`);
      
      // FIX: Create and destroy the context per URL to flush memory caches completely
      const context = await browser.newContext(buildContextOptions(storageStatePath));
      
      try {
        await runAlfaForUrl(context, url, reportsDir);
      } finally {
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err?.stack || err);
  process.exit(1);
});