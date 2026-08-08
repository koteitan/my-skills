---
name: github-math-check
description: Verify that math in a Markdown file actually renders on GitHub. Use when a formula renders locally (KaTeX/MathJax/VS Code) but breaks on github.com — "Missing \end{aligned}", vanished braces, stray commas — or before publishing math-heavy Markdown. Decodes the exact string GitHub hands to its client-side renderer, so the check is measurement, not guesswork.
---

# github-math-check

**Rendering math locally proves nothing about GitHub.** GitHub transforms the math text
on its way to the client-side renderer, and the transformed string is what fails. Always
measure the delivered string.

## Known transformations (measured on live pages, 2026-07)

| written in the file | delivered to the renderer | effect |
|---|---|---|
| `\\` (row break) | `\\\` | `\begin{aligned}` rows merge → **`Missing \end{aligned}`** |
| `\\\\` | `\\\` | same |
| `\cr`, `\newline` | unchanged | ✅ use these for row breaks |
| `$\{x\}$` | `${x}$` | braces vanish (Markdown ate the escape) |
| `` $`a<b`$ `` | `$a&amp;lt;b$` | **double-escaped** → KaTeX sees `&lt;`; write `\lt` / `\gt` |
| `\tag{$x$}`, `\text{$x$}` | `\tag{\$x\$}` | `$` is escaped even inside a fence → math commands land in text mode |
| `$a \, b$` | `$a , b$` | **a stray comma is rendered** |
| `` $`\{x\}`$ ``, `` $`a \, b`$ `` | unchanged | ✅ code span is not escaped |
| ```` ```math ```` fence | contents kept, except `\\` | ✅ for display math |

So the safe forms are:

* display math → ```` ```math ```` fence (not `$$ … $$`)
* inline math → `` $`…`$ `` (not bare `$…$`)
* row breaks → `\cr` (never `\\`)
* `<` and `>` in **inline** math → `\lt`, `\gt` (inside a fence they are fine)
* never write `$` anywhere inside math — not in `\text{…}`, not in `\tag{…}`

## Scripts (start here)

`scripts/check-local.js` — before pushing. Renders every formula of the given files (or
every `*.md` of a directory) with KaTeX and enforces the safe forms above.

```bash
npm install -g katex          # once
node ~/.claude/skills/github-math-check/scripts/check-local.js md/YAPSS
```

`scripts/check-github.js` — after pushing, and this is the one that decides. It fetches
the file's rendered payload from GitHub, pulls out **every** `<math-renderer>` body — the
exact string handed to the browser's renderer — and runs each through KaTeX.

```bash
node ~/.claude/skills/github-math-check/scripts/check-github.js \
     https://github.com/OWNER/REPO/blob/BRANCH/path/File.md
# url      : ...
# formulas : 2178 (84 display, 2094 inline)
# errors   : 0
```

Both exit non-zero on failure, so they can gate a commit. Green locally does **not**
imply green on GitHub — always run the second one on the pushed file.

Implementation note: request the blob URL with `Accept: application/json` and read
`payload.codeViewBlobRoute.richText`. The plain HTML page sets `richTextTruncated: true`
and `richText: null` for large files; the JSON response is never truncated.

## Method 1 — GitHub's Markdown API (fast, no push)

Shows how GitHub converts a snippet. Good for comparing two ways of writing something.

```bash
printf '%s' '{"text":"```math\n\\begin{aligned}\nA &= 1,\\cr\nB &= 2.\n\\end{aligned}\n```\n"}' > /tmp/p.json
curl -s -X POST https://api.github.com/markdown -H "Content-Type: application/json" --data @/tmp/p.json
```

Read the HTML it returns: `<pre lang="math"><code>…</code></pre>` for a fence,
`$<code>…</code>$` for `` $`…`$ ``. Check that backslashes and escapes survived.

⚠ The API does **not** reproduce the `\\` → `\\\` step, which happens in the blob-page
pipeline. Use method 2 for that.

## Method 2 — decode what the live page delivers (authoritative)

```bash
curl -s --max-time 40 "https://github.com/OWNER/REPO/blob/BRANCH/PATH.md?t=$(date +%s)" -o /tmp/gh.html
python3 - <<'EOF'
import re, json
s = open('/tmp/gh.html', encoding='utf-8', errors='replace').read()
for b in re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', s, re.S):
    if 'aligned' not in b:            # or any marker from the formula you care about
        continue
    def walk(o):
        if isinstance(o, str): yield o
        elif isinstance(o, dict):
            for v in o.values(): yield from walk(v)
        elif isinstance(o, list):
            for v in o: yield from walk(v)
    for t in walk(json.loads(b)):
        i = t.find('begin{aligned}')
        if i >= 0:
            print(repr(t[i:i+200]))   # <- the exact string the renderer receives
            raise SystemExit
EOF
```

Count the backslashes in the output. `,\cr` is right; `,\\\` is the bug.
Add a cache-busting query (`?t=…`) — GitHub serves the page cached otherwise, and you
will keep reading an old revision. Confirm the revision by grepping the page for the
commit sha.

The blob page carries the math as `<math-renderer class="js-display-math">$$…$$</math-renderer>`;
the error text (`Missing \end{aligned}`) is produced in the browser, so it is **not** in
the served HTML. Do not conclude "no error" from its absence — inspect the string.

## Method 3 — probe file (when comparing several spellings)

Push a throwaway file with the variants side by side, decode it with method 2, then
delete it. This is how the table above was measured.

```markdown
## A: fence + double backslash
```math
\begin{aligned}
A &= 1,\\
B &= 2.
\end{aligned}
```
## B: fence + \cr
```math
\begin{aligned}
A &= 1,\cr
B &= 2.
\end{aligned}
```
```

Wait ~10 s after the push before fetching.

## Local pre-check (necessary, not sufficient)

Render every formula with KaTeX — the same engine GitHub uses — to catch genuine LaTeX
errors before looking at GitHub:

```bash
npm install katex
node -e '
const katex=require("katex"), fs=require("fs");
let bad=0;
for (const f of fs.readdirSync(".").filter(x=>x.endsWith(".md"))) {
  const lines=fs.readFileSync(f,"utf8").split("\n"); let i=0; const rest=[];
  while (i<lines.length) {                       // ```math fences
    if (lines[i].trim()==="```math") {
      let j=i+1, body=[];
      while (j<lines.length && lines[j].trim()!=="```") body.push(lines[j++]);
      try { katex.renderToString(body.join("\n"),{displayMode:true,throwOnError:true}); }
      catch(e){ bad++; console.log(f,i+1,e.message.slice(0,70)); }
      i=j+1; continue;
    }
    rest.push(lines[i++]);
  }
  const j=rest.join("\n");                        // $`...`$ inline
  for (const m of j.matchAll(/\$`([^`]+)`\$/g)) {
    try { katex.renderToString(m[1],{displayMode:false,throwOnError:true}); }
    catch(e){ bad++; console.log(f,e.message.slice(0,70)); }
  }
  const stray=j.replace(/\$`[^`]+`\$/g,"").match(/\$/g);
  if (stray) { bad+=stray.length; console.log(f,"unprotected $ x"+stray.length); }
  const rows=fs.readFileSync(f,"utf8").match(/\\\\(?!\\)/g);
  if (rows) { bad+=rows.length; console.log(f,"use \\cr not \\\\ x"+rows.length); }
}
console.log("errors:",bad); process.exit(bad?1:0);'
```

A green run here plus method 2 on one representative formula is enough to publish.

## Order of work when a formula is reported broken

1. Fetch the raw file (`raw.githubusercontent.com/...`) and confirm which revision the
   report is about — the reader may be looking at a cached page of an older commit.
2. Method 2 on that formula. The delivered string tells you which transformation bit you.
3. Fix the spelling per the table, re-push, and **re-measure with method 2**. Do not
   report it fixed on the strength of a local render.
