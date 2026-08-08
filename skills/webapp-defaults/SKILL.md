---
name: webapp-defaults
description: The standing defaults when scaffolding a small vanilla web app (index.html + main.js + style.css) — dark mode ON by default and persisted to localStorage, a top-right hamburger pulldown menu, and tab/option state saved to localStorage and restored on load. Apply when creating a new simple SPA/tool page.
---

# webapp-defaults

Default UI conventions the user re-specifies in every small vanilla web app.
Apply them by default when scaffolding a new page unless told otherwise.

## When to invoke

- Creating a new small front-end (a tool page, toy, visualizer) from scratch,
  especially when the user says "main.js style.css index.html で作って".
- User asks for a menu / dark mode / state persistence on such a page.

## Defaults

1. **Stack:** plain `index.html` + `main.js` + `style.css` (vanilla, no build
   step) unless the project already uses a framework.

2. **Dark mode:**
   - **Default is DARK.**
   - Toggle lives as a checkbox in the menu (below).
   - Persist the choice to `localStorage` and restore it on load.

3. **Menu:** a **hamburger pulldown menu in the top-right corner**. Put the
   dark-mode checkbox and any options in it.

4. **State persistence:** save UI state — selected tab, chosen options,
   toggles — to `localStorage`, and **restore it on load** so a reload
   reproduces the last state.

## Sketch

```js
// main.js — dark mode default + persistence
const KEY = 'ui';
const state = JSON.parse(localStorage.getItem(KEY) || '{}');
const dark = state.dark ?? true;                 // default dark
document.documentElement.classList.toggle('dark', dark);

function save(patch) {
  Object.assign(state, patch);
  localStorage.setItem(KEY, JSON.stringify(state));
}
// on tab switch: save({ tab: id });  on load: restore state.tab
```

```css
/* style.css — dark by default via :root, .dark just re-affirms/toggles */
:root { color-scheme: dark; background:#1a1a1a; color:#d4d4d4; }
```

Keep it minimal and dependency-free. Match existing project style if one
exists.
