#!/usr/bin/env node
/**
 * The website's product screenshots (site/public/screens/<name>-<locale>-<theme>.webp), captured
 * from the running app: 1440 × 900 at 2× in French and English, light and dark, then written as
 * 2000 px WebP. The invoice workflow runs one real extraction per language first, so its fields,
 * rules and publish step show real values.
 *
 *   E2E_WEB_URL=http://localhost:3100 node scripts/capture-site-screens.mjs
 *
 * Needs the app (sign-in off) with the demo data, and Python with Pillow (the backend's venv).
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { chromium } from "@playwright/test";

const WEB = process.env.E2E_WEB_URL ?? "http://localhost:3100";
const ROOT = path.resolve(import.meta.dirname, "..");
const OUT = path.join(ROOT, "site", "public", "screens");
const SAMPLE = path.join(
  ROOT,
  "e2e",
  "fixtures",
  "documents",
  "Facture RETOUCHE remplie AVEC TVA.png"
);
const REPORT = process.env.REPORT_RUN ?? "run-01a1d593bab7772bb61bb237aac64f03";
const RAW = mkdtempSync(path.join(tmpdir(), "repody-screens-"));

const settle = (page, ms = 1200) =>
  page.waitForLoadState("networkidle").then(() => page.waitForTimeout(ms));

async function shot(page, name, locale, theme) {
  await page.mouse.move(0, 0); // no hover state
  const file = path.join(RAW, `${name}-${locale}-${theme}.png`);
  writeFileSync(file, await page.screenshot());
  console.log("  ", path.basename(file));
}

async function capture(browser, locale, theme) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: theme,
    locale: locale === "fr" ? "fr-FR" : "en-US",
  });
  const { hostname } = new URL(WEB);
  await context.addCookies([
    { name: "wb_locale", value: locale, domain: hostname, path: "/" },
    { name: "wb_tz", value: "Africa/Casablanca", domain: hostname, path: "/" },
  ]);
  await context.addInitScript((value) => localStorage.setItem("theme", value), theme);
  const page = await context.newPage();
  const go = async (route) => {
    await page.goto(`${WEB}${route}`);
    await page.addStyleTag({ content: "nextjs-portal{display:none!important}" });
    // The local app runs without sign-in: keep its "dev" account row out of the picture.
    await page.getByRole("button", { name: /no sign-in|sans connexion/ }).evaluate((row) => {
      row.style.visibility = "hidden";
    });
    await settle(page);
  };

  await go("/dashboard");
  await shot(page, "overview", locale, theme);
  await go("/audits");
  await shot(page, "runs", locale, theme);
  await go(`/audits/${REPORT}`);
  await shot(page, "report", locale, theme);
  await go("/settings");
  await shot(page, "settings", locale, theme);
  await go("/workflows/wf-claim-auto/edit");
  await page.getByRole("tab", { name: /2/ }).first().click();
  await settle(page);
  await shot(page, "builder-claim", locale, theme);

  // The invoice workflow on a real sample: extract, then each step.
  await go("/workflows/wf-invoice-audit/edit");
  await page.locator('input[type="file"]').first().setInputFiles(SAMPLE);
  await page.keyboard.press("Control+Enter");
  await page
    .getByText(/\d+ (sur|of) \d+/)
    .first()
    .waitFor({ timeout: 300_000 });
  await settle(page, 2500);
  await shot(page, "builder-documents", locale, theme);
  await page.getByRole("tab", { name: /2/ }).first().click();
  await settle(page);
  await shot(page, "builder-rules", locale, theme);
  await page.getByRole("tab", { name: /3/ }).first().click();
  await settle(page);
  await shot(page, "builder-publish", locale, theme);
  await context.close();
}

const browser = await chromium.launch();
for (const locale of ["fr", "en"]) {
  for (const theme of ["light", "dark"]) {
    console.log(locale, theme);
    await capture(browser, locale, theme);
  }
}
await browser.close();

mkdirSync(OUT, { recursive: true });
execFileSync(
  "uv",
  [
    "run",
    "--directory",
    path.join(ROOT, "backend"),
    "python",
    "-c",
    `import pathlib,sys
from PIL import Image
raw, out = map(pathlib.Path, sys.argv[1:3])
for png in sorted(raw.glob("*.png")):
    image = Image.open(png).convert("RGB")
    image = image.resize((2000, round(image.height * 2000 / image.width)), Image.Resampling.LANCZOS)
    image.save(out / (png.stem + ".webp"), "WEBP", quality=82, method=6)
    print("  ", png.stem + ".webp")`,
    RAW,
    OUT,
  ],
  { stdio: "inherit" }
);
