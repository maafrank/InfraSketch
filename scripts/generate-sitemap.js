#!/usr/bin/env node
// Regenerate frontend/public/sitemap.xml from blog/posts/index.json + a static
// route list. Wired into the build via the `prebuild` npm script in
// frontend/package.json. Vite copies public/sitemap.xml into dist on build.

import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const SITE = 'https://infrasketch.net';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const POSTS_INDEX = path.join(REPO_ROOT, 'frontend/public/blog/posts/index.json');
const SITEMAP_PATH = path.join(REPO_ROOT, 'frontend/public/sitemap.xml');

const TODAY = new Date().toISOString().slice(0, 10);

const STATIC_ROUTES = [
  { loc: '/', priority: '1.0', changefreq: 'weekly' },
  { loc: '/blog', priority: '0.9', changefreq: 'weekly' },
  { loc: '/compare', priority: '0.9', changefreq: 'monthly' },
  { loc: '/about', priority: '0.8', changefreq: 'monthly' },
  { loc: '/pricing', priority: '0.8', changefreq: 'monthly' },
  { loc: '/contact', priority: '0.5', changefreq: 'monthly' },
  { loc: '/careers', priority: '0.4', changefreq: 'monthly' },
  { loc: '/privacy', priority: '0.3', changefreq: 'yearly' },
  { loc: '/terms', priority: '0.3', changefreq: 'yearly' },
  { loc: '/tools', priority: '0.9', changefreq: 'monthly' },
  { loc: '/tools/system-design-tool', priority: '1.0', changefreq: 'monthly' },
  { loc: '/tools/ai-diagram-generator', priority: '1.0', changefreq: 'monthly' },
  { loc: '/tools/architecture-diagram-tool', priority: '1.0', changefreq: 'monthly' },
  { loc: '/tools/design-doc-generator', priority: '1.0', changefreq: 'monthly' },
  { loc: '/tools/ml-system-design-tool', priority: '1.0', changefreq: 'monthly' },
  { loc: '/tools/llm-architecture-tool', priority: '1.0', changefreq: 'monthly' },
  { loc: '/compare/eraser', priority: '0.9', changefreq: 'monthly' },
  { loc: '/compare/lucidchart', priority: '0.9', changefreq: 'monthly' },
  { loc: '/compare/system-design-primer', priority: '0.9', changefreq: 'monthly' },
  { loc: '/compare/bytebytego', priority: '0.9', changefreq: 'monthly' },
  { loc: '/compare/mermaid', priority: '0.9', changefreq: 'monthly' },
  { loc: '/compare/draw-io', priority: '0.9', changefreq: 'monthly' },
  { loc: '/compare/whimsical', priority: '0.9', changefreq: 'monthly' },
  { loc: '/compare/chatgpt', priority: '0.9', changefreq: 'monthly' },
];

function urlEntry({ loc, lastmod, priority, changefreq, image }) {
  const lines = [
    '  <url>',
    `    <loc>${SITE}${loc}</loc>`,
    `    <lastmod>${lastmod}</lastmod>`,
    `    <priority>${priority}</priority>`,
    `    <changefreq>${changefreq}</changefreq>`,
  ];
  if (image) {
    lines.push(
      '    <image:image>',
      `      <image:loc>${image.loc}</image:loc>`,
      `      <image:title>${image.title}</image:title>`,
      '    </image:image>'
    );
  }
  lines.push('  </url>');
  return lines.join('\n');
}

async function main() {
  const raw = await readFile(POSTS_INDEX, 'utf8');
  const { posts } = JSON.parse(raw);

  const homepageImage = {
    loc: `${SITE}/full-app-with-design-doc.png`,
    title: 'InfraSketch AI System Design Tool Screenshot',
  };

  const staticEntries = STATIC_ROUTES.map((r) =>
    urlEntry({
      ...r,
      lastmod: TODAY,
      image: r.loc === '/' ? homepageImage : undefined,
    })
  );

  const blogEntries = posts.map((p) =>
    urlEntry({
      loc: `/blog/${p.slug}`,
      lastmod: p.date,
      priority: '0.9',
      changefreq: 'monthly',
    })
  );

  const xml =
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n` +
    `        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n` +
    [...staticEntries, ...blogEntries].join('\n') +
    `\n</urlset>\n`;

  await writeFile(SITEMAP_PATH, xml, 'utf8');
  console.log(
    `[generate-sitemap] wrote ${SITEMAP_PATH} (${STATIC_ROUTES.length} static + ${posts.length} blog = ${STATIC_ROUTES.length + posts.length} URLs)`
  );
}

main().catch((err) => {
  console.error('[generate-sitemap] failed:', err);
  process.exit(1);
});
