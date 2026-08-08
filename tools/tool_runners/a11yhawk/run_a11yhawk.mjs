import fs from 'node:fs';
import path from 'node:path';
import { renderHtmlReport, scan, ScanError } from 'a11yhawk';

function safeSlug(input) {
  return String(input || '')
    .replace(/^https?:\/\//i, '')
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

function ensureJob(jobDir, toolDir) {
  const urlsPath = path.join(jobDir, 'input', 'urls.txt');
  const storageStatePath = path.join(jobDir, 'auth', 'storage_state.json');
  const reportsDir = path.join(jobDir, 'reports', toolDir);

  fs.mkdirSync(reportsDir, { recursive: true });

  if (!fs.existsSync(urlsPath)) {
    throw new Error(`urls.txt not found: ${urlsPath}`);
  }

  const urls = fs
    .readFileSync(urlsPath, 'utf-8')
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);

  return { urls, storageStatePath, reportsDir };
}

async function runOneUrl(url, reportsDir) {
  const base = safeSlug(url);
  const jsonPath = path.join(reportsDir, `${base}.json`);

  console.log(`a11yhawk scanning ${url} (deterministic/no API key)...`);

  try {
    const report = await scan(url, {
      wcagVersion: '2.2',
      wcagLevel: 'AAA',
      annotatedScreenshot: true,
      onProgress: (e) => console.log(`  [${base}] [${e.stage}] ${e.message}`),
    });

    // 1. Primary JSON report payload for systemic analyzer ingestion
    const payload = {
      tool: 'a11yhawk',
      url,
      scanned_at: new Date().toISOString(),
      result: report.structured,
      durationMs: report.durationMs,
      finalUrl: report.finalUrl,
    };

    fs.writeFileSync(jsonPath, JSON.stringify(payload, null, 2), 'utf8');

    // 2. Optional auxiliary reports (HTML, Markdown, Screenshots)
    try {
      if (report.markdown) {
        fs.writeFileSync(path.join(reportsDir, `${base}.md`), report.markdown, 'utf8');
      }
      if (typeof renderHtmlReport === 'function' && report.structured) {
        fs.writeFileSync(path.join(reportsDir, `${base}.html`), renderHtmlReport(report), 'utf8');
      }
      if (report.screenshot) {
        fs.writeFileSync(path.join(reportsDir, `${base}.jpg`), report.screenshot);
      }
      if (report.screenshot) {
        fs.writeFileSync(path.join(reportsDir, `${base}-annotated.jpg`), report.annotatedScreenshot);
      }
    } catch (artifactErr) {
      console.warn(`[${base}] Warning: Failed to save extra report artifacts:`, artifactErr.message);
    }

    console.log(
      `[${base}] Completed | Score: ${report.structured?.overallScore}/100 | Issues: ${report.structured?.issues?.length || 0}`
    );

    return null;
  } catch (error) {
    const errorMessage =
      error instanceof ScanError
        ? `Scan failed [${error.code}] retryable=${error.retryable}: ${error.message}`
        : error instanceof Error
        ? error.message
        : String(error);

    console.error(`Failed a11yhawk audit for ${url}: ${errorMessage}`);

    // Standardized error JSON payload for the adapter pipeline
    fs.writeFileSync(
      jsonPath,
      JSON.stringify(
        {
          analyzer_error: true,
          tool: 'a11yhawk',
          url,
          error: errorMessage,
          scanned_at: new Date().toISOString(),
        },
        null,
        2
      ),
      'utf8'
    );

    return {
      url,
      message: errorMessage,
    };
  }
}

async function main() {
  const jobDir = process.argv[2];
  if (!jobDir) {
    throw new Error('Usage: node run_a11yhawk.mjs <job_dir>');
  }

  const { urls, reportsDir } = ensureJob(jobDir, 'a11yhawk');

  console.log(`a11yhawk starting batch scan for ${urls.length} URL(s)...`);

  const failures = [];
  const CONCURRENCY = 1;

  for (let i = 0; i < urls.length; i += CONCURRENCY) {
    const chunk = urls.slice(i, i + CONCURRENCY);
    const results = await Promise.all(
      chunk.map((url) => runOneUrl(url, reportsDir))
    );

    results.forEach((failure) => {
      if (failure) failures.push(failure);
    });
  }

  if (failures.length) {
    console.log(
      `a11yhawk completed with ${failures.length} failed URL(s). See error JSON files for details.`
    );
  } else {
    console.log('a11yhawk batch scan completed successfully.');
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});