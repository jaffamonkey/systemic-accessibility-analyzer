const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

function safeSlug(input) {
  return String(input || "")
    .replace(/^https?:\/\//i, "")
    .replace(/#/, "-")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();
}

function readUrls(filePath) {
  return fs
    .readFileSync(filePath, "utf8")
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf8");
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function appendLog(filePath, text) {
  fs.appendFileSync(filePath, text, "utf8");
}

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function getTopLevelMeta(reportJson, fallbackUrl) {
  if (Array.isArray(reportJson) && reportJson[0]) {
    return {
      url: reportJson[0].url || fallbackUrl,
      title: reportJson[0].title || fallbackUrl,
    };
  }

  return {
    url: reportJson?.url || fallbackUrl,
    title: reportJson?.title || fallbackUrl,
  };
}

function resolveContrastBinary() {
  const localBin = path.resolve(__dirname, "node_modules/.bin/contrastcheck");
  if (fs.existsSync(localBin)) return localBin;
  return "contrastcheck";
}

function buildToolCommand({ url, outputPath }) {
  return {
    command: resolveContrastBinary(),
    args: [
      url,
      "--json",
      "--output",
      outputPath,
    ],
  };
}

function runCommand(command, args, cwd) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: "utf8",
    shell: false,
  });

  return {
    status: result.status,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
    error: result.error || null,
  };
}

function tryParseJsonString(text) {
  const raw = String(text || "").trim();
  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch {
    const firstBracket = raw.indexOf("[");
    const firstBrace = raw.indexOf("{");

    let start = -1;
    if (firstBracket >= 0 && firstBrace >= 0) {
      start = Math.min(firstBracket, firstBrace);
    } else if (firstBracket >= 0) {
      start = firstBracket;
    } else if (firstBrace >= 0) {
      start = firstBrace;
    }

    if (start >= 0) {
      const sliced = raw.slice(start);
      try {
        return JSON.parse(sliced);
      } catch {
        return null;
      }
    }

    return null;
  }
}

async function main() {
  const jobDir = process.argv[2];
  if (!jobDir) {
    throw new Error('Usage: node run_contrast_checker.js <job_dir>');
  }

  const inputDir = path.join(jobDir, 'input');
  const urlsFile = path.join(inputDir, 'urls.txt');
  const reportsDir = path.join(jobDir, 'reports', 'contrast-checker');
  const manifestPath = path.join(reportsDir, 'manifest.json');

  if (!fs.existsSync(urlsFile)) {
    throw new Error(`urls.txt not found: ${urlsFile}`);
  }

  ensureDir(reportsDir);

  const urls = readUrls(urlsFile);
  const manifest = [];

  for (const url of urls) {
    const slug = safeSlug(url);
    const jsonPath = path.join(reportsDir, `${slug}.json`);
    const logPath = path.join(reportsDir, `${slug}-runlog.txt`);

    console.log(`Checking contrast for: ${url}`);

    // Clear old log if it exists and start a new one
    fs.writeFileSync(logPath, `Starting contrast check for ${url}\n`, "utf8");

    const { command, args } = buildToolCommand({ url, outputPath: jsonPath });

    try {
      // Execute the local binary synchronously
      const result = runCommand(command, args, process.cwd());

      appendLog(logPath, `\n--- STDOUT ---\n${result.stdout}\n`);

      if (result.stderr) {
        appendLog(logPath, `\n--- STDERR ---\n${result.stderr}\n`);
      }

      const parsedJson = tryParseJsonString(result.stdout);

      if (parsedJson) {
        writeJson(jsonPath, parsedJson);

        // FIX 1: Extract the metadata using your helper function
        const meta = getTopLevelMeta(parsedJson, url);

        manifest.push({
          page: slug,
          url: meta.url,
          title: meta.title,
          // FIX 2: Provide both keys so the UI guarantees a match
          json: `${slug}.json`,
          report: `${slug}.json`,
          ok: true
        });
        console.log(`  Saved: ${slug}.json`);
      } else {
        throw new Error(`Failed to extract valid JSON from contrast tool stdout. Exit status: ${result.status}`);
      }
    } catch (error) {
      console.error(`  Failed: ${error.message}`);
      appendLog(logPath, `\n--- ERROR ---\n${error.message}\n`);

      writeJson(jsonPath, {
        analyzer_error: true,
        tool: "contrast-checker",
        url,
        error: error.message
      });

      manifest.push({
        page: slug,
        url,
        title: slug,
        json: `${slug}.json`,
        report: `${slug}.json`,
        ok: false,
        error: error.message
      });
    }

    // Incrementally save the manifest!
    writeJson(manifestPath, manifest);

    // Optional: Add a tiny sleep to let the OS breathe between heavy binary executions
    sleep(1000);
  }

  console.log(`Done. Saved manifest to ${manifestPath}`);
}

// THIS is the line that was missing! It actually runs the script.
main().catch((err) => {
  console.error(err);
  process.exit(1);
});