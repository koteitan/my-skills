---
name: formalization-statement-fidelity-audit
description: Audit a formalization (Lean/Isabelle/Coq/…) against the article it formalizes — one page per proposition, every difference classified X/Y/Z/W/S/R/U — and publish the result as a `diff/` directory with a classification tally. Use when asked to check whether a formalization is faithful to its source, to find where the machine proof silently deviates from the paper, or to produce/refresh `diff/`. Fans the work out with the Workflow tool: one agent per proposition (plan 1) or per chapter (plan 2).
---

# formalization-statement-fidelity-audit

A green build proves the formalization is *correct*. It says nothing about whether it is
**the article's proof**. This skill measures that gap, classifies every difference, and
writes it down.

For every proposition of the source article it produces one page holding:

1. the article's statement, quoted;
2. the article's proof, quoted;
3. the formalized statement, **rewritten as mathematics** (not code);
4. the formalized proof, **rewritten as mathematics**, in full detail;
5. every place where 3–4 depart from 1–2, each tagged with its **class**.

The index then tallies the classes, so the shape of the gap is visible at a glance:
an article with 60 `R`s is over-proved; one with 3 `X`s is broken.

## The classification (the point of the whole exercise)

Every difference gets exactly one class. Classify the **difference**, not the page — one
page usually carries several. `X` and `Z` carry a 🚨 prefix, `Y` a ⚠️, `U` a 🌳; `W`, `S`
and `R` carry none. Write the prefix everywhere the class appears — the table below, the
finding bullets on each page, and the IDs in the index.

| class | condition | whose problem |
|---|---|---|
| 🚨**X** | formalizing the article as written yields a contradiction; essential or large | article — a real error |
| ⚠️**Y** | formalizing the article as written yields a contradiction; a slip of the pen | article — a typo |
| 🚨**Z** | the article's proof has a gap; the gap is essential and large | article — missing mathematics |
| **W** | the article skips steps the formalization must take, as papers normally do; the gap is small | article — an "obviously" |
| **S** | a detour, but the difference from the article's claim is small and nothing downstream changes | ours — benign |
| **R** | part of the article's proof is not needed; the proof goes through without it | article — redundancy |
| 🌳**U** | could not be written the article's way for formalization reasons, so it detours | ours — a real deviation |

Decide in this order, and stop at the first hit:

1. Is the article's statement **false** as written? → 🚨**X** if essential or large,
   ⚠️**Y** if a typo.
2. Is the statement true but the **proof incomplete**? → 🚨**Z** if the gap is essential and
   large, **W** if the formalization fills it with routine work.
3. Did the formalization **not need** part of the article's proof? → **R**.
4. Did we **detour**? → **S** if the claim barely moved and nothing downstream changed,
   otherwise 🌳**U**.

`X`/`Y` become corrections to send to the author. `Z`/`W` are gaps in the article. `R` is
redundancy in the article. `S`/`U` are ours, and `U` is the backlog: each one is either
something still to fix or a structural obstacle to record.

## Invoking Workflow

**This skill authorizes the Workflow tool.** The audit is a fan-out over independent
propositions, which is exactly what Workflow is for. Respect the session's workflow size
guideline; if the item count exceeds it, run several waves rather than one huge workflow.

## Step 0 — collect the inputs

Establish these four things and state them back to the user before writing any script:

| input | how to get it |
|---|---|
| **source text** | the article in readable form (extracted Markdown/plain text). Record its path; if it lives outside the published repository, it must never be named in the output. |
| **item list** | every 定義 / 補題 / 命題 / 系 / 定理 of the article, in order of appearance, numbered `01`, `02`, … Grep the source text for its heading pattern. **Do not reconstruct the list from the formalization** — you would inherit its omissions. |
| **formalization root** | the directory holding the proofs, and its file naming scheme. |
| **item → file map** | which file(s) formalize each item. |

Cross-check both ways: an article item with no file, and a file with no article item, are
both findings. Record them; do not quietly drop them.

## Step 0.5 — pick the plan

| plan | agent granularity | when |
|---|---|---|
| **plan 1** | one agent per proposition | the default. The agent reads one proposition's whole proof, so the page can be detailed. |
| **plan 2** | one agent per chapter | when the item count is large enough that plan 1 would need many waves. One agent writes every page of its chapter. |

Choose by the size of the *proof*, not the number of items: if one proposition's
formalization runs to hundreds of lines, stay on plan 1 and use waves.

## Step 1 — plant the rule in the target repository

Copy [`prompts/rule.md`](prompts/rule.md) to `<project>/diff/rule.md` and fill in its
placeholders (formalization system name, article name, path root). The agents read the
copy, so the project can amend it without touching the skill.

## Step 2 — run the workflow

Every agent reads `diff/rule.md` first, reads its item in the article and in the
formalization, writes `diff/<number>-<slug>.md`, and **returns its findings** so the
parent can tally without re-reading the pages.

