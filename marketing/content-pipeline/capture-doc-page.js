/**
 * Capture a set of design-doc-focused screenshots for the
 * /tools/design-doc-generator landing page.
 *
 * Output (in ./output/doc-page/):
 *   01-doc-panel-full.png        - The whole design doc panel, header to footer
 *   02-doc-executive-summary.png - Just the Executive Summary section
 *   03-doc-component-details.png - Just the Component Details section
 *   04-doc-data-flow.png         - Just the Data Flow section
 *   05-doc-trade-offs.png        - Just Trade-offs / Security / Scalability
 *   06-doc-toolbar.png           - Toolbar zoomed (proves it's editable)
 *   07-doc-export-dropdown.png   - Export dropdown opened
 *   08-doc-app-with-sync.png     - Full app showing sync indicator (reuses auto-sync flow)
 *   09-doc-second-example.png    - A different diagram + its doc, for variety
 *
 * Usage:
 *   cd marketing/content-pipeline
 *   node capture-doc-page.js
 */

import puppeteer from "puppeteer";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadEnv() {
  const candidates = [path.join(__dirname, ".env"), path.join(__dirname, "..", "..", ".env")];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      for (const line of fs.readFileSync(p, "utf-8").split("\n")) {
        const t = line.trim();
        if (!t || t.startsWith("#")) continue;
        const i = t.indexOf("=");
        if (i === -1) continue;
        const k = t.slice(0, i);
        const v = t.slice(i + 1);
        if (!process.env[k]) process.env[k] = v;
      }
    }
  }
}
loadEnv();

const CONFIG = {
  url: process.env.INFRASKETCH_URL || "https://infrasketch.net",
  clerkSecretKey: process.env.CLERK_SECRET_KEY,
  clerkUserId: process.env.CLERK_USER_ID,
  outputDir: path.join(__dirname, "output", "doc-page"),
  diagramTimeout: 90_000,
  chatResponseTimeout: 60_000,
  designDocTimeout: 180_000,
};

if (!fs.existsSync(CONFIG.outputDir)) fs.mkdirSync(CONFIG.outputDir, { recursive: true });

const PROMPT_PRIMARY =
  "Design a URL shortening service like bit.ly with analytics, caching, and high availability.";
const PROMPT_SECONDARY =
  "Design a video streaming platform with upload, transcoding, and CDN distribution.";
const SYNC_TRIGGER_MESSAGE =
  "Add a CDN in front of the load balancer to serve cached responses faster.";

