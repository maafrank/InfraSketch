/**
 * InfraSketch Content Generator
 *
 * Automates the full 8-step content creation flow:
 * 1. Show the prompt
 * 2. Generate diagram
 * 3. Ask question about diagram
 * 4. Request diagram edit
 * 5. Generate design doc
 * 6. Edit design doc
 * 7. Export design doc
 * 8. Branding CTA slide
 *
 * Uses Clerk sign-in tokens for authentication and drives the real UI.
 *
 * Usage:
 *   node generate-content.js --diagram "Build a scalable video streaming platform"
 *   node generate-content.js --from-calendar 42
 *   node generate-content.js --dry-run
 *
 * Environment (in .env):
 *   INFRASKETCH_URL       - Frontend URL (default: http://localhost:5173)
 *   CLERK_SECRET_KEY      - Clerk backend secret (from project .env)
 *   CLERK_USER_ID         - Your Clerk user ID
 *   OUTPUT_DIR            - Where to save screenshots (default: ./output)
 */

import puppeteer from "puppeteer";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load .env from project root
function loadEnv() {
  const envPath = path.join(__dirname, ".env");
  const rootEnvPath = path.join(__dirname, "..", ".env");
  for (const p of [envPath, rootEnvPath]) {
    if (fs.existsSync(p)) {
      const lines = fs.readFileSync(p, "utf-8").split("\n");
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;
        const eqIdx = trimmed.indexOf("=");
        if (eqIdx === -1) continue;
        const key = trimmed.slice(0, eqIdx);
        const val = trimmed.slice(eqIdx + 1);
        if (!process.env[key]) process.env[key] = val;
      }
    }
  }
}
loadEnv();

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const CONFIG = {
  url: process.env.INFRASKETCH_URL || "http://localhost:5173",
  clerkSecretKey: process.env.CLERK_SECRET_KEY,
  clerkUserId:
    process.env.CLERK_USER_ID || "user_35iGQA7ljylILobA6sMZOom9jd5",
  outputDir: process.env.OUTPUT_DIR || path.join(__dirname, "output"),
  viewport: { width: 1920, height: 1080 },
  diagramTimeout: 180_000,
  chatResponseTimeout: 300_000,
  designDocTimeout: 180_000,
  screenshotDelay: 1500,
};

// ---------------------------------------------------------------------------
// CLI arg parsing
// ---------------------------------------------------------------------------

