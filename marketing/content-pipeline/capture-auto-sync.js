/**
 * One-shot capture: produces a hero image for the landing page that shows
 * the auto-sync feature in action. Specifically, the moment when the design
 * doc panel is showing "Auto-sync queued" or "Syncing with diagram..." after
 * the diagram has been modified.
 *
 * Usage:
 *   cd marketing/content-pipeline
 *   node capture-auto-sync.js
 *   # output: ./output/auto-sync-hero.png
 *
 * Reuses Clerk sign-in flow + helpers from generate-content.js.
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
  outputDir: path.join(__dirname, "output"),
  diagramTimeout: 90_000,
  chatResponseTimeout: 60_000,
  designDocTimeout: 180_000,
};

if (!fs.existsSync(CONFIG.outputDir)) fs.mkdirSync(CONFIG.outputDir, { recursive: true });

const PROMPT =
  "Build a URL shortener with a load balancer, API service, Redis cache, and PostgreSQL database. Keep it simple, just the essentials.";
const SYNC_TRIGGER_MESSAGE = "Add a CDN in front of the load balancer to serve cached responses faster.";

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

(async () => {
  console.log(`Capturing auto-sync hero from ${CONFIG.url}`);
  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
    defaultViewport: { width: 1600, height: 1000, deviceScaleFactor: 2 },
  });

  const page = await browser.newPage();
  page.on("console", (msg) => {
    const t = msg.text();
    if (/error|warn/i.test(t)) console.log(`  [browser] ${t.slice(0, 200)}`);
  });

  try {
    await page.goto(CONFIG.url, { waitUntil: "networkidle0", timeout: 60_000 });
    await signInWithClerk(page);

    // Generate diagram
    console.log("Step 1: generate diagram");
    await page.waitForSelector("textarea", { visible: true, timeout: 10_000 });
    await fillTextarea(page, "textarea", PROMPT);
    await page.click('button[type="submit"]');
    process.stdout.write("  generating");
    await page.waitForSelector(".custom-node", { visible: true, timeout: CONFIG.diagramTimeout });
    console.log(" done.");
    await new Promise((r) => setTimeout(r, 4000));

    // Generate design doc
    console.log("Step 2: generate design doc");
    const exitBtn = await page.$(".exit-node-focus-button");
    if (exitBtn) await exitBtn.click();
    await new Promise((r) => setTimeout(r, 500));
    await page.click(".create-design-doc-button");
    process.stdout.write("  waiting for design doc");
    await page.waitForFunction(
      () => {
        const editor = document.querySelector(".design-doc-panel .ProseMirror");
        return editor && editor.textContent.length > 200;
      },
      { timeout: CONFIG.designDocTimeout, polling: 2000 }
    );
    console.log(" done.");
    await new Promise((r) => setTimeout(r, 3000));

    // Trigger a sync via chat (adds a CDN, mutates the diagram)
    console.log("Step 3: trigger auto-sync via chat");
    await fillTextarea(page, ".chat-input-form textarea", SYNC_TRIGGER_MESSAGE);
    const msgCountBefore = await page.evaluate(
      () => document.querySelectorAll(".message.assistant").length
    );
    await page.click('.chat-input-form button[type="submit"]');
    await page.waitForFunction(
      (prev) => {
        const msgs = document.querySelectorAll(".message.assistant");
        if (msgs.length <= prev) return false;
        return !document.querySelector(".message-content.typing");
      },
      { timeout: CONFIG.chatResponseTimeout },
      msgCountBefore
    );
    console.log("  diagram modified.");

    // Now poll for the sync indicator to appear in the doc panel.
    // The save-status div text becomes "Auto-sync queued" then "Syncing with diagram...".
    console.log("Step 4: poll for sync indicator");
    const indicatorVisible = await page.waitForFunction(
      () => {
        const el = document.querySelector(".design-doc-panel .save-status");
        if (!el) return false;
        const t = el.textContent || "";
        return /Auto-sync queued|Syncing with diagram/i.test(t);
      },
      { timeout: 30_000, polling: 250 }
    ).catch((err) => {
      console.log(`  warning: indicator not seen within timeout (${err.message})`);
      return null;
    });

    if (indicatorVisible) {
      const observed = await page.$eval(".design-doc-panel .save-status", (el) => el.textContent);
      console.log(`  indicator visible: ${observed}`);
    }

    // Capture immediately - the indicator stays for at least the 8s debounce + sync run.
    await new Promise((r) => setTimeout(r, 600));
    const out = path.join(CONFIG.outputDir, "auto-sync-hero.png");
    await page.screenshot({ path: out, fullPage: false });
    console.log(`Saved: ${out}`);

    // Bonus: if "Syncing with diagram..." comes around, capture that too.
    const runningSeen = await page.waitForFunction(
      () => {
        const el = document.querySelector(".design-doc-panel .save-status");
        return el && /Syncing with diagram/i.test(el.textContent || "");
      },
      { timeout: 12_000, polling: 250 }
    ).catch(() => null);

    if (runningSeen) {
      await new Promise((r) => setTimeout(r, 400));
      const out2 = path.join(CONFIG.outputDir, "auto-sync-running-hero.png");
      await page.screenshot({ path: out2, fullPage: false });
      console.log(`Saved: ${out2}`);
    }
  } finally {
    await browser.close();
  }
})();
