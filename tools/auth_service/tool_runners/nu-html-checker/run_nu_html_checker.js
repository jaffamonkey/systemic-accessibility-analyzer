const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const { safeSlug, ensureJob, preparePage } = require("../common/job_utils.cjs");

function writeJson(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf8");
}

function resolveVnuJar() {
  try {
    const resolved = require("vnu-jar");
    if (typeof resolved === "string") return resolved;
    if (resolved && typeof resolved.path === "string") return resolved.path;
    if (resolved && typeof resolved.jarPath === "string") return resolved.jarPath;
  } catch (_) {}

  const candidates = [
    "vnu-jar/build/dist/vnu.jar",
    "vnu-jar/build/dist/vnu.jar",
    "vnu-jar/vnu.jar"
  ];

  for (const candidate of candidates) {
    try {
      return require.resolve(candidate);
    } catch (_) {}
  }

  throw new Error("Could not resolve vnu.jar. Try: npm install --save-dev vnu-jar");
}

async function fetchHtml(url, storageStatePath) {
  const browser = await chromium.launch({ headless: true });
  const contextOptions = { ignoreHTTPSErrors: true };

  if (storageStatePath && fs.existsSync(storageStatePath)) {
    contextOptions.storageState = storageStatePath;
  }

  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();

  try {
    await preparePage(page, url);
    return await page.content();
  } finally {
    await page.close();
    await context.close();
    await browser.close();
  }
}

async function runNuForUrl(url, reportsDir, storageStatePath, jarPath) {
  const outPath = path.join(reportsDir, `${safeSlug(url)}.json`);

  try {
    const html = await fetchHtml(url, storageStatePath);
    const tmpFile = path.join(os.tmpdir(), `${safeSlug(url)}-${Date.now()}.html`);
    fs.writeFileSync(tmpFile, html, "utf8");

    const result = spawnSync(
      "java",
      [
        "-jar",
        jarPath,
        "--format",
        "json",
        "--skip-non-html",
        tmpFile
      ],
      {
        encoding: "utf8",
        maxBuffer: 1024 * 1024 * 20
      }
    );

    try {
      fs.unlinkSync(tmpFile);
    } catch (_) {}

    let parsed = null;
    try {
      const jsonText = result.stdout && result.stdout.trim()
        ? result.stdout
        : result.stderr;

      parsed = JSON.parse(jsonText || "{}");
    } catch (_) {
      parsed = {
        stdout: result.stdout,
        stderr: result.stderr
      };
    }

    writeJson(outPath, {
      tool: "nu-html-checker",
      url,
      scanned_at: new Date().toISOString(),
      returncode: result.status,
      result: parsed,
      stderr: result.stderr || ""
    });
  } catch (err) {
    writeJson(outPath, {
      tool: "nu-html-checker",
      url,
      scanned_at: new Date().toISOString(),
      error: err && err.message ? err.message : String(err),
      stack: err && err.stack ? err.stack : null
    });
  }
}

async function main() {
  const jobDir = process.argv[2];
  if (!jobDir) throw new Error("Usage: node run_nu_html_checker.js <job_dir>");

  const { urls, storageStatePath, reportsDir } = ensureJob(jobDir, "nu-html-checker");
  const jarPath = resolveVnuJar();

  for (const url of urls) {
    console.log(`Nu Html Checker scanning ${url}`);
    await runNuForUrl(url, reportsDir, storageStatePath, jarPath);
  }
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
});