function parseArgs() {
  const args = process.argv.slice(2);
  const parsed = {
    diagram: null,
    fromCalendar: null,
    dryRun: false,
    chatQuestion: "What are the main bottlenecks in this architecture?",
    chatEdit:
      "Move the cache layer between the API gateway and the backend services for better read performance",
    model: "claude-haiku-4-5",
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--diagram":
        parsed.diagram = args[++i];
        break;
      case "--from-calendar":
        parsed.fromCalendar = parseInt(args[++i], 10);
        break;
      case "--dry-run":
        parsed.dryRun = true;
        break;
      case "--question":
        parsed.chatQuestion = args[++i];
        break;
      case "--edit":
        parsed.chatEdit = args[++i];
        break;
      case "--model":
        parsed.model = args[++i];
        break;
    }
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Calendar loader
// ---------------------------------------------------------------------------

function parseCSVLine(line) {
  const fields = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        current += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        current += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      fields.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  fields.push(current);
  return fields;
}

function loadCalendarEntry(dayNumber) {
  // Try CSV first, then JSON
  const csvPath = path.join(__dirname, "content-calendar.csv");
  const jsonPath = path.join(__dirname, "content-calendar.json");

  if (fs.existsSync(csvPath)) {
    const lines = fs.readFileSync(csvPath, "utf-8").split("\n").filter((l) => l.trim());
    const headers = parseCSVLine(lines[0]);

    for (let i = 1; i < lines.length; i++) {
      const fields = parseCSVLine(lines[i]);
      const row = {};
      headers.forEach((h, idx) => (row[h.trim()] = (fields[idx] || "").trim()));
      if (parseInt(row["Day"], 10) === dayNumber) {
        return {
          day: dayNumber,
          title: row["Diagram Title"] || `Day ${dayNumber}`,
          prompt: row["Step 1: Generation Prompt"],
          question: row["Step 3: Chat Question"],
          category: row["Category"],
          instagramCaption: row["Instagram Caption"],
          tiktokCaption: row["TikTok Caption"],
          hashtags: row["Hashtags"],
          difficulty: row["Difficulty"],
        };
      }
    }
    throw new Error(`No calendar entry for day ${dayNumber} in CSV`);
  }

  if (fs.existsSync(jsonPath)) {
    const calendar = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
    const entry = calendar.find((e) => e.day === dayNumber);
    if (!entry) throw new Error(`No calendar entry for day ${dayNumber}`);
    return entry;
  }

  throw new Error("No content-calendar.csv or content-calendar.json found.");
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

async function screenshot(page, name, stepNumber, outputDir, opts = {}) {
  await new Promise((r) => setTimeout(r, CONFIG.screenshotDelay));
  const filename = `${String(stepNumber).padStart(2, "0")}-${name}.png`;
  const filepath = path.join(outputDir, filename);

  if (opts.selector) {
    // Element-level screenshot (crops to just that DOM element)
    const el = await page.$(opts.selector);
    if (el) {
      await el.screenshot({ path: filepath });
      console.log(`  Screenshot: ${filename} (element: ${opts.selector})`);
      return filepath;
    }
    console.log(`  Warning: ${opts.selector} not found, falling back to full page`);
  }

  await page.screenshot({ path: filepath, fullPage: false });
  console.log(`  Screenshot: ${filename}`);
  return filepath;
}

/**
 * React-compatible textarea fill. Standard page.type() doesn't trigger
 * React's synthetic events properly.
 */
async function fillTextarea(page, selector, text) {
  await page.waitForSelector(selector, { visible: true, timeout: 10_000 });
  await page.evaluate(
    (sel, val) => {
      const el = document.querySelector(sel);
      if (!el) return;
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value"
      ).set;
      setter.call(el, val);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    },
    selector,
    text
  );
}

// ---------------------------------------------------------------------------
// Auth: Clerk sign-in via token
// ---------------------------------------------------------------------------

async function signInWithClerk(page) {
  if (!CONFIG.clerkSecretKey) {
    throw new Error("CLERK_SECRET_KEY not set. Add it to .env");
  }

  console.log("  Creating Clerk sign-in token...");
  const tokenRes = await fetch("https://api.clerk.com/v1/sign_in_tokens", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${CONFIG.clerkSecretKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: CONFIG.clerkUserId,
      expires_in_seconds: 3600,
    }),
  });
  const tokenData = await tokenRes.json();
  if (!tokenData.token) {
    throw new Error(
      `Failed to create sign-in token: ${JSON.stringify(tokenData)}`
    );
  }

  // Wait for Clerk to load in the browser
  await page.waitForFunction(() => window.Clerk && window.Clerk.loaded, {
    timeout: 15_000,
  });

  // Use the ticket strategy to sign in
  const result = await page.evaluate(async (ticket) => {
    try {
      const signIn = await window.Clerk.client.signIn.create({
        strategy: "ticket",
        ticket,
      });
      await window.Clerk.setActive({ session: signIn.createdSessionId });
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message || String(err) };
    }
  }, tokenData.token);

  if (!result.success) {
    throw new Error(`Clerk sign-in failed: ${result.error}`);
  }

  // Wait for the app to re-render as authenticated
  await new Promise((r) => setTimeout(r, 3000));
  console.log("  Signed in as Matt Frank");
}

// ---------------------------------------------------------------------------
// Step implementations (all UI-driven)
// ---------------------------------------------------------------------------

/**
 * Step 1: Type the prompt and screenshot
 */
