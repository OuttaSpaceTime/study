"""Run the lint checks: structure errors, prose warnings, per-page `lint_ignore`."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from scripts.wiki.index import iter_wiki_pages, load_index
from scripts.wiki.lint.page import ParsedPage, parse_pages
from scripts.wiki.lint.prose import prose_warnings
from scripts.wiki.lint.structure import structure_errors


def lint_wiki(
    wiki_dir: Path,
    dirty_pages: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Run all lint checks.

    Returns (errors, warnings). Errors should block CI; warnings are informational.

    Per-page `lint_ignore` frontmatter suppresses named **warnings** for that page,
    but only while the page is committed (not dirty in git) — see `_apply_lint_ignore`.
    `dirty_pages` (rel paths under `wiki_dir`) is computed from git when omitted;
    pass an explicit set to make the suppression deterministic in tests.
    """
    wiki_dir = Path(wiki_dir)
    if dirty_pages is None:
        dirty_pages = _dirty_wiki_pages(wiki_dir)
    md_files = iter_wiki_pages(wiki_dir)

    if not md_files:
        return [], []

    pages = parse_pages(wiki_dir, md_files)
    index = load_index(wiki_dir / ".wiki-index.json")

    errors = structure_errors(wiki_dir, pages, index)
    warnings = _apply_lint_ignore(prose_warnings(pages), pages, dirty_pages)

    return errors, warnings


def _dirty_wiki_pages(wiki_dir: Path) -> set[str]:
    """Return wiki-relative paths that have uncommitted git changes.

    Includes modified, staged, and untracked files. Returns an empty set when
    `wiki_dir` is not inside a git repo or git is unavailable — so suppression
    falls back to "treat as clean" rather than crashing lint.
    """
    try:
        top = subprocess.run(
            ["git", "-C", str(wiki_dir), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if top.returncode != 0:
            return set()
        root = Path(top.stdout.strip())
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if status.returncode != 0:
            return set()
    except (OSError, subprocess.SubprocessError):
        return set()

    dirty: set[str] = set()
    for line in status.stdout.splitlines():
        if len(line) < 4:
            continue
        path_part = line[3:]
        # Renames are reported as "old -> new"; the new path is what's on disk.
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        abs_path = (root / path_part.strip().strip('"')).resolve()
        try:
            dirty.add(str(abs_path.relative_to(wiki_dir.resolve())))
        except ValueError:
            continue  # outside the wiki tree
    return dirty


def _warning_label_and_target(warning: str) -> tuple[str, str]:
    """Split a warning string into its `label` and the page rel-path it concerns.

    Warnings are formatted `"<label>: <rel> ..."`. A warning whose second token
    is not a page path simply won't match any page's lint_ignore, so it is never
    suppressed by accident.
    """
    label, _, rest = warning.partition(": ")
    target = rest.split(maxsplit=1)[0] if rest else ""
    return label, target


def _apply_lint_ignore(
    warnings: list[str], pages: list[ParsedPage], dirty_pages: set[str]
) -> list[str]:
    """Drop warnings a page opted out of via `lint_ignore`, unless the page is dirty.

    `lint_ignore` is a frontmatter list of warning labels (e.g. `heading-case`).
    The opt-out only holds while the page is committed: a page with uncommitted
    changes still gets all its warnings, so the decision to ignore must itself be
    committed before it takes effect, and editing the page re-surfaces the rule.
    Only warnings are suppressible; errors are never filtered.
    """
    ignore_map: dict[str, set[str]] = {}
    for p in pages:
        rules = p.meta.get("lint_ignore") or []
        if isinstance(rules, list):
            ignored = {str(r) for r in rules}
            if ignored:
                ignore_map[p.rel] = ignored

    if not ignore_map:
        return warnings

    kept: list[str] = []
    for w in warnings:
        label, target = _warning_label_and_target(w)
        ignored = ignore_map.get(target)
        if ignored and label in ignored and target not in dirty_pages:
            continue
        kept.append(w)
    return kept


def main() -> None:
    parser = argparse.ArgumentParser(description="Wiki linter")
    parser.add_argument("wiki_dir", nargs="?", default="wiki", help="Wiki directory")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    md_files = iter_wiki_pages(wiki_dir)
    errors, warnings = lint_wiki(wiki_dir)

    if not errors and not warnings:
        print(f"lint: wiki is clean ({len(md_files)} pages checked)")
        sys.exit(0)

    summary = []
    if errors:
        summary.append(f"{len(errors)} error(s)")
    if warnings:
        summary.append(f"{len(warnings)} warning(s)")
    print(f"lint: {', '.join(summary)} in {len(md_files)} pages:")
    print()
    for err in errors:
        print(f"  \u2717 {err}")
    for warn in warnings:
        print(f"  \u26a0 {warn}")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
