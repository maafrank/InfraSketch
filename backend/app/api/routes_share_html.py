"""Server-rendered surfaces for share links.

Mounted at the ROOT (no /api prefix), because the shareable URL is
infrasketch.net/share/{token}. A CloudFront behavior for /share/* routes those
paths to API Gateway instead of the S3 bucket.

Why server-rendered at all: the site is prerendered at build time and served
from S3, so a dynamic share page cannot get per-diagram meta tags that way.
Google renders JS and would eventually index a client-only page, but Slack,
X, and LinkedIn read the raw HTML, so an unfurled share link would show the
generic site preview. These routes fix that.
"""

import html
import logging
import os
import time
from typing import Optional
from xml.sax.saxutils import escape as xml_escape

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from app.session.manager import session_manager
from app.utils.diagram_export import generate_diagram_png

logger = logging.getLogger(__name__)
router = APIRouter()

SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://infrasketch.net")
SHELL_CACHE_TTL_SECONDS = 300

# Cached copy of the deployed index.html. Fetching the live shell instead of
# templating our own means the hashed Vite asset filenames stay correct across
# frontend deploys with no coordination between the two.
_shell_cache: Optional[str] = None
_shell_cache_at: float = 0.0


def _fetch_app_shell() -> Optional[str]:
    """Fetch and cache the deployed index.html."""
    global _shell_cache, _shell_cache_at

    if _shell_cache and (time.time() - _shell_cache_at) < SHELL_CACHE_TTL_SECONDS:
        return _shell_cache

    try:
        response = requests.get(f"{SITE_URL}/index.html", timeout=5)
        response.raise_for_status()
        _shell_cache = response.text
        _shell_cache_at = time.time()
        return _shell_cache
    except Exception as e:
        logger.warning(f"share: could not fetch app shell: {e}")
        # Serve a stale shell rather than nothing. Old asset hashes still
        # resolve on CloudFront for a while after a deploy.
        return _shell_cache


def _strip_tag(markup: str, needle: str) -> str:
    """Remove every <meta>/<link> tag whose text contains `needle`.

    The prerendered shell already carries landing-page OG tags; leaving them in
    alongside ours would give scrapers two competing values for the same
    property, and which one wins is scraper-dependent.
    """
    out = []
    cursor = 0
    while True:
        start = markup.find("<", cursor)
        if start == -1:
            out.append(markup[cursor:])
            break
        end = markup.find(">", start)
        if end == -1:
            out.append(markup[cursor:])
            break
        tag = markup[start:end + 1]
        out.append(markup[cursor:start])
        if needle not in tag:
            out.append(tag)
        cursor = end + 1
    return "".join(out)


def _build_meta(session, token: str) -> str:
    """Per-diagram title, description, OG/Twitter tags, and JSON-LD."""
    name = session.name or "Untitled Design"
    nodes = session.diagram.nodes if session.diagram else []
    components = ", ".join(n.label for n in nodes[:6] if n.label)

    title = f"{name} - Architecture Diagram | InfraSketch"
    description = (
        f"{name}: a system architecture with {len(nodes)} components"
        + (f" including {components}." if components else ".")
        + " Built with InfraSketch."
    )

    canonical = f"{SITE_URL}/share/{token}"
    image = f"{SITE_URL}/share/{token}/preview.png"

    e = html.escape
    return f"""<title>{e(title)}</title>
<meta name="description" content="{e(description)}" />
<link rel="canonical" href="{e(canonical)}" />
<meta property="og:type" content="article" />
<meta property="og:title" content="{e(title)}" />
<meta property="og:description" content="{e(description)}" />
<meta property="og:url" content="{e(canonical)}" />
<meta property="og:image" content="{e(image)}" />
<meta property="og:site_name" content="InfraSketch" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{e(title)}" />
<meta name="twitter:description" content="{e(description)}" />
<meta name="twitter:image" content="{e(image)}" />
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"CreativeWork","name":{_json_str(name)},"description":{_json_str(description)},"url":{_json_str(canonical)},"image":{_json_str(image)},"isAccessibleForFree":true}}
</script>"""


def _json_str(value: str) -> str:
    """JSON-encode a string for embedding in a JSON-LD block."""
    import json
    return json.dumps(value)


# Declared BEFORE /share/{token}: FastAPI matches routes in declaration order,
# so with the token route first, "sitemap.xml" is captured as a token and the
# sitemap 404s. Same hazard as /nodes/positions vs /nodes/{node_id}.
@router.get("/share/sitemap.xml")
async def share_sitemap():
    """Sitemap of publicly shared diagrams.

    Served here rather than baked into the build-time sitemap because shares are
    created continuously and the frontend is deployed rarely. Lives under
    /share/ so it is covered by the same CloudFront behavior.
    """
    sessions = session_manager.list_public_sessions(limit=5000)

    urls = []
    for session in sessions:
        if not session.share_token:
            continue
        lastmod = ""
        if session.shared_at:
            lastmod = f"<lastmod>{session.shared_at.date().isoformat()}</lastmod>"
        urls.append(
            f"<url><loc>{xml_escape(SITE_URL)}/share/{xml_escape(session.share_token)}</loc>"
            f"{lastmod}<changefreq>weekly</changefreq><priority>0.5</priority></url>"
        )

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )

    return Response(
        content=body,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/share/{token}", response_class=HTMLResponse)
async def shared_diagram_page(token: str):
    """HTML shell for a shared diagram, with per-diagram meta tags."""
    session = session_manager.get_session_by_share_token(token)
    if not session:
        raise HTTPException(status_code=404, detail="This diagram is not shared or the link has expired")

    shell = _fetch_app_shell()
    if not shell:
        raise HTTPException(status_code=503, detail="Temporarily unable to render this page")

    markup = shell
    for needle in ('property="og:', 'name="twitter:', 'rel="canonical"', 'name="description"'):
        markup = _strip_tag(markup, needle)

    # Replace the prerendered <title> rather than adding a second one.
    title_start = markup.find("<title")
    if title_start != -1:
        title_end = markup.find("</title>", title_start)
        if title_end != -1:
            markup = markup[:title_start] + markup[title_end + len("</title>"):]

    meta = _build_meta(session, token)
    if "</head>" in markup:
        markup = markup.replace("</head>", f"{meta}\n</head>", 1)
    else:
        markup = meta + markup

    # Empty the root element. main.jsx branches on rootElement.hasChildNodes():
    # any content (including whitespace) sends it down hydrateRoot against the
    # prerendered landing page, which is not what this route renders. There must
    # be no whitespace between the tags.
    root_start = markup.find('<div id="root"')
    if root_start != -1:
        open_end = markup.find(">", root_start)
        close_start = markup.find("</div>", open_end)
        if open_end != -1 and close_start != -1:
            markup = markup[:open_end + 1] + markup[close_start:]

    return HTMLResponse(
        content=markup,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/share/{token}/preview.png")
async def shared_diagram_preview(token: str):
    """OG image for a shared diagram, rendered server-side with Pillow."""
    session = session_manager.get_session_by_share_token(token)
    if not session:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        png = generate_diagram_png(session.diagram.model_dump())
    except Exception as e:
        logger.exception(f"share: failed to render preview for {token}: {e}")
        raise HTTPException(status_code=500, detail="Could not render a preview")

    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
