#!/usr/bin/env node
// Build-time prerender. After `vite build` produces frontend/dist/, this script:
//   1. Boots `vite preview` against dist on port 4173.
//   2. Crawls each public route with Puppeteer.
//   3. Waits for react-helmet-async to inject the per-page <title>/canonical/og tags.
//   4. Serializes the rendered DOM and writes it to dist/<route>/index.html.
//
// Wired into the build via the `postbuild` npm script in frontend/package.json.
// S3 website hosting auto-serves <directory>/index.html, so the directory layout
// works without any CloudFront URI rewriting.
//
// Auth-gated routes (/history, /session/:id, /settings, /achievements) are
// intentionally excluded; they require Clerk and have no SEO value.

import { spawn } from 'node:child_process';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const FRONTEND = path.join(REPO_ROOT, 'frontend');
const DIST = path.join(FRONTEND, 'dist');
const POSTS_INDEX = path.join(FRONTEND, 'public/blog/posts/index.json');

// puppeteer + p-limit are devDependencies of frontend/, not the repo root.
// Resolve them via the frontend package's module map.
const fromFrontend = createRequire(path.join(FRONTEND, 'package.json'));
const puppeteerEntry = fromFrontend.resolve('puppeteer');
const pLimitEntry = fromFrontend.resolve('p-limit');
const puppeteer = (await import(pathToFileURL(puppeteerEntry).href)).default;
const pLimit = (await import(pathToFileURL(pLimitEntry).href)).default;

const PORT = 4173;
const ORIGIN = `http://localhost:${PORT}`;
const CONCURRENCY = 4;
const PAGE_TIMEOUT_MS = 30_000;

const STATIC_ROUTES = [
  '/',
  '/about',
  '/careers',
  '/contact',
  '/pricing',
  '/privacy',
  '/terms',
  '/blog',
  '/compare',
  '/tools/system-design-tool',
  '/tools/ai-diagram-generator',
  '/tools/architecture-diagram-tool',
  '/tools/design-doc-generator',
  '/tools/ml-system-design-tool',
  '/tools/llm-architecture-tool',
  '/compare/eraser',
  '/compare/lucidchart',
  '/compare/system-design-primer',
  '/compare/bytebytego',
  '/compare/mermaid',
  '/compare/draw-io',
  '/compare/whimsical',
  '/compare/chatgpt',
];

async function getRoutes() {
  const raw = await readFile(POSTS_INDEX, 'utf8');
  const { posts } = JSON.parse(raw);
  const blogRoutes = posts.map((p) => `/blog/${p.slug}`);
  // '__notfound__' is a sentinel: prerender writes dist/404.html (NotFoundPage with
  // noindex), used by CloudFront's CustomErrorResponse for 404 responses.
  return [...STATIC_ROUTES, ...blogRoutes, '__notfound__'];
}

function startVitePreview() {
  return new Promise((resolve, reject) => {
    const child = spawn(
      'npx',
      ['vite', 'preview', '--port', String(PORT), '--strictPort'],
      { cwd: FRONTEND, stdio: ['ignore', 'pipe', 'pipe'] }
    );
    let resolved = false;
    // Vite emits ANSI color codes on Linux CI runners even when stdio is piped,
    // inserting escapes between "Local" and ":" that break a naive regex.
    const ANSI_RE = /\x1b\[[0-9;]*m/g;
    const onLine = (chunk) => {
      const text = chunk.toString();
      const clean = text.replace(ANSI_RE, '');
      process.stdout.write(`[vite] ${text}`);
      if (!resolved && /Local:\s+http:\/\/localhost/.test(clean)) {
        resolved = true;
        resolve(child);
      }
    };
    child.stdout.on('data', onLine);
    child.stderr.on('data', onLine);
    child.on('exit', (code) => {
      if (!resolved) reject(new Error(`vite preview exited early with code ${code}`));
    });
    setTimeout(() => {
      if (!resolved) reject(new Error('vite preview did not become ready within 20s'));
    }, 20_000);
  });
}

async function waitForReady(url, attempts = 30) {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`server did not respond OK at ${url}`);
}

