#!/usr/bin/env python3
"""Detect cross-language link mistakes under the my-github-md-rule convention.

A file written in one language should link to same-language documents. For
example, a Japanese file (`README-ja.md`) that references another document
should point to that document's Japanese variant, not its English one. This
checker flags links where the target's language variant differs from the
source file's language -- but only when the correct same-language sibling
actually exists on disk, so single-language documents are never flagged.

Language of a file is decided by its name suffix, which depends on the mode
(see ../SKILL.md):

  mode 3 (Japanese main):  README.md = ja,  README-en.md = en
  mode 4 (English  main):  README.md = en,  README-ja.md = ja

`-ja` / `-en` suffixes always mean Japanese / English; a bare name takes the
mode's main language. Pick the mode with --mode. Modes 1 and 2 are
single-language, so there is nothing to cross-check.

Navigation links -- the language switcher (`[English](README.md)`,
`[日本語](README-ja.md)`) and the back link (`[← Back](../README.md)`) -- are
intentional cross-language links and are skipped. They are recognized by their
visible text (language names and back arrows), not by their target.

Usage:
  check-link-lang.py --mode 4 [PATH ...]

PATH may be files or directories (recursed). Default: current directory.
Exit code is 1 when any mismatch is found, 0 otherwise, so it works in CI.
"""

import argparse
import os
import re
import sys
from urllib.parse import unquote

# Markdown inline link: [text](target).  target may carry a "title" after a
# space, which we drop.
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

# Compact tokens that mark a navigation link (language switcher / back link).
# Link text is reduced to lowercase letters + CJK before comparing, so arrows,
# emoji, brackets and backticks around the word do not matter.
NAV_TOKENS = {
    "english", "japanese", "日本語", "en", "ja",  # language switchers
    "back", "戻る", "もどる", "top", "home", "index",  # back / home links
}
_KEEP_RE = re.compile(r"[a-z぀-ヿ一-鿿]+")


def reduce_text(text: str) -> str:
    """Lowercase and keep only letters + kana/kanji, so decorations drop out."""
    return "".join(_KEEP_RE.findall(text.lower()))


def is_nav_link(text: str) -> bool:
    core = reduce_text(text)
    return core == "" or core in NAV_TOKENS


def classify(name: str, main_lang: str):
    """Return (language, base) for a markdown filename.

    base is the path stem with any -ja/-en suffix removed, so that two language
    variants of the same document share a base.
    """
    stem = name[:-3] if name.endswith(".md") else name
    if stem.endswith("-ja"):
        return "ja", stem[:-3]
    if stem.endswith("-en"):
        return "en", stem[:-3]
    return main_lang, stem


def sibling(base: str, lang: str, main_lang: str) -> str:
    """Filename of the `lang` variant of `base` under the given main language."""
    if lang == main_lang:
        return base + ".md"
    return base + "-" + lang + ".md"


def iter_links(path: str):
    """Yield (lineno, text, target) for markdown links outside code."""
    in_fence = False
    with open(path, encoding="utf-8", errors="replace") as fh:
        for lineno, raw in enumerate(fh, 1):
            if FENCE_RE.match(raw):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for m in LINK_RE.finditer(raw):
                yield lineno, m.group(1), m.group(2)


def collect_files(paths):
    files = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
        elif os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = [d for d in dirs if d != ".git"]
                for n in names:
                    if n.endswith(".md"):
                        files.append(os.path.join(root, n))
        else:
            print(f"warning: no such path: {p}", file=sys.stderr)
    return sorted(set(files))


def check_file(path: str, main_lang: str):
    """Return a list of issue strings for one source file."""
    issues = []
    src_dir = os.path.dirname(path) or "."
    slang, _ = classify(os.path.basename(path), main_lang)

    for lineno, text, target in iter_links(path):
        if is_nav_link(text):
            continue
        raw = target.strip().split()[0].strip("<>")  # drop "title", angle brackets
        raw = raw.split("#", 1)[0].split("?", 1)[0]   # drop anchor / query
        raw = unquote(raw)
        if not raw or not raw.endswith(".md"):
            continue
        if "://" in raw or raw.startswith("mailto:") or os.path.isabs(raw):
            continue

        tlang, tbase = classify(os.path.basename(raw), main_lang)
        if tlang == slang:
            continue

        want_name = sibling(os.path.basename(tbase), slang, main_lang)
        want_rel = os.path.join(os.path.dirname(raw), want_name) if os.path.dirname(raw) else want_name
        want_abs = os.path.normpath(os.path.join(src_dir, want_rel))
        if not os.path.isfile(want_abs):
            continue  # no same-language sibling: single-language doc, skip

        issues.append(
            f"{path}:{lineno}: [{slang}] file links to {tlang} variant "
            f"'{raw}'; expected '{want_rel}'"
        )
    return issues


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Detect cross-language link mistakes (my-github-md-rule).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Modes: 3 = Japanese main (README.md=ja), 4 = English main (README.md=en).",
    )
    ap.add_argument(
        "--mode", type=int, choices=(3, 4), required=True,
        help="skill mode: 3 (Japanese main) or 4 (English main)",
    )
    ap.add_argument(
        "paths", nargs="*", default=["."],
        help="files or directories to scan (default: current directory)",
    )
    args = ap.parse_args(argv)

    main_lang = "ja" if args.mode == 3 else "en"
    files = collect_files(args.paths)

    issues = []
    for f in files:
        issues.extend(check_file(f, main_lang))

    for line in issues:
        print(line)

    if issues:
        print(f"\n{len(issues)} mismatch(es) found.", file=sys.stderr)
        return 1
    print(f"No language-link mismatches in {len(files)} file(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
