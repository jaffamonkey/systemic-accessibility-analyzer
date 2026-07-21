import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';

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
  const visualPreviewDir = path.join(jobDir, 'reports', 'visual-preview');

  fs.mkdirSync(reportsDir, { recursive: true });
  fs.mkdirSync(visualPreviewDir, { recursive: true });

  if (!fs.existsSync(urlsPath)) {
    throw new Error(`urls.txt not found: ${urlsPath}`);
  }

  const urls = fs
    .readFileSync(urlsPath, 'utf-8')
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);

  return { urls, storageStatePath, reportsDir, visualPreviewDir };
}

async function clickLocator(locator, label) {
  try {
    const first = locator.first();
    if (await first.isVisible({ timeout: 500 })) {
      await first.click({ timeout: 2000 });
      await first.page?.().waitForTimeout?.(500);
      return { clicked: true, label };
    }
  } catch {}

  return { clicked: false, label };
}

async function dismissCookieBannerInFrame(frame) {
  const selectors = [
    '#onetrust-accept-btn-handler',
    '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
    '#didomi-notice-agree-button',
    '#truste-consent-button',
    '#acceptCookies',
    '#accept-cookies',
    '#cookie-accept',
    '.cookie-accept',
    '.accept-cookies',
    'button[aria-label="Accept cookies"]',
    'button[aria-label="Accept all"]',
    'input[type="submit"][value="Sounds good!"]',
    'input[type="submit"][value*="Accept" i]',
    'input[type="submit"][value*="Agree" i]',
    'input[type="submit"][value*="OK" i]',
    'input[type="submit"][value*="Got it" i]',
    'input[type="submit"][value*="Sounds good" i]',
  ];

  for (const selector of selectors) {
    try {
      const control = frame.locator(selector).first();
      if (await control.isVisible({ timeout: 500 })) {
        await control.click({ timeout: 2000 });
        return { action: 'clicked', detail: selector };
      }
    } catch {}
  }

  const texts = [
    'Accept',
    'Accept All',
    'Accept all',
    'Accept cookies',
    'Allow all',
    'I agree',
    'Agree',
    'OK',
    'Got it',
    'Continue',
    'Sounds good!',
    'Confirm choices',
  ];

  for (const text of texts) {
    try {
      const button = frame.getByRole('button', {
        name: new RegExp(`^${text}$`, 'i'),
      }).first();

      if (await button.isVisible({ timeout: 500 })) {
        await button.click({ timeout: 2000 });
        return { action: 'clicked', detail: text };
      }
    } catch {}
  }

  return { action: 'none', detail: '' };
}

async function dismissCookieBanner(page) {
  // Try main page and any same-origin/accessible frames.
  for (const frame of page.frames()) {
    const result = await dismissCookieBannerInFrame(frame).catch(() => ({ action: 'none', detail: '' }));
    if (result.action !== 'none') {
      await page.waitForTimeout(700);
      console.log(`Accepted/dismissed cookies using ${result.detail}`);
      return result;
    }
  }

  // Last-resort overlay removal. Keep best-effort only.
  const removed = await page.evaluate(() => {
    const keywordRe = /(cookie|consent|gdpr|privacy|cmp|onetrust|trustarc|didomi|cookiebot|qc-cmp|sp_message_container)/i;
    let removedCount = 0;

    const elements = Array.from(document.querySelectorAll('body *'));
    for (const el of elements) {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      const text = (el.textContent || '').slice(0, 500);
      const idClass = `${el.id || ''} ${(el.className || '').toString()}`;
      const attrs = `${el.getAttribute('aria-label') || ''} ${el.getAttribute('role') || ''}`;

      const keywordMatch = keywordRe.test(idClass) || keywordRe.test(text) || keywordRe.test(attrs);
      const overlayish = style.position === 'fixed' || style.position === 'sticky';
      const highZ =
        style.zIndex === '2147483647' ||
        (!Number.isNaN(Number(style.zIndex)) && Number(style.zIndex) >= 999);
      const largeEnough =
        rect.width >= window.innerWidth * 0.3 ||
        rect.height >= window.innerHeight * 0.15;

      if (keywordMatch && (overlayish || highZ) && largeEnough) {
        el.remove();
        removedCount += 1;
      }
    }

    document.documentElement.style.overflow = '';
    document.body.style.overflow = '';

    return removedCount;
  }).catch(() => 0);

  if (removed > 0) {
    await page.waitForTimeout(700);
    return { action: 'removed', detail: `${removed} overlay(s)` };
  }

  return { action: 'none', detail: '' };
}