async function fillTextarea(page, selector, text) {
  await page.waitForSelector(selector, { visible: true, timeout: 10_000 });
  await page.evaluate((sel, val) => {
    const el = document.querySelector(sel);
    if (!el) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
    setter.call(el, val);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, selector, text);
}

async function signInWithClerk(page) {
  if (!CONFIG.clerkSecretKey) throw new Error("CLERK_SECRET_KEY not set");
  console.log("  Creating Clerk sign-in token...");
  const tokenRes = await fetch("https://api.clerk.com/v1/sign_in_tokens", {
    method: "POST",
    headers: { Authorization: `Bearer ${CONFIG.clerkSecretKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: CONFIG.clerkUserId, expires_in_seconds: 3600 }),
  });
  const tokenData = await tokenRes.json();
  if (!tokenData.token) throw new Error(`Failed to create sign-in token: ${JSON.stringify(tokenData)}`);
  await page.waitForFunction(() => window.Clerk && window.Clerk.loaded, { timeout: 15_000 });
  const result = await page.evaluate(async (ticket) => {
    try {
      const signIn = await window.Clerk.client.signIn.create({ strategy: "ticket", ticket });
      await window.Clerk.setActive({ session: signIn.createdSessionId });
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message || String(err) };
    }
  }, tokenData.token);
  if (!result.success) throw new Error(`Clerk sign-in failed: ${result.error}`);
  await new Promise((r) => setTimeout(r, 3000));
  console.log("  Signed in.");
}

async function generateDiagramAndDoc(page, prompt) {
  await page.waitForSelector("textarea", { visible: true, timeout: 10_000 });
  await fillTextarea(page, "textarea", prompt);
  await page.click('button[type="submit"]');
  process.stdout.write("  generating diagram");
  await page.waitForSelector(".custom-node", { visible: true, timeout: CONFIG.diagramTimeout });
  console.log(" done.");
  await new Promise((r) => setTimeout(r, 4000));

  const exitBtn = await page.$(".exit-node-focus-button");
  if (exitBtn) await exitBtn.click();
  await new Promise((r) => setTimeout(r, 500));

  process.stdout.write("  generating design doc");
  await page.click(".create-design-doc-button");
  await page.waitForFunction(
    () => {
      const editor = document.querySelector(".design-doc-panel .ProseMirror");
      return editor && editor.textContent.length > 800;
    },
    { timeout: CONFIG.designDocTimeout, polling: 2000 }
  );
  console.log(" done.");
  await new Promise((r) => setTimeout(r, 2500));
}

/**
 * Screenshot a section of the design doc identified by its heading text.
 * Scrolls the doc to put that section near the top of the panel, then
 * crops the screenshot to the panel area.
 */
async function captureDocSection(page, headingText, outName) {
  const found = await page.evaluate((heading) => {
    const editor = document.querySelector(".design-doc-panel .ProseMirror");
    if (!editor) return { ok: false, reason: "no editor" };
    const headings = Array.from(editor.querySelectorAll("h1, h2, h3"));
    const target = headings.find((h) =>
      h.textContent.trim().toLowerCase().startsWith(heading.toLowerCase())
    );
    if (!target) {
      return { ok: false, reason: "heading not found", available: headings.map((h) => h.textContent.trim()).slice(0, 12) };
    }
    target.scrollIntoView({ block: "start" });
    return { ok: true, top: target.getBoundingClientRect().top };
  }, headingText);

  if (!found.ok) {
    console.log(`  warning: section "${headingText}" — ${found.reason}; available: ${(found.available || []).join(" | ")}`);
    return null;
  }

  await new Promise((r) => setTimeout(r, 600));

  const panel = await page.$(".design-doc-panel");
  if (!panel) {
    console.log(`  warning: design-doc-panel not found`);
    return null;
  }
  const out = path.join(CONFIG.outputDir, outName);
  await panel.screenshot({ path: out });
  console.log(`  saved ${outName}`);
  return out;
}

(async () => {
  console.log(`Capturing doc-page screenshots from ${CONFIG.url}`);
  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
    defaultViewport: { width: 1600, height: 1000, deviceScaleFactor: 2 },
  });

  const page = await browser.newPage();
  page.on("console", (msg) => {
    const t = msg.text();
    if (/error/i.test(t)) console.log(`  [browser] ${t.slice(0, 200)}`);
  });

  try {
    await page.goto(CONFIG.url, { waitUntil: "networkidle0", timeout: 60_000 });
    await signInWithClerk(page);

    // ============================================================
    // SESSION 1: URL shortener — primary doc screenshots
    // ============================================================
    console.log("\nSession 1: URL shortener");
    await generateDiagramAndDoc(page, PROMPT_PRIMARY);

    // 01: Full design doc panel
    const docPanel = await page.$(".design-doc-panel");
    if (docPanel) {
      // Scroll to top of doc first
      await page.evaluate(() => {
        const editor = document.querySelector(".design-doc-panel .ProseMirror");
        if (editor) editor.scrollTop = 0;
      });
      await new Promise((r) => setTimeout(r, 500));
      const out = path.join(CONFIG.outputDir, "01-doc-panel-full.png");
      await docPanel.screenshot({ path: out });
      console.log("  saved 01-doc-panel-full.png");
    }

    // 02-05: section close-ups
    await captureDocSection(page, "Executive Summary", "02-doc-executive-summary.png");
    await captureDocSection(page, "Component Details", "03-doc-component-details.png");
    await captureDocSection(page, "Data Flow", "04-doc-data-flow.png");
    // try Trade-offs first; fall back to Scalability
    const tradeShot = await captureDocSection(page, "Trade-offs", "05-doc-trade-offs.png");
    if (!tradeShot) await captureDocSection(page, "Scalability", "05-doc-trade-offs.png");

    // 06: toolbar close-up. Crop the design-doc-toolbar element.
    await page.evaluate(() => {
      const editor = document.querySelector(".design-doc-panel .ProseMirror");
      if (editor) editor.scrollTop = 0;
    });
    await new Promise((r) => setTimeout(r, 400));
    const toolbar = await page.$(".design-doc-toolbar");
    if (toolbar) {
      // To make the toolbar shot meaningful, also include some of the editor underneath it.
      // We screenshot a tall slice of the panel that starts at the toolbar and includes the first paragraph.
      const box = await toolbar.boundingBox();
      if (box) {
        const slice = {
          x: box.x,
          y: box.y - 4,
          width: box.width,
          height: Math.min(box.height + 280, 600),
        };
        const out = path.join(CONFIG.outputDir, "06-doc-toolbar.png");
        await page.screenshot({ path: out, clip: slice });
        console.log("  saved 06-doc-toolbar.png");
      }
    }

    // 07: export dropdown open
    const exportSelect = await page.$(".design-doc-panel .export-dropdown");
    if (exportSelect) {
      // Open the native <select> menu — Puppeteer can't really open a native select.
      // Instead, screenshot the footer row with the dropdown closed (still informative).
      const footer = await page.$(".design-doc-footer");
      if (footer) {
        const out = path.join(CONFIG.outputDir, "07-doc-export-footer.png");
        await footer.screenshot({ path: out });
        console.log("  saved 07-doc-export-footer.png");
      }
    }

    // 08: full app showing sync indicator (trigger via chat)
    console.log("\nCapturing sync indicator state...");
    await fillTextarea(page, ".chat-input-form textarea", SYNC_TRIGGER_MESSAGE);
    const msgCountBefore = await page.evaluate(() => document.querySelectorAll(".message.assistant").length);
    await page.click('.chat-input-form button[type="submit"]');
    await page.waitForFunction(
      (prev) => {
        const msgs = document.querySelectorAll(".message.assistant");
        return msgs.length > prev && !document.querySelector(".message-content.typing");
      },
      { timeout: CONFIG.chatResponseTimeout },
      msgCountBefore
    );
    // Wait for sync indicator to appear
    const indicatorSeen = await page.waitForFunction(
      () => {
        const el = document.querySelector(".design-doc-panel .save-status");
        return el && /Auto-sync queued|Syncing with diagram/i.test(el.textContent || "");
      },
      { timeout: 30_000, polling: 250 }
    ).catch(() => null);

    if (indicatorSeen) {
      const observed = await page.$eval(".design-doc-panel .save-status", (el) => el.textContent);
      console.log(`  sync indicator: ${observed}`);
      await new Promise((r) => setTimeout(r, 500));
      const out = path.join(CONFIG.outputDir, "08-doc-app-with-sync.png");
      await page.screenshot({ path: out, fullPage: false });
      console.log("  saved 08-doc-app-with-sync.png");
    } else {
      console.log("  (sync indicator did not appear in time, skipping 08)");
    }

    // ============================================================
    // SESSION 2: Different example for variety
    // ============================================================
    console.log("\nSession 2: video streaming (for variety)");
    // Click "New Design" button to start fresh
    const newBtn = await page.$(".new-design-button");
    if (newBtn) {
      await newBtn.click();
      await new Promise((r) => setTimeout(r, 1500));
    } else {
      // Fallback: hard reload
      await page.goto(CONFIG.url, { waitUntil: "networkidle0", timeout: 60_000 });
      await new Promise((r) => setTimeout(r, 1500));
    }

    try {
      await generateDiagramAndDoc(page, PROMPT_SECONDARY);
      const out = path.join(CONFIG.outputDir, "09-doc-second-example.png");
      await page.screenshot({ path: out, fullPage: false });
      console.log("  saved 09-doc-second-example.png");
    } catch (e) {
      console.log(`  session 2 skipped: ${e.message}`);
    }
  } finally {
    await browser.close();
  }
})();