function outputPathFor(route) {
  if (route === '/') return path.join(DIST, 'index.html');
  if (route === '__notfound__') return path.join(DIST, '404.html');
  return path.join(DIST, route.replace(/^\//, ''), 'index.html');
}

function isBlogPost(route) {
  return route.startsWith('/blog/') && route !== '/blog/';
}

function validate(html, route) {
  const titleMatch = html.match(/<title[^>]*>([^<]*)<\/title>/i);
  const title = titleMatch ? titleMatch[1].trim() : '';
  const hasCanonical = /<link[^>]+rel=["']canonical["']/i.test(html);
  const hasNoindex = /<meta[^>]+name=["']robots["'][^>]+noindex/i.test(html);
  const errors = [];
  if (!title || title === 'InfraSketch') {
    errors.push(`default or empty title (got "${title}")`);
  }
  // NotFoundPage (and any other noindex page) intentionally omits canonical.
  if (!hasCanonical && !hasNoindex) {
    errors.push('missing <link rel="canonical"> on indexable page');
  }
  return errors;
}

async function prerenderRoute(browser, route) {
  // Special sentinel: hit a known-bad URL so React Router renders NotFoundPage,
  // and we save the result to dist/404.html for CloudFront's 404 response page.
  const targetUrl =
    route === '__notfound__' ? `${ORIGIN}/__not_found_sentinel__` : `${ORIGIN}${route}`;
  const page = await browser.newPage();
  page.setDefaultTimeout(PAGE_TIMEOUT_MS);
  // Block Clerk + analytics requests. The production Clerk key rejects localhost
  // and retries indefinitely, which prevents networkidle0 from resolving and slows
  // every prerender. We don't need auth to render public pages.
  await page.setRequestInterception(true);
  page.on('request', (req) => {
    const url = req.url();
    if (/clerk\.(com|infrasketch\.net|accounts\.dev)|stripe\.com|google-analytics|googletagmanager|api\.producthunt\.com|api\.foundrlist\.com|cdn-b\.saashub\.com|tinylaunch\.com|peerpush\.net|trylaunch\.ai|nxgntools\.com|launchigniter\.com/.test(url)) {
      return req.abort();
    }
    return req.continue();
  });
  try {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
    // Wait for Helmet to set a non-default title.
    await page.waitForFunction(
      () => document.title && document.title !== 'InfraSketch' && !/^Loading/i.test(document.title),
      { timeout: PAGE_TIMEOUT_MS }
    );
    if (isBlogPost(route)) {
      await page.waitForSelector('.blog-post-content', { timeout: PAGE_TIMEOUT_MS });
    }
    // Brief settle so Helmet finishes injecting canonical + og:* alongside title.
    await new Promise((r) => setTimeout(r, 300));
    const html = await page.content();
    const errs = validate(html, route);
    if (errs.length) {
      throw new Error(`prerender validation failed: ${errs.join(', ')}`);
    }
    const out = outputPathFor(route);
    await mkdir(path.dirname(out), { recursive: true });
    await writeFile(out, html, 'utf8');
    console.log(`  ok  ${route}  -> ${path.relative(DIST, out)}  (${html.length} bytes)`);
  } catch (err) {
    console.error(`  FAIL ${route}: ${err.message}`);
    throw err;
  } finally {
    await page.close();
  }
}

async function runPass(browser, routes, concurrency) {
  const limit = pLimit(concurrency);
  const failures = [];
  await Promise.all(
    routes.map((route) =>
      limit(async () => {
        try {
          await prerenderRoute(browser, route);
        } catch (err) {
          failures.push({ route, err });
        }
      })
    )
  );
  return failures;
}

async function main() {
  const routes = await getRoutes();
  console.log(`[prerender] ${routes.length} routes (concurrency ${CONCURRENCY})`);

  console.log('[prerender] starting vite preview...');
  const vite = await startVitePreview();
  await waitForReady(ORIGIN);
  console.log('[prerender] vite preview ready');

  const browser = await puppeteer.launch({ headless: 'new' });
  let failures = [];
  try {
    failures = await runPass(browser, routes, CONCURRENCY);

    // Retry flaky failures sequentially (concurrency 1) to rule out
    // resource contention as the cause of Puppeteer waitFor timeouts.
    const MAX_RETRIES = 2;
    for (let attempt = 1; attempt <= MAX_RETRIES && failures.length; attempt++) {
      const retryRoutes = failures.map((f) => f.route);
      console.log(
        `[prerender] retry pass ${attempt}/${MAX_RETRIES} for ${retryRoutes.length} route(s) (sequential)`
      );
      failures = await runPass(browser, retryRoutes, 1);
    }
  } finally {
    await browser.close();
    vite.kill('SIGTERM');
  }

  if (failures.length) {
    console.error(`[prerender] ${failures.length} route(s) failed after retries`);
    for (const { route, err } of failures) {
      console.error(`  ${route}: ${err.message}`);
    }
    process.exit(1);
  }
  console.log(`[prerender] done: ${routes.length} routes prerendered`);
}

main().catch((err) => {
  console.error('[prerender] fatal:', err);
  process.exit(1);
});
