#!/usr/bin/env python3
"""Generate a GitHub-flavored Table of Contents for README files.

Inserts (or refreshes) a TOC block between the ``<!-- TOC -->`` and
``<!-- /TOC -->`` markers, placed right before the first H2 heading.
Idempotent: re-running on an already-generated file only rewrites the block,
leaving the rest of the document untouched.

Anchor rules follow GitHub's slugger behavior (keeps CJK characters):
lowercase -> strip HTML tags -> drop ASCII punctuation -> spaces to hyphens.
Repeated headings get ``-1``, ``-2`` ... suffixes, matching GitHub rendering.

Usage:
    python scripts/gen_toc.py README.md README.en.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TOC_BEGIN = "<!-- TOC -->"
TOC_END = "<!-- /TOC -->"
HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")  # H2 ~ H4


def _slugify(text: str) -> str:
    """GitHub-style anchor id (github-slugger compatible, CJK-friendly)."""
    s = text.lower()
    s = re.sub(r"<[^>]+>", "", s)
    # Keep unicode word chars (incl. CJK), digits, underscore, hyphen, space;
    # drop everything else (ASCII punctuation etc.).
    s = re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE)
    return s.replace(" ", "-")


def _collect_headings(text: str) -> list[tuple[int, str, str]]:
    """Collect (level, raw_title, anchor) for H2-H4 outside fenced blocks and TOC block."""
    headings: list[tuple[int, str, str]] = []
    in_fence = False
    in_toc = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith(TOC_BEGIN):
            in_toc = True
            continue
        if stripped.startswith(TOC_END):
            in_toc = False
            continue
        if in_toc:
            continue
        m = HEADING_RE.match(stripped)
        if not m:
            continue
        level = len(m.group(1))
        raw = m.group(2).strip()
        # Anchor text ignores inline markdown links and emphasis/code markers.
        anchor_text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", raw)
        anchor_text = re.sub(r"[*_`]", "", anchor_text)
        headings.append((level, raw, _slugify(anchor_text)))
    return headings


def _build_toc(headings: list[tuple[int, str, str]]) -> str:
    counts: dict[str, int] = {}
    for _, _, anchor in headings:
        counts[anchor] = counts.get(anchor, 0) + 1
    seen: dict[str, int] = {}
    lines = [TOC_BEGIN]
    for level, raw, anchor in headings:
        seen[anchor] = seen.get(anchor, 0) + 1
        suffix = "" if seen[anchor] == 1 else f"-{seen[anchor] - 1}"
        indent = "  " * (level - 2)
        lines.append(f"{indent}- [{raw}](#{anchor}{suffix})")
    lines.append(TOC_END)
    return "\n".join(lines)


def _inject(text: str, toc_block: str) -> str:
    """Replace existing TOC block or insert a fresh one before the first H2.

    Works line-wise so the operation is idempotent: the marker block and its
    items are dropped, leading blank lines above the first H2 are normalized
    to exactly one, then the new block is inserted.
    """
    lines = text.splitlines()
    out: list[str] = []
    in_toc = False
    for ln in lines:
        st = ln.strip()
        if st == TOC_BEGIN:
            in_toc = True
            continue
        if st == TOC_END:
            in_toc = False
            continue
        if not in_toc:
            out.append(ln)
    head = -1
    for i, ln in enumerate(out):
        if HEADING_RE.match(ln.strip()):
            head = i
            break
    if head == -1:
        return text
    j = head
    while j > 0 and out[j - 1].strip() == "":
        j -= 1
    prefix = out[:j]
    suffix = out[head:]
    # Blank line above the TOC block (markdown paragraph/block separation).
    gap = [""] if prefix and prefix[-1].strip() != "" else []
    new_lines = prefix + gap + [toc_block, ""] + suffix
    return "\n".join(new_lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/gen_toc.py README.md [README.en.md ...]", file=sys.stderr)
        return 2
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        raw = path.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8-sig")
        headings = _collect_headings(text)
        toc = _build_toc(headings)
        new_text = _inject(text, toc)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8", newline="\r\n" if crlf else "\n")
            print(f"updated: {path} ({len(headings)} headings)")
        else:
            print(f"unchanged: {path} ({len(headings)} headings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
