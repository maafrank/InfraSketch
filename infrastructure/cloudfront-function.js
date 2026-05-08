// CloudFront Function (viewer-request) for distribution E2YM028NUBX2QN.
//
// Responsibilities:
//   1. 301 redirect from www.infrasketch.net to https://infrasketch.net (apex),
//      preserving the path and query string. Fixes the "Page with redirect"
//      issue Google Search Console reported.
//   2. Rewrite extensionless paths (e.g., /blog/foo) to /blog/foo/index.html so
//      CloudFront fetches the prerendered file directly. Without this rewrite,
//      the S3 website origin returns a 302 to add the trailing slash, which
//      Google reports as "Page with redirect".

function handler(event) {
  var req = event.request;
  var hostHeader = req.headers && req.headers.host;
  var host = hostHeader && hostHeader.value;

  // 1) www -> apex 301
  if (host === 'www.infrasketch.net') {
    var qs = '';
    if (req.querystring) {
      var parts = [];
      for (var k in req.querystring) {
        if (Object.prototype.hasOwnProperty.call(req.querystring, k)) {
          parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(req.querystring[k].value));
        }
      }
      if (parts.length) qs = '?' + parts.join('&');
    }
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: {
        'location': { value: 'https://infrasketch.net' + req.uri + qs },
        'cache-control': { value: 'max-age=3600' }
      }
    };
  }

  // 2) URI rewrite: directory paths -> <dir>/index.html
  var uri = req.uri;
  if (uri.endsWith('/')) {
    req.uri = uri + 'index.html';
  } else {
    // No trailing slash. If the last segment has no file extension, treat as a
    // directory and append /index.html. Skip if it already points at a file
    // (e.g., /sitemap.xml, /robots.txt, /assets/foo.js, /og-image.png).
    var lastSlash = uri.lastIndexOf('/');
    var lastSegment = uri.slice(lastSlash + 1);
    if (lastSegment.indexOf('.') === -1) {
      req.uri = uri + '/index.html';
    }
  }

  return req;
}
