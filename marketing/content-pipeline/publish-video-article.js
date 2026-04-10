#!/usr/bin/env node
/**
 * Publish a Dev.to article recapping the previous day's video content.
 *
 * Reads the content calendar and Upload-Post results to generate an article
 * with links to all 7 platform videos, then posts it to Dev.to.
 *
 * Usage:
 *   node publish-video-article.js              # Auto-calculates yesterday's day number
 *   node publish-video-article.js --day 1      # Override day number
 *   node publish-video-article.js --dry-run    # Generate article but skip posting
 *
 * Environment (loaded from .env):
 *   ANTHROPIC_API_KEY, DEVTO_API_KEY, UPLOAD_POST_API_KEY
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load .env
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx > 0) {
      const key = trimmed.slice(0, eqIdx);
      const val = trimmed.slice(eqIdx + 1);
      if (!process.env[key]) process.env[key] = val;
    }
  }
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const START_DATE = '2026-04-07'; // Day 1
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const DEVTO_API_KEY = process.env.DEVTO_API_KEY;
const UPLOAD_POST_API_KEY = process.env.UPLOAD_POST_API_KEY;

// ---------------------------------------------------------------------------
// Parse args
// ---------------------------------------------------------------------------
const args = process.argv.slice(2);
let dayNumber = null;
let dryRun = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--day') { dayNumber = parseInt(args[++i], 10); }
  else if (args[i] === '--dry-run') { dryRun = true; }
}

// Default to yesterday's day number
if (dayNumber === null) {
  const startEpoch = new Date(START_DATE + 'T00:00:00Z').getTime();
  const now = new Date();
  // Yesterday in UTC
  const yesterday = new Date(now.getTime() - 86400000);
  const yesterdayStr = yesterday.toISOString().slice(0, 10);
  const yesterdayEpoch = new Date(yesterdayStr + 'T00:00:00Z').getTime();
  dayNumber = Math.floor((yesterdayEpoch - startEpoch) / 86400000) + 1;
}

if (dayNumber < 1 || dayNumber > 365) {
  console.error(`Day ${dayNumber} is outside the 1-365 range`);
  process.exit(1);
}

console.log(`=== Video Article Publisher - Day ${dayNumber} ===`);
console.log(`Dry run: ${dryRun}`);

// ---------------------------------------------------------------------------
// CSV parser (handles quoted fields with commas/newlines)
// ---------------------------------------------------------------------------
function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
      } else if (ch === ',') {
        row.push(field);
        field = '';
      } else if (ch === '\n' || (ch === '\r' && text[i + 1] === '\n')) {
        row.push(field);
        field = '';
        if (row.length > 1) rows.push(row);
        row = [];
        if (ch === '\r') i++;
      } else {
        field += ch;
      }
    }
  }
  // Last field/row
  if (field || row.length > 0) {
    row.push(field);
    if (row.length > 1) rows.push(row);
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Step 1: Read content calendar
// ---------------------------------------------------------------------------
console.log('\nStep 1: Reading content calendar...');
const calendarPath = path.join(__dirname, 'content-calendar.csv');
const calendarText = fs.readFileSync(calendarPath, 'utf8');
const calendarRows = parseCSV(calendarText);
const headers = calendarRows[0];

// Find the row for the target day
const dayIdx = headers.indexOf('Day');
const dateIdx = headers.indexOf('Date');
const categoryIdx = headers.indexOf('Category');
const titleIdx = headers.indexOf('Diagram Title');
const promptIdx = headers.indexOf('Step 1: Generation Prompt');
const questionIdx = headers.indexOf('Step 3: Chat Question');
const hashtagsIdx = headers.indexOf('Hashtags');
const difficultyIdx = headers.indexOf('Difficulty');

const dayRow = calendarRows.find(r => parseInt(r[dayIdx], 10) === dayNumber);
if (!dayRow) {
  console.error(`Day ${dayNumber} not found in content calendar`);
  process.exit(1);
}

const calendarDate = dayRow[dateIdx];
const category = dayRow[categoryIdx];
const title = dayRow[titleIdx];
const prompt = dayRow[promptIdx];
const chatQuestion = dayRow[questionIdx];
const hashtags = dayRow[hashtagsIdx];
const difficulty = dayRow[difficultyIdx];

console.log(`  Title: ${title}`);
console.log(`  Date: ${calendarDate}`);
console.log(`  Category: ${category}`);

// ---------------------------------------------------------------------------
// Step 2: Find output directory and upload result
// ---------------------------------------------------------------------------
console.log('\nStep 2: Finding upload results...');
const outputBase = path.join(__dirname, 'output');
const outputDirs = fs.readdirSync(outputBase).filter(d => d.startsWith(calendarDate));

let uploadResult = null;
let outputDir = null;

for (const dir of outputDirs) {
  const resultPath = path.join(outputBase, dir, 'upload-result.json');
  if (fs.existsSync(resultPath)) {
    uploadResult = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
    outputDir = path.join(outputBase, dir);
    break;
  }
}

if (!uploadResult) {
  console.error(`No upload-result.json found for date ${calendarDate} in ${outputBase}`);
  console.error(`Available directories: ${outputDirs.join(', ') || 'none'}`);
  process.exit(1);
}

const requestId = uploadResult.request_id;
console.log(`  Output dir: ${outputDir}`);
console.log(`  Request ID: ${requestId}`);

// ---------------------------------------------------------------------------
// Step 3: Get platform URLs from Upload-Post status API
// ---------------------------------------------------------------------------
console.log('\nStep 3: Fetching platform URLs from Upload-Post...');

const statusUrl = `https://api.upload-post.com/api/uploadposts/status?request_id=${requestId}`;
const statusResp = await fetch(statusUrl, {
  headers: { 'Authorization': `Apikey ${UPLOAD_POST_API_KEY}` }
});

if (!statusResp.ok) {
  console.error(`Upload-Post status API failed: ${statusResp.status}`);
  process.exit(1);
}

const statusData = await statusResp.json();

if (statusData.status !== 'completed') {
  console.error(`Upload not yet completed (status: ${statusData.status})`);
  process.exit(1);
}

// Extract platform URLs (only successful ones)
const platformUrls = {};
const platformNames = {
  youtube: 'YouTube',
  tiktok: 'TikTok',
  instagram: 'Instagram',
  facebook: 'Facebook',
  x: 'X (Twitter)',
  threads: 'Threads',
  linkedin: 'LinkedIn'
};

for (const result of statusData.results || []) {
  if (result.success && result.url) {
    platformUrls[result.platform] = result.url;
    console.log(`  ${platformNames[result.platform] || result.platform}: ${result.url}`);
  }
}

const successCount = Object.keys(platformUrls).length;
console.log(`  ${successCount} platforms with URLs`);

if (successCount === 0) {
  console.error('No successful platform uploads found');
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Step 4: Generate article with Claude
// ---------------------------------------------------------------------------
console.log('\nStep 4: Generating article with Claude...');

// Build the watch links section
const watchLinks = Object.entries(platformUrls)
  .map(([platform, url]) => `- [${platformNames[platform] || platform}](${url})`)
  .join('\n');

const articlePrompt = `You are a technical writer creating a short, engaging Dev.to article about a system design topic. The article accompanies a video that shows AI generating an architecture diagram in real-time.

Topic: ${title}
Category: ${category}
System prompt used: ${prompt}
Follow-up question explored: ${chatQuestion}
Difficulty: ${difficulty}

Write a Dev.to article (500-800 words) with this structure:

1. **Hook** (2-3 sentences) - Why this architecture matters, what problem it solves
2. **Architecture Overview** (2-3 paragraphs) - Key components, how they connect, design decisions. Focus on concepts, not code.
3. **Design Insight** (1 paragraph) - Answer or expand on this question: "${chatQuestion}"
4. **Watch the Full Design Process** - Introduce the video links (provided below, do not make up URLs)
5. **Try It Yourself** - CTA for InfraSketch

Writing rules:
- Professional but approachable tone
- NO em-dashes, use commas or separate sentences instead
- NO code blocks (this is about architecture, not implementation)
- Use ## for main sections, ### for subsections
- Keep paragraphs to 3-4 sentences max
- Mention [InfraSketch](https://infrasketch.net) 2-3 times naturally
- This is Day ${dayNumber} of a 365-day system design challenge

For the "Watch the Full Design Process" section, use exactly these links:
${watchLinks}

End with a "## Try It Yourself" section with a call-to-action:
"Head over to [InfraSketch](https://infrasketch.net) and describe your system in plain English. In seconds, you'll have a professional architecture diagram, complete with a design document."

Write the article now in markdown. Do NOT include a title (Dev.to adds it separately). Start directly with the hook paragraph.`;

const claudeResp = await fetch('https://api.anthropic.com/v1/messages', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': ANTHROPIC_API_KEY,
    'anthropic-version': '2023-06-01'
  },
  body: JSON.stringify({
    model: 'claude-haiku-4-5-20251001',
    max_tokens: 4000,
    messages: [{ role: 'user', content: articlePrompt }]
  })
});

if (!claudeResp.ok) {
  const errText = await claudeResp.text();
  console.error(`Claude API failed (${claudeResp.status}): ${errText}`);
  process.exit(1);
}

const claudeData = await claudeResp.json();
let articleBody = claudeData.content[0].text;
const articleTitle = `Day ${dayNumber}: ${title} - AI System Design in Seconds`;

// Embed YouTube video at the top if available
if (platformUrls.youtube) {
  const ytMatch = platformUrls.youtube.match(/[?&]v=([^&]+)/);
  if (ytMatch) {
    articleBody = `{% youtube ${ytMatch[1]} %}\n\n${articleBody}`;
  }
}

console.log(`  Title: ${articleTitle}`);
console.log(`  Length: ${articleBody.length} chars`);

// ---------------------------------------------------------------------------
// Step 5: Post to Dev.to
// ---------------------------------------------------------------------------
if (dryRun) {
  console.log('\nDRY RUN: Skipping Dev.to publish');
  console.log('\n--- Article Preview ---');
  console.log(`Title: ${articleTitle}`);
  console.log(articleBody.slice(0, 500) + '...');

  // Save draft locally
  const draftPath = path.join(outputDir, 'devto-article-draft.md');
  fs.writeFileSync(draftPath, `# ${articleTitle}\n\n${articleBody}`);
  console.log(`\nDraft saved to: ${draftPath}`);
  process.exit(0);
}

console.log('\nStep 5: Publishing to Dev.to...');

// Derive tags from hashtags (max 4, normalized)
const tags = (hashtags || 'systemdesign,architecture,webdev,programming')
  .replace(/#/g, '')
  .split(/[\s,]+/)
  .filter(t => t.length > 0)
  .map(t => t.toLowerCase().replace(/[^a-z0-9]/g, ''))
  .filter(t => t.length > 0)
  .slice(0, 4);

const devtoPayload = {
  article: {
    title: articleTitle,
    body_markdown: articleBody,
    published: true,
    tags: tags,
    series: 'AI System Design in Seconds - 365 Day Challenge',
    main_image: 'https://infrasketch.net/full-app-with-design-doc.png'
  }
};

const devtoResp = await fetch('https://dev.to/api/articles', {
  method: 'POST',
  headers: {
    'api-key': DEVTO_API_KEY,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(devtoPayload)
});

if (!devtoResp.ok) {
  const errText = await devtoResp.text();
  console.error(`Dev.to API failed (${devtoResp.status}): ${errText}`);
  process.exit(1);
}

const devtoData = await devtoResp.json();
console.log(`  Published: ${devtoData.url}`);
console.log(`  Article ID: ${devtoData.id}`);

// Save result
const resultPath = path.join(outputDir, 'devto-article-result.json');
fs.writeFileSync(resultPath, JSON.stringify({
  day: dayNumber,
  title: articleTitle,
  devto_id: devtoData.id,
  devto_url: devtoData.url,
  platforms: platformUrls,
  published_at: new Date().toISOString()
}, null, 2));

console.log(`\n=== Article published for Day ${dayNumber} ===`);
console.log(`  Dev.to: ${devtoData.url}`);
console.log(`  Result saved: ${resultPath}`);
