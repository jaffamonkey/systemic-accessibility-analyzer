const fs = require('fs');
const path = require('path');

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

async function clickIfVisible(locator, timeout = 750) {
  try {
    const first = locator.first();
    if (await first.isVisible({ timeout })) {
      await first.click({ timeout: 2000 });
      return true;
    }
  } catch (_) {}

  return false;
}

async function dismissCookieBanner(page) {
  const selectors = [
    "#onetrust-accept-btn-handler",
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    "#didomi-notice-agree-button",
    "#truste-consent-button",
    "#acceptCookies",
    "#accept-cookies",
    "#cookie-accept",
    ".cookie-accept",
    ".accept-cookies",
    "button[aria-label='Accept cookies']",
    "button[aria-label='Close']",
    "button.agree-button"
  ];

  for (const selector of selectors) {
    try {
      const button = page.locator(selector).first();
      if (await button.isVisible({ timeout: 500 })) {
        await button.click({ timeout: 2000 });
        await page.waitForTimeout(500);
        return true;
      }
    } catch {}
  }

  const texts = ["Accept", "Accept All", "Accept all", "Allow all", "Consent", "I agree", "Agree", "OK", "Got it", "Continue", "I'm OK with analytics cookies"];

  for (const text of texts) {
    try {
      const button = page.getByRole("button", {
        name: new RegExp(`^${text}$`, "i")
      }).first();

      if (await button.isVisible({ timeout: 500 })) {
        await button.click({ timeout: 2000 });
        await page.waitForTimeout(500);
        return true;
      }
    } catch {}
  }

  return false;
}

async function dismissCookieBanner(page) {
  const selectors = [
    "#onetrust-accept-btn-handler",
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    "#didomi-notice-agree-button",
    "#truste-consent-button",

    "#acceptCookies",
    "#accept-cookies",
    "#cookie-accept",
    ".cookie-accept",
    ".accept-cookies",
    ".eu-cookie-compliance-secondary-button",

    "button[aria-label='Accept cookies']",
    "button[aria-label='Accept all']",

    'input[type="submit"][value="Sounds good!"]',
    'input[type="submit"][value*="Accept" i]',
    'input[type="submit"][value*="Agree" i]',
    'input[type="submit"][value*="OK" i]',
    'input[type="submit"][value*="Got it" i]',
    'input[type="submit"][value*="Sounds good" i]',
    'button.agree-button'
  ];

  for (const selector of selectors) {
    try {
      const button = page.locator(selector).first();
      if (await button.isVisible({ timeout: 500 })) {
        await button.click({ timeout: 2000 });
        await page.waitForTimeout(500);
        return true;
      }
    } catch {}
  }

  const texts = ["Accept", "Accept All", "Accept all", "Allow all", "I agree", "Agree", "OK", "Got it", "Continue", "Sounds good!"];

  for (const text of texts) {
    try {
      const button = page.getByRole("button", {
        name: new RegExp(`^${text}$`, "i")
      }).first();

      if (await button.isVisible({ timeout: 500 })) {
        await button.click({ timeout: 2000 });
        await page.waitForTimeout(500);
        return true;
      }
    } catch {}
  }

  return false;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function preparePage(page, url) {
  await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: 120000
  });

  try {
    await dismissCookieBanner(page);
  } catch (err) {
    console.warn(`Cookie banner dismissal skipped: ${err.message || err}`);
  }

  try {
    await page.waitForLoadState("networkidle", { timeout: 10000 });
  } catch {
    // Some pages never become network idle. That's fine.
  }

  await page.waitForTimeout(1000);
}

module.exports = {
  safeSlug,
  ensureJob,
  dismissCookieBanner,
  preparePage,
};