```js
export const meta = {
  name: 'fidelity-audit',
  description: 'Audit each proposition of the article against its formalization',
  phases: [{ title: 'Audit' }],
}

const REPORT = {
  type: 'object',
  properties: {
    number: { type: 'string' },
    title:  { type: 'string' },
    slug:   { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          class:   { type: 'string', enum: ['X', 'Y', 'Z', 'W', 'S', 'R', 'U'] },
          summary: { type: 'string' },
        },
        required: ['class', 'summary'],
      },
    },
  },
  required: ['number', 'title', 'slug', 'findings'],
}

const results = await parallel(args.items.map(it => () =>
  agent(
    [
      `Read <project>/diff/rule.md and follow it exactly, including the classification.`,
      `Audit item ${it.number} "${it.title}" of the article.`,
      `Article text: <source path>, lines ${it.srcFrom}-${it.srcTo}.`,
      `Formalization: ${it.files.join(', ')}.`,
      `Write <project>/diff/${it.number}-${it.slug}.md.`,
      `Read every proof step you describe; never summarize what you have not read.`,
      `Do not run a build. Do not edit anything outside your own page.`,
      `Return one entry per difference, in the order they appear on the page, with the`,
      `class letter and a one-line summary. Return an empty list if the item is`,
      `formalized exactly as the article gives it.`,
    ].join('\n'),
    { label: `audit:${it.number}`, phase: 'Audit', schema: REPORT })))

return { results }
```

Pass the item list as `args` — a real JSON array, never a stringified one.

For plan 2 the map is per chapter and the agent returns an array of `REPORT`s.

## Step 3 — assemble the index

Build `<project>/diff/README.md` from the returned findings, not by re-reading the pages.
Assign each finding a stable ID `<class>-<n>`, numbered per class in page order.

```markdown
# チェックシート

原文の各項目について、形式化が原文どおりかを一覧にする。各ページの書き方は
[rule.md](rule.md)。

## 分類

| 分類 | 条件 | 件数 |
|---|---|---|
| 🚨**X** | 原文をそのまま形式化すると矛盾する。本質的、または規模が大きい | 0 |
| ⚠️**Y** | 原文をそのまま形式化すると矛盾する。誤記の類 | 2 |
| 🚨**Z** | 原文に飛躍がある。飛躍が本質的で大きい | 0 |
| **W** | 形式化に比べると原文に飛躍があるが、通常通り小さいもの | 22 |
| **S** | 迂回だが原文の主張との差が小さく、下流の内容を変えない | 0 |
| **R** | 原文の証明の一部が無くても証明が通る | 36 |
| 🌳**U** | 形式化の都合で原文どおりに書けず迂回している | 74 |
| | **合計** | **134** |

## 項目

W と S は件数が多く、どの項目にもあるので、この表には出さない。

| # | 項目 | 指摘 |
|---|---|---|
| [01](01-....md) | 系（…） | — |
| [02](02-....md) | 命題（…） | ⚠️Y-1, 🌳U-3 |

## 指摘一覧

| ID | 項目 | 要旨 |
|---|---|---|
| ⚠️Y-1 | [02](02-....md) | … |
| W-1 | [02](02-....md) | … |
| 🌳U-3 | [02](02-....md) | … |
```

The 項目 table lists only 🚨`X` / ⚠️`Y` / 🚨`Z` / `R` / 🌳`U`; `W` and `S` are too numerous
and too evenly spread to carry information there. The 指摘一覧 stays complete.

IDs exist so findings can be referred to from outside. When you refresh a page, keep the
IDs of findings that persist; do not renumber the whole file.

Then check the totals: the number of rows in 項目 must equal the item count from Step 0,
and 合計 must equal the number of rows in 指摘一覧. Say both counts out loud in your report.

## Step 4 — verify before reporting

Agents optimize for looking finished. Check, do not trust:

1. **Every page exists** and is linked from the index.
2. **No page is an outline.** Open the two or three longest formalized proofs and confirm
   the page describes their actual steps. This is the failure mode the rule spends most of
   its length on, and agents commit it anyway.
3. **Classes are consistent.** Sample one finding of each class and re-run the decision
   tree on it yourself. Fan-out makes agents drift, typically calling `U` what is really
   `W` (blaming our formalization for the article's gap) — that inversion is the one to
   hunt for.
4. **No formalization identifiers leak** outside the correspondence table.
5. **Nothing outside the published tree is named** — not the article's path, not a scratch
   directory.

Report the tally and the `X`/`Y`/`Z` findings in full; summarize the rest by count.

## Refreshing an existing `diff/`

Re-run only the items whose formalization changed since their page was written (`git log`
on the mapped files). Rewrite those pages from scratch rather than patching them: per
rule 5 a page describes the present state, and patched pages accumulate the history the
rule forbids. Carry the old IDs forward for findings that persist.

## Why this is not a code review

A code review asks whether the proof is right. This audit assumes it is right — the build
already said so — and asks whether it is **the same proof the article gives**. A page
saying "our proof is cleaner" has failed: the point is to make the difference visible and
classified, so the user can decide whether to fix the formalization (`U`) or to file a
correction against the article (`X`/`Y`).
