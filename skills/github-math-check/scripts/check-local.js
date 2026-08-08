#!/usr/bin/env node
// Local pre-check of Markdown math, before pushing.
//
//   node check-local.js FILE.md [FILE2.md ...]
//   node check-local.js DIR            (checks every *.md in it)
//
// Checks, per file:
//   1. every ```math fence and every $`...`$ renders under KaTeX (GitHub's engine);
//   2. no bare $...$  — GitHub escapes its contents (\{x\} -> {x}, \, -> a comma);
//   3. no \\ row break — GitHub delivers it as \\\ , which breaks \begin{aligned};
//   4. no bare < or > inside inline math — GitHub delivers them as &amp;lt; ;
//      and no $ inside \text{...} — GitHub escapes it to \$ ;
//   5. every ```math fence is closed.
//
// Green here is necessary but not sufficient: it does not reproduce GitHub's own
// transformations. Run scripts/check-github.js on the pushed file as well.
//
// Requires katex:  npm install -g katex   (or run with NODE_PATH=<dir with katex>)

let katex;
try { katex = require('katex'); }
catch { console.error('katex not found. Try: npm install -g katex   (or NODE_PATH=<dir> node ...)'); process.exit(2); }

const fs = require('fs'), path = require('path');
let args = process.argv.slice(2);
if (args.length === 0) args = ['.'];
const files = [];
for (const a of args) {
  // The braces matter: without them `else` binds to the inner `if`, and a
  // plain file argument is silently dropped (0 files checked, exit 0).
  if (fs.existsSync(a) && fs.statSync(a).isDirectory()) {
    for (const f of fs.readdirSync(a).sort()) {
      if (f.endsWith('.md')) files.push(path.join(a, f));
    }
  } else {
    files.push(a);
  }
}

let total = 0, bad = 0;
for (const f of files) {
  const src = fs.readFileSync(f, 'utf8');
  const lines = src.split('\n');
  const errs = [];
  const rest = [];
  const mathText = [];
  let i = 0, openFence = -1;

  while (i < lines.length) {
    const s = lines[i].trim();
    if (s.startsWith('```')) {
      const isMath = s === '```math';
      const start = i; let j = i + 1; const body = [];
      while (j < lines.length && lines[j].trim() !== '```') body.push(lines[j++]);
      if (j >= lines.length) { errs.push([start + 1, 'unclosed ``` fence']); openFence = start; break; }
      if (isMath) {
        total++;
        mathText.push(body.join('\n'));
        try { katex.renderToString(body.join('\n'), { displayMode: true, throwOnError: true, strict: false }); }
        catch (e) { errs.push([start + 1, 'display: ' + e.message.slice(0, 70)]); }
        // GitHub escapes $ to \$ even inside a fence, so any $ in math content breaks it
        body.forEach((b, k) => { if (b.includes('$')) errs.push([start + 2 + k, '$ inside math — remove it (\\tag{$x$} -> \\tag{x}, \\text{$x$} -> pull x out)']); });
      }
      for (let k = start; k <= j; k++) rest.push('');
      i = j + 1; continue;
    }
    rest.push(lines[i]); i++;
  }

  const outside = rest.join('\n');
  for (const m of outside.matchAll(/\$`([^`]+)`\$/g)) {
    total++;
    const at = outside.slice(0, m.index).split('\n').length;
    mathText.push(m[1]);
    try { katex.renderToString(m[1], { displayMode: false, throwOnError: true, strict: false }); }
    catch (e) { errs.push([at, 'inline: ' + e.message.slice(0, 70)]); }
    if (m[1].includes('\n')) errs.push([at, 'inline formula spans a line break']);
  }

  const stray = outside.replace(/\$`[^`]+`\$/g, '');
  const strayLines = stray.split('\n');
  strayLines.forEach((l, n) => {
    const c = (l.match(/(?<!\\)\$/g) || []).length;
    if (c) errs.push([n + 1, `bare $ x${c} — write inline math as $\`...\`$`]);
  });

  const rows = [...src.matchAll(/\\\\(?!\\)/g)];
  if (rows.length) errs.push([src.slice(0, rows[0].index).split('\n').length, `\\\\ x${rows.length} — write row breaks as \\cr`]);

  // < and > are delivered double-escaped inside inline math (&amp;lt;), which KaTeX
  // cannot read; \lt and \gt pass through. Display fences are fine either way.
  const lt = [...outside.matchAll(/\$`[^`]*[<>][^`]*`\$/g)];
  if (lt.length) errs.push([outside.slice(0, lt[0].index).split('\n').length, `< or > in inline math x${lt.length} — write \\lt / \\gt`]);

  // GitHub escapes $ to \$ even inside a ```math fence, so \text{$x$} arrives as
  // \text{\$x\$} and KaTeX then refuses the math-mode commands inside it.
  for (const m of outside.matchAll(/\$`([^`]+)`\$/g))
    if (m[1].includes('$')) errs.push([outside.slice(0, m.index).split('\n').length, '$ inside inline math']);

  // GitHub runs KaTeX behind a macro allowlist of its own, and rejects the whole
  // formula with "The following macros are not allowed: <name>". Plain KaTeX accepts
  // them, so this is invisible to the render above and to check-github.js — the
  // rejection happens in the browser, not in the delivered string. Avoid them.
  const BANNED = ['hphantom', 'phantom', 'vphantom', 'smash', 'def', 'gdef', 'edef',
    'xdef', 'let', 'newcommand', 'renewcommand', 'providecommand', 'global',
    'htmlClass', 'htmlId', 'htmlStyle', 'htmlData', 'includegraphics'];
  for (const name of BANNED) {
    const re = new RegExp('\\\\' + name + '(?![A-Za-z])', 'g');
    const n = mathText.reduce((a, t) => a + (t.match(re) || []).length, 0);
    if (n) {
      const hit = src.match(re);
      errs.push([src.slice(0, src.indexOf(hit[0])).split('\n').length,
        `\\${name} x${n} — GitHub's KaTeX does not allow this macro`]);
    }
  }

  // GitHub never builds a math element inside a link: [$`x`$](u) is delivered as
  // $<code>x</code>$, which shows as literal code, and if another formula follows in
  // the same paragraph their $ delimiters mispair into one broken expression.
  const inLink = [...src.matchAll(/(?<!`)\[\$`/g)];
  if (inLink.length) errs.push([src.slice(0, inLink[0].index).split('\n').length,
    `math inside a link x${inLink.length} — put the link after the formula`]);

  // GitHub renders a page's math only until a cost budget runs out, then turns
  // every remaining formula into "Unable to render expression". Measured: 1200 tiny
  // formulas (6096 chars of math source) all render; 140-char formulas stop at the
  // 181st (25956 chars); a real file stopped at 28588. The budget is not a formula
  // count, and if it is a time budget the boundary moves with the reader's machine,
  // so warn well below it.
  let mathChars = 0;
  for (const t of mathText) mathChars += t.length + 2;
  if (mathChars > 20000) errs.push([1,
    `math source ${mathChars} chars — over the 20000 budget; GitHub will stop rendering partway (split the file)`]);

  if (errs.length) {
    bad += errs.length;
    console.log(`\n=== ${f}: ${errs.length} ===`);
    for (const e of errs.slice(0, 8)) console.log(`  L${e[0]}: ${e[1]}`);
  }
}
console.log(`\nfiles: ${files.length}, formulas: ${total}, problems: ${bad}`);
process.exit(bad ? 1 : 0);
