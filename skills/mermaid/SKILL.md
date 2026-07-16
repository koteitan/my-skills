---
name: mermaid
description: Rules for drawing Mermaid diagrams — no node fill colors, no diamond nodes, short captions without parentheses
---

# Mermaid diagram rules

Apply these whenever you write a Mermaid diagram.

## No background color on nodes

Do not fill nodes with a background color. Colored fills make the label text hard
to read, and they break in the reader's opposite light/dark theme.

- Do not use `style N fill:#...`, `classDef ... fill:#...`, or `%%{init: ... }%%`
  theme overrides that set node fills.
- Leave nodes on the default theme. If you must distinguish groups, use
  `subgraph`, or a stroke, or the node shape — not a fill.

```
%% bad
style A fill:#f96

%% good
subgraph Input
  A[read file]
end
```

## No diamond nodes

Do not use the diamond shape `X{...}`. It is large and wastes horizontal space,
and long text inside it gets very wide.

Write the decision as a plain node and put the branch condition on the **edge
label** instead.

```
%% bad
A{is cache valid?} -->|yes| B[serve]
A -->|no| C[rebuild]

%% good
A[check cache] -->|valid| B[serve]
A -->|stale| C[rebuild]
```

## Short captions

Keep every node caption short — a few words, ideally under ~20 characters.

- **No parentheses.** They make captions long. Move the detail to an edge label,
  a `subgraph` title, or drop it.
- Prefer a noun or a short verb phrase. Drop articles.

```
%% bad
A[parse the session JSONL file (including sub-agents)]

%% good
A[parse session JSONL]
```

If a qualifier really matters, put it on the edge:

```
A[parse JSONL] -->|sub-agents included| B[index]
```