async function waitForPageToSettle(page) {
  await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});

  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) {
      await document.fonts.ready.catch(() => {});
    }
  }).catch(() => {});

  const selectors = [
    '[aria-busy="true"]',
    '.loading',
    '.spinner',
    '.loader',
    '[data-loading="true"]',
  ];

  for (const selector of selectors) {
    await page.locator(selector).first().waitFor({
      state: 'hidden',
      timeout: 3000,
    }).catch(() => {});
  }

  await page.waitForTimeout(1500);
}

function escapeXml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

function buildOverlaySvg(width, height, focusable) {
  const parts = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`
  ];

  for (let i = 0; i < focusable.length; i++) {
    const item = focusable[i];
    const { left, top, width: w, height: h } = item.rect;

    const x = Math.max(0, left);
    const y = Math.max(0, top);
    const boxWidth = Math.max(1, w);
    const boxHeight = Math.max(1, h);

    const badgeX = x;
    const badgeY = y;

    parts.push(
      `<rect x="${x}" y="${y}" width="${boxWidth}" height="${boxHeight}" fill="none" stroke="#2563eb" stroke-width="2" />`
    );

    parts.push(
      `<circle cx="${badgeX}" cy="${badgeY}" r="10" fill="#2563eb" />`
    );

    parts.push(
      `<text x="${badgeX}" y="${badgeY}" text-anchor="middle" dominant-baseline="central" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#ffffff">${escapeXml(i + 1)}</text>`
    );

    if (i < focusable.length - 1) {
      const next = focusable[i + 1].rect;
      const x1 = x + boxWidth / 2;
      const y1 = y + boxHeight / 2;
      const x2 = next.left + next.width / 2;
      const y2 = next.top + next.height / 2;

      parts.push(
        `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#2563eb" stroke-width="2" stroke-dasharray="5,5" />`
      );
    }
  }

  parts.push(`</svg>`);
  return parts.join('');
}

async function collectTabMapData(page) {
  return await page.evaluate(() => {
    const selector =
      'a[href], button, input, select, textarea, [tabindex], [contenteditable="true"]';

    function isFocusable(el, doc) {
      const rawTabIndex = el.getAttribute('tabindex');
      const tabIndex = rawTabIndex === null ? 0 : parseInt(rawTabIndex || '0', 10);

      const style = doc.defaultView.getComputedStyle(el);
      const rect = el.getBoundingClientRect();

      const isVisible =
        rect.width > 0 &&
        rect.height > 0 &&
        style.visibility !== 'hidden' &&
        style.display !== 'none';

      return tabIndex >= 0 && isVisible && !el.hasAttribute('disabled');
    }

    function collectFocusableFromDocument(doc, offsetX = 0, offsetY = 0, source = 'document') {
      return Array.from(doc.querySelectorAll(selector))
        .filter((el) => isFocusable(el, doc))
        .map((el) => {
          const rect = el.getBoundingClientRect();
          const rawTabIndex = el.getAttribute('tabindex');
          const tabIndex = rawTabIndex === null ? 0 : parseInt(rawTabIndex || '0', 10);

          return {
            tabIndex,
            rect: {
              left: rect.left + offsetX,
              top: rect.top + offsetY,
              width: rect.width,
              height: rect.height,
            },
            source,
          };
        });
    }

    const frameInfo = {
      frameCount: 0,
      sameOriginFrameCount: 0,
      crossOriginFrameCount: 0,
    };

    let focusable = collectFocusableFromDocument(
      document,
      window.scrollX,
      window.scrollY,
      'document'
    );

    const frameElements = Array.from(document.querySelectorAll('frame, iframe'));
    frameInfo.frameCount = frameElements.length;

    for (const frameEl of frameElements) {
      try {
        const frameDoc = frameEl.contentDocument;
        const frameWin = frameEl.contentWindow;

        if (!frameDoc || !frameWin) {
          frameInfo.crossOriginFrameCount += 1;
          continue;
        }

        const frameRect = frameEl.getBoundingClientRect();
        frameInfo.sameOriginFrameCount += 1;

        const frameItems = Array.from(frameDoc.querySelectorAll(selector))
          .filter((el) => isFocusable(el, frameDoc))
          .map((el) => {
            const rect = el.getBoundingClientRect();
            const rawTabIndex = el.getAttribute('tabindex');
            const tabIndex = rawTabIndex === null ? 0 : parseInt(rawTabIndex || '0', 10);

            return {
              tabIndex,
              rect: {
                left: rect.left + frameRect.left + window.scrollX,
                top: rect.top + frameRect.top + window.scrollY,
                width: rect.width,
                height: rect.height,
              },
              source: 'frame',
            };
          });

        focusable = focusable.concat(frameItems);
      } catch {
        frameInfo.crossOriginFrameCount += 1;
      }
    }

    focusable = focusable.sort((a, b) => {
      if (a.tabIndex > 0 && b.tabIndex > 0) return a.tabIndex - b.tabIndex;
      if (a.tabIndex > 0) return -1;
      if (b.tabIndex > 0) return 1;
      return 0;
    });

    return {
      title: document.title || '',
      focusable,
      focusableCount: focusable.length,
      frameCount: frameInfo.frameCount,
      sameOriginFrameCount: frameInfo.sameOriginFrameCount,
      crossOriginFrameCount: frameInfo.crossOriginFrameCount,
      pageWidth: Math.max(
        document.documentElement.scrollWidth,
        document.body ? document.body.scrollWidth : 0,
        window.innerWidth
      ),
      pageHeight: Math.max(
        document.documentElement.scrollHeight,
        document.body ? document.body.scrollHeight : 0,
        window.innerHeight
      ),
    };
  });
}

