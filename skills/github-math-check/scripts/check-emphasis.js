#!/usr/bin/env node
// Find plain-text formulas that GitHub turns into italics.
//
//   node check-emphasis.js FILE.md|DIR ...
//
// A formula written as plain text (not math, not code) is Markdown to GitHub:
// `psi(W^(W*w)) = psi(W^2*w)` renders as `psi(W^(W<em>w)) = psi(W^2</em>w)`.
// For every table cell (or every other line) this reports a `*` or `_` that can open
// emphasis followed by one of the same kind that can close it, by the CommonMark
// flanking rules. Ignored: code spans, fenced code blocks, escaped \* \_, and runs of two
// or more (`**bold**`, `__x__`), which are almost always intended.
// Not detected: emphasis that runs across a line break inside one paragraph.
'use strict';
const fs = require('fs');
const path = require('path');

const files = [];
for (const a of process.argv.slice(2)) {
  if (fs.statSync(a).isDirectory()) {
    for (const f of fs.readdirSync(a)) if (f.endsWith('.md')) files.push(path.join(a, f));
  } else files.push(a);
}
if (!files.length) {
  console.error('usage: check-emphasis.js FILE.md|DIR ...');
  process.exit(2);
}

const ws = c => /\s/u.test(c);
const pu = c => /[\p{P}\p{S}]/u.test(c);

// true if some delimiter can open emphasis and a later one of the same kind can close it
function risky(text) {
  const t = [...text];
  const open = { '*': false, '_': false };
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (c !== '*' && c !== '_') continue;
    if (t[i - 1] === '\\') continue;                       // escaped
    if (t[i - 1] === c || t[i + 1] === c) continue;        // ** or __ run
    const prev = i > 0 ? t[i - 1] : ' ';
    const next = i + 1 < t.length ? t[i + 1] : ' ';
    const left = !ws(next) && (!pu(next) || ws(prev) || pu(prev));
    const right = !ws(prev) && (!pu(prev) || ws(next) || pu(next));
    const canOpen = c === '*' ? left : left && (!right || pu(prev));
    const canClose = c === '*' ? right : right && (!left || pu(next));
    if (open[c] && canClose) return true;
    if (canOpen) open[c] = true;
  }
  return false;
}

let bad = 0;
for (const f of files) {
  let fence = false;
  fs.readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
    if (/^ {0,3}(```|~~~)/.test(line)) { fence = !fence; return; }
    if (fence) return;
    const s = line.replace(/(`+)[\s\S]*?\1/g, 'x')           // code spans are safe
      .replace(/^\s*(>\s*)*([-*+]|\d+[.)])\s+/, '')           // list marker, blockquote
      .replace(/^\s*#+\s/, '');                               // heading marker
    const parts = /^\s*\|/.test(line) ? s.split(/(?<!\\)\|/) : [s];
    if (parts.some(risky)) {
      bad++;
      console.log(`${f}:${i + 1}: ${line.length > 120 ? line.slice(0, 117) + '...' : line}`);
    }
  });
}
console.log(`files : ${files.length}`);
console.log(`errors: ${bad}`);
process.exit(bad ? 1 : 0);
