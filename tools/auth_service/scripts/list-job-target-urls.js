// scripts/list-job-target-urls.js
import fs from "node:fs/promises";
import path from "node:path";

const jobsDir = process.argv[2] || "jobs";
const outFile = process.argv[3] || "target-urls.txt";

async function exists(file) {
  try {
    await fs.access(file);
    return true;
  } catch {
    return false;
  }
}

const jobNames = await fs.readdir(jobsDir);
let output = "";

for (const jobName of jobNames.sort()) {
  const jobPath = path.join(jobsDir, jobName);

  if (!(await fs.stat(jobPath)).isDirectory()) continue;

  const configFile = path.join(jobPath, "incoming_job_config.json");

  if (!(await exists(configFile))) continue;

  try {
    const config = JSON.parse(await fs.readFile(configFile, "utf8"));
    const urls = [...new Set(config.target_urls || [])];

    output += `${jobName}\n`;
    output += `${"-".repeat(jobName.length)}\n`;

    if (urls.length === 0) {
      output += "(No target_urls found)\n";
    } else {
      output += urls.join("\n");
      output += "\n";
    }

    output += "\n";
  } catch (err) {
    console.error(`Error reading ${configFile}: ${err.message}`);
  }
}

await fs.writeFile(outFile, output);

console.log(`✓ Wrote ${outFile}`);