async function step1_showPrompt(page, prompt, model, stepNum, outputDir) {
  console.log(`\nStep ${stepNum}: Show the prompt`);

  // We're authenticated, so we see the app view with input panel
  // Wait for the input area
  await page.waitForSelector("textarea", { visible: true, timeout: 10_000 });

  // Select model if dropdown exists
  const modelSelect = await page.$("#model-select");
  if (modelSelect) {
    await page.select("#model-select", model);
  }

  // Type the prompt
  await fillTextarea(page, "textarea", prompt);

  return screenshot(page, "prompt", stepNum, outputDir, { selector: ".chat-input-form" });
}

/**
 * Step 2: Submit and wait for diagram to generate
 */
async function step2_generateDiagram(page, stepNum, outputDir) {
  console.log(`\nStep ${stepNum}: Generate diagram`);

  // Click submit
  await page.click('button[type="submit"]');

  // Wait for nodes to appear (diagram generated)
  process.stdout.write("  Generating");
  await page.waitForSelector(".custom-node", {
    visible: true,
    timeout: CONFIG.diagramTimeout,
  });
  console.log(" done!");

  // Wait for layout to settle
  await new Promise((r) => setTimeout(r, 3000));

  // Export diagram-only PNG by clicking the app's export button.
  // This captures just nodes/edges at 2x resolution with watermark,
  // no chat panel or UI chrome, ideal for reels and mobile content.
  const filename = `${String(stepNum).padStart(2, "0")}-diagram.png`;
  const filepath = path.join(outputDir, filename);

  // Set up download interception to capture the exported PNG
  const client = await page.createCDPSession();
  await client.send("Page.setDownloadBehavior", {
    behavior: "allow",
    downloadPath: outputDir,
  });

  // The export button downloads "diagram.png", remove any stale copy
  const downloadedPath = path.join(outputDir, "diagram.png");
  if (fs.existsSync(downloadedPath)) fs.unlinkSync(downloadedPath);

  // Dismiss any alert dialogs (the export shows an alert on failure)
  const dialogHandler = (dialog) => dialog.dismiss();
  page.on("dialog", dialogHandler);

  // Click the camera/export PNG button on the React Flow canvas
  const exportBtn = await page.$(".floating-camera-button");
  if (exportBtn) {
    await exportBtn.click();

    // Wait for the download to complete (the app's export is near-instant)
    let waited = 0;
    while (!fs.existsSync(downloadedPath) && waited < 15_000) {
      await new Promise((r) => setTimeout(r, 250));
      waited += 250;
    }

    if (fs.existsSync(downloadedPath)) {
      fs.renameSync(downloadedPath, filepath);
      console.log(`  Screenshot: ${filename} (diagram-only export, 2x resolution)`);
      await client.detach();
      page.off("dialog", dialogHandler);
      return filepath;
    }
    console.log("  Warning: export download timed out, falling back to element screenshot");
  } else {
    console.log("  Warning: export button not found, falling back to element screenshot");
  }

  await client.detach();
  page.off("dialog", dialogHandler);

  // Fallback: screenshot just the React Flow container
  return screenshot(page, "diagram", stepNum, outputDir, { selector: ".react-flow" });
}

/**
 * Step 3: Click a node and ask a question
 */
async function step3_askQuestion(page, question, stepNum, outputDir) {
  console.log(`\nStep ${stepNum}-${stepNum + 1}: Ask question about diagram`);

  // Chat panel is already open after diagram generation, just type in it
  await page.waitForSelector(".chat-input-form textarea", {
    visible: true,
    timeout: 5000,
  });
  await new Promise((r) => setTimeout(r, 500));

  // Type question
  const results = [];
  await fillTextarea(page, ".chat-input-form textarea", question);
  results.push(await screenshot(page, "question-typed", stepNum, outputDir, { selector: ".chat-input-form" }));

  // Count messages before sending
  const msgCountBefore = await page.evaluate(
    () => document.querySelectorAll(".message.assistant").length
  );

  // Send
  await page.click('.chat-input-form button[type="submit"]');

  // Wait for a new assistant message that isn't a loading indicator
  await page.waitForFunction(
    (prevCount) => {
      const msgs = document.querySelectorAll(".message.assistant");
      if (msgs.length <= prevCount) return false;
      // Check that no .typing indicator is present (loading done)
      const typing = document.querySelector(".message-content.typing");
      return !typing;
    },
    { timeout: CONFIG.chatResponseTimeout },
    msgCountBefore
  );

  await new Promise((r) => setTimeout(r, 1500));

  // Scroll chat panel to the bottom so the latest response is visible
  await page.evaluate(() => {
    const chatMessages = document.querySelector(".chat-messages");
    if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
  });
  await new Promise((r) => setTimeout(r, 500));

  results.push(await screenshot(page, "question-answered", stepNum + 1, outputDir, { selector: ".chat-panel" }));
  return results;
}

