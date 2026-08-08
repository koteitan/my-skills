#!/usr/bin/env node
// Check EVERY formula of a Markdown file as GitHub actually delivers it.
//
//   node check-github.js https://github.com/OWNER/REPO/blob/BRANCH/path/to/File.md
//   node check-github.js OWNER/REPO BRANCH path/to/File.md
//
// It fetches the live blob page, decodes the embedded JSON payload, pulls out every
// <math-renderer> body — that is the exact string GitHub hands to the client-side
// renderer — and renders each one with KaTeX, the same engine the browser uses.
//
// This is the only check that catches GitHub's own transformations, e.g. \\ arriving
// as \\\ (which breaks \begin{aligned} and yields "Missing \end{aligned}").
//
// Requires katex:  npm install -g katex   (or run with NODE_PATH=<dir with katex>)

let katex;
try { katex = require('katex'); }
catch { console.error('katex not found. Try: npm install -g katex   (or NODE_PATH=<dir> node ...)'); process.exit(2); }

const args = process.argv.slice(2);
if (args.length === 0) { console.error('usage: check-github.js <blob URL> | <owner/repo> <branch> <path>'); process.exit(2); }
const url = args.length === 1
  ? args[0]
  : `https://github.com/${args[0]}/blob/${args[1]}/${args[2]}`;

const unescapeHtml = (s) => s
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
  .replace(/&#39;/g, "'").replace(/&#x27;/g, "'").replace(/&nbsp;/g, ' ')
  .replace(/&amp;/g, '&');            // last, so &amp;lt; survives as &lt;

(async () => {
  // Ask for the JSON payload: the HTML page truncates `richText` for large files
  // (richTextTruncated: true, richText: null), the JSON response never does.
  const res = await fetch(`${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`, {
    headers: { Accept: 'application/json', 'Cache-Control': 'no-cache' },
  });
  if (!res.ok) { console.error(`fetch failed: ${res.status} ${res.statusText}`); process.exit(2); }
  const data = await res.json();
  const route = (data.payload || {}).codeViewBlobRoute || {};
  const rich = route.richText;

  console.log(`url      : ${url}`);
  if (route.richTextTruncated) console.error('warning: GitHub reports richText as truncated');
  if (!rich) { console.error('no rendered content in the payload (is the file Markdown?)'); process.exit(2); }

  const items = [];
  for (const m of rich.matchAll(/<math-renderer[^>]*class="([^"]*)"[^>]*>([\s\S]*?)<\/math-renderer>/g)) {
    const display = m[1].includes('display-math');
    let body = unescapeHtml(m[2]).trim();
    if (body.startsWith('$$') && body.endsWith('$$')) body = body.slice(2, -2);
    else if (body.startsWith('$') && body.endsWith('$')) body = body.slice(1, -1);
    items.push({ display, body });
  }

  let bad = 0;
  const show = [];
  for (const it of items) {
    const corrupt = /\\\\\\(?!\\)/.test(it.body);   // the \\ -> \\\ transformation
    let err = null;
    try { katex.renderToString(it.body, { displayMode: it.display, throwOnError: true, strict: false }); }
    catch (e) { err = e.message; }
    if (err || corrupt) {
      bad++;
      if (show.length < 8) show.push({
        kind: it.display ? 'display' : 'inline',
        why: corrupt ? 'GitHub delivered \\\\\\ (row break corrupted — write \\cr instead)' : err,
        head: it.body.replace(/\n/g, ' ⏎ ').slice(0, 110),
      });
    }
  }

  console.log(`formulas : ${items.length} (${items.filter(i => i.display).length} display, ${items.filter(i => !i.display).length} inline)`);
  console.log(`errors   : ${bad}`);
  for (const s of show) console.log(`\n  [${s.kind}] ${s.why}\n    ${s.head}`);
  process.exit(bad ? 1 : 0);
})();