async function main() {
  const jobDir = process.argv[2];
  if (!jobDir) {
    throw new Error('Usage: node run_tab_map.js <job_dir>');
  }

  const { urls, storageStatePath, reportsDir, visualPreviewDir } = ensureJob(jobDir, 'tab-map');
  const hasStorageState = storageStatePath && fs.existsSync(storageStatePath);

  const manifest = [];
  const browser = await chromium.launch({ headless: true });

  try {
    for (const url of urls) {
      const contextOptions = {
        ignoreHTTPSErrors: true,
        viewport: { width: 1440, height: 1200 },
      };

      if (hasStorageState) {
        contextOptions.storageState = storageStatePath;
      }

      const context = await browser.newContext(contextOptions);
      const page = await context.newPage();

      try {
        console.log(`Generating visual preview and tab map: ${url}`);

        await page.goto(url, {
          waitUntil: 'domcontentloaded',
          timeout: 180000,
        });

        console.log(`Landed on: ${page.url()}`);

        const consentActions = [];
        for (let i = 0; i < 3; i += 1) {
          const result = await dismissCookieBanner(page).catch(() => ({ action: 'none', detail: '' }));
          if (result.action !== 'none') {
            consentActions.push(result);
          }
          await page.waitForTimeout(700);
        }

        await waitForPageToSettle(page);

        const tabData = await collectTabMapData(page);

        const screenshotBuffer = await page.screenshot({
          fullPage: true,
          type: 'png',
        });

        const overlaySvg = buildOverlaySvg(
          tabData.pageWidth,
          tabData.pageHeight,
          tabData.focusable
        );

        const finalPngBuffer = await sharp(screenshotBuffer)
          .composite([
            {
              input: Buffer.from(overlaySvg),
              top: 0,
              left: 0,
            },
          ])
          .png()
          .toBuffer();

        const base = safeSlug(url);
        const capturedAt = new Date().toISOString();
        const previewPath = path.join(visualPreviewDir, `${base}.png`);
        const pngPath = path.join(reportsDir, `${base}.png`);
        const jsonPath = path.join(reportsDir, `${base}.json`);

        fs.writeFileSync(previewPath, screenshotBuffer);
        fs.writeFileSync(pngPath, finalPngBuffer);

        const payload = {
          tool: 'tab-map',
          url,
          landed_url: page.url(),
          title: tabData.title,
          page: base,
          captured_at: capturedAt,
          focusable_count: tabData.focusableCount,
          frame_count: tabData.frameCount ?? 0,
          same_origin_frame_count: tabData.sameOriginFrameCount ?? 0,
          cross_origin_frame_count: tabData.crossOriginFrameCount ?? 0,
          image: path.basename(pngPath),
          preview_image: path.basename(previewPath),
          preview_dir: 'visual-preview',
          json: path.basename(jsonPath),
          consent_actions: consentActions,
        };

        fs.writeFileSync(jsonPath, JSON.stringify(payload, null, 2), 'utf8');
        manifest.push(payload);

        console.log(`Saved visual preview: ${previewPath}`);
        console.log(`Saved tab map: ${pngPath}`);
      } catch (error) {
        const base = safeSlug(url);
        const capturedAt = new Date().toISOString();
        const errorPath = path.join(reportsDir, `${base}-error.json`);

        const errorPayload = {
          tool: 'tab-map',
          url,
          page: base,
          captured_at: capturedAt,
          error: error instanceof Error ? error.message : String(error),
          error_type: error instanceof Error ? error.name : 'Error',
        };

        fs.writeFileSync(errorPath, JSON.stringify(errorPayload, null, 2), 'utf8');
        manifest.push(errorPayload);

        console.error(`Failed visual/tab map for ${url}: ${error.message || String(error)}`);
      } finally {
        await page.close().catch(() => {});
        await context.close().catch(() => {});
      }
    }

    const manifestPath = path.join(reportsDir, 'manifest.json');
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf8');
    console.log(`Saved tab map manifest: ${manifestPath}`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