/**
 * Step 5: Generate design document
 */
async function step5_generateDesignDoc(page, stepNum, outputDir) {
  console.log(`\nStep ${stepNum}-${stepNum + 1}: Generate design doc`);

  // Exit node focus first
  const exitBtn = await page.$(".exit-node-focus-button");
  if (exitBtn) await exitBtn.click();
  await new Promise((r) => setTimeout(r, 500));

  // Click "Create Design Doc"
  await page.click(".create-design-doc-button");

  // Wait for overlay to appear
  try {
    await page.waitForSelector(".generating-overlay", {
      visible: true,
      timeout: 5000,
    });
    await screenshot(page, "design-doc-generating", stepNum, outputDir);
  } catch {
    // May already be past the loading state
  }

  // Wait for overlay to disappear (generation complete)
  process.stdout.write("  Generating");
  await page.waitForSelector(".generating-overlay", {
    hidden: true,
    timeout: CONFIG.designDocTimeout,
  });
  console.log(" done!");

  await new Promise((r) => setTimeout(r, 2000));
  const complete = await screenshot(page, "design-doc-complete", stepNum + 1, outputDir, { selector: ".design-doc-panel" });

  // Return both screenshots
  const generating = path.join(outputDir, `${String(stepNum).padStart(2, "0")}-design-doc-generating.png`);
  const results = [];
  if (fs.existsSync(generating)) results.push(generating);
  results.push(complete);
  return results;
}

/**
 * Branded CTA slide with real logo
 */
async function stepBrandingSlide(page, stepNum, outputDir) {
  console.log(`\nStep ${stepNum}: Branding slide`);

  // Read the logo file as base64
  // Try local copy first (EC2 deploy), then repo root (local dev)
  const localLogo = path.join(__dirname, "InfraSketchLogoTransparent_03_256.png");
  const repoLogo = path.join(__dirname, "..", "..", "assets", "logos", "InfraSketchLogoTransparent_03_256.png");
  const logoPath = fs.existsSync(localLogo) ? localLogo : repoLogo;
  const logoBase64 = fs.readFileSync(logoPath).toString("base64");
  const logoDataUrl = `data:image/png;base64,${logoBase64}`;

  await page.evaluate((logoSrc) => {
    const overlay = document.createElement("div");
    overlay.style.cssText = `
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: #141419;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 99999;
      color: white;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    `;
    overlay.innerHTML = `
      <div style="text-align: center; transform: scale(1.4); transform-origin: center center;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 20px; margin-bottom: 16px;">
          <img src="${logoSrc}" style="width: 80px; height: 80px;" />
          <div style="font-size: 72px; font-weight: 800; letter-spacing: -2px; color: #00cc44;">
            InfraSketch
          </div>
        </div>
        <div style="font-size: 28px; opacity: 0.7; margin-bottom: 48px; font-weight: 300;">
          AI-Powered System Design
        </div>
        <div style="
          font-size: 24px;
          padding: 16px 48px;
          border: 2px solid #00cc44;
          border-radius: 12px;
          letter-spacing: 1px;
          color: #00cc44;
        ">
          infrasketch.net
        </div>
        <div style="font-size: 18px; opacity: 0.4; margin-top: 32px;">
          Design your infrastructure in minutes, not hours
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
  }, logoDataUrl);

  return screenshot(page, "branding-cta", stepNum, outputDir);
}

// ---------------------------------------------------------------------------
// Main flow
// ---------------------------------------------------------------------------

async function generateContent(args) {
  let prompt, chatQuestion, chatEdit, metadata;

  if (args.fromCalendar) {
    const entry = loadCalendarEntry(args.fromCalendar);
    prompt = entry.prompt;
    chatQuestion = entry.question || args.chatQuestion;
    chatEdit = entry.edit || args.chatEdit;
    metadata = entry;
    console.log(`Loaded calendar day ${args.fromCalendar}: "${entry.title}"`);
  } else if (args.diagram) {
    prompt = args.diagram;
    chatQuestion = args.chatQuestion;
    chatEdit = args.chatEdit;
    metadata = { title: prompt.slice(0, 60), day: "manual" };
  } else {
    console.error("Provide --diagram or --from-calendar");
    process.exit(1);
  }

  // Create output directory
  const timestamp = new Date().toISOString().slice(0, 10);
  const slug = metadata.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .slice(0, 40);
  const runDir = path.join(CONFIG.outputDir, `${timestamp}-${slug}`);
  ensureDir(runDir);

  console.log(`Output: ${runDir}`);
  console.log(`Target: ${CONFIG.url}`);
  console.log(`Prompt: "${prompt}"`);

  // Launch browser
  const launchOpts = {
    headless: "new",
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--window-size=1920,1080",
    ],
    defaultViewport: CONFIG.viewport,
  };
  // Use system Chromium on EC2 (set via PUPPETEER_EXECUTABLE_PATH env var)
  if (process.env.PUPPETEER_EXECUTABLE_PATH) {
    launchOpts.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
  }
  const browser = await puppeteer.launch(launchOpts);

  const page = await browser.newPage();
  const screenshots = [];

  try {
    // Navigate to InfraSketch
    console.log("\nNavigating to InfraSketch...");
    await page.goto(CONFIG.url, {
      waitUntil: "networkidle2",
      timeout: 30_000,
    });

    // Sign in with Clerk token
    console.log("Signing in...");
    await signInWithClerk(page);

    // Wait for authenticated app to load
    await page.waitForSelector("textarea", {
      visible: true,
      timeout: 10_000,
    });

    let step = 1;

    // 01: Show the prompt
    screenshots.push(await step1_showPrompt(page, prompt, args.model, step++, runDir));

    // 02: Generate diagram
    screenshots.push(await step2_generateDiagram(page, step++, runDir));

    // 03: Question typed, 04: Question answered (retry once on timeout)
    try {
      screenshots.push(...await step3_askQuestion(page, chatQuestion, step, runDir));
    } catch (chatErr) {
      console.log(`  Chat question failed (${chatErr.message}), retrying...`);
      await new Promise((r) => setTimeout(r, 3000));
      screenshots.push(...await step3_askQuestion(page, chatQuestion, step, runDir));
    }
    step += 2;

    // 05: Design doc generating, 06: Design doc complete
    screenshots.push(...await step5_generateDesignDoc(page, step, runDir));
    step += 2;

    // 08: Branding CTA
    screenshots.push(await stepBrandingSlide(page, step++, runDir));

    // Write metadata
    const meta = {
      timestamp: new Date().toISOString(),
      prompt,
      chatQuestion,
      chatEdit,
      model: args.model,
      screenshots: screenshots.map((s) => path.basename(s)),
      calendar: metadata,
    };
    fs.writeFileSync(
      path.join(runDir, "metadata.json"),
      JSON.stringify(meta, null, 2)
    );

    console.log(
      `\nDone! ${screenshots.length} screenshots saved to ${runDir}`
    );
    console.log("Screenshots:", meta.screenshots.join(", "));

    return { runDir, screenshots, metadata: meta };
  } catch (err) {
    console.error("\nError during content generation:", err.message);
    await page
      .screenshot({ path: path.join(runDir, "error-state.png") })
      .catch(() => {});
    throw err;
  } finally {
    await browser.close();
  }
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

const args = parseArgs();
generateContent(args).catch((err) => {
  console.error(err);
  process.exit(1);
});
