"""Documentation policy check (README.md, "How documents work"). Run by CI.

    python3 tools/check_docs.py [repo_root]

It fails (exit 1) when:
  1. a relative markdown link outside archive/ points at a missing file
  2. a file under archive/ has no row in archive/README.md
  3. a live document has struck-through text or an "outdated" marker
  4. CHANGELOG.md has no entry for a PR merged into the current history
"""
import fnmatch
import os
import re
import subprocess
import sys

LIVE_GLOBS = [
    "README.md",
    "research/orb_breakout/SETUP_GUIDE.md",
    "research/orb_breakout/ops/*.md",
]
LIVE_EXCLUDE = {"research/orb_breakout/ops/weekly_reviews.md"}   # a record
STALE_MARKERS = [
    (re.compile(r"~~"), "struck-through text"),
    (re.compile(r"\(outdated", re.I), "'(outdated' block"),
    (re.compile(r"\*\*Status update \(", re.I), "dated status update"),
]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^\s*```")


def tracked(root):
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    files = out.stdout.split() if out.returncode == 0 else []
    if not files:   # not a git checkout (e.g. tests): walk the tree
        for d, _, fs in os.walk(root):
            if ".git" in d.split(os.sep):
                continue
            files += [os.path.relpath(os.path.join(d, f), root) for f in fs]
    # a moved/deleted file can still be listed until the commit: keep what exists
    return sorted(f for f in files if os.path.exists(os.path.join(root, f)))


def md_lines(path):
    """Lines outside fenced code blocks, with line numbers."""
    fenced = False
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if FENCE.match(line):
                fenced = not fenced
                continue
            if not fenced:
                yield n, re.sub(r"`[^`]*`", "", line)   # ignore inline code


def check_links(root, files):
    errs = []
    for f in files:
        if not f.endswith(".md") or f.startswith("archive/"):
            continue
        base = os.path.dirname(os.path.join(root, f))
        for n, line in md_lines(os.path.join(root, f)):
            for target in LINK.findall(line):
                if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                    continue
                path = target.split("#", 1)[0]
                if path and not os.path.exists(os.path.normpath(os.path.join(base, path))):
                    errs.append(f"{f}:{n}: broken link -> {target}")
    return errs


def check_archive_index(root, files):
    idx = os.path.join(root, "archive", "README.md")
    text = open(idx, encoding="utf-8").read() if os.path.exists(idx) else ""
    errs = []
    for f in files:
        if f.startswith("archive/") and f != "archive/README.md":
            rel = f[len("archive/"):]
            if f"`{rel}`" not in text:
                errs.append(f"{f}: archived file has no row in archive/README.md")
    return errs


def live_docs(root, files):
    def match(f, g):
        d, pat = os.path.split(g)
        return os.path.dirname(f) == d and fnmatch.fnmatch(os.path.basename(f), pat)
    return [f for f in files if f not in LIVE_EXCLUDE and any(match(f, g) for g in LIVE_GLOBS)]


def check_stale(root, files):
    errs = []
    for f in live_docs(root, files):
        for n, line in md_lines(os.path.join(root, f)):
            for rx, what in STALE_MARKERS:
                if rx.search(line):
                    errs.append(f"{f}:{n}: {what} in a live document - "
                                "state the current truth and move history to archive/")
    return errs


def changelog_prs(text):
    prs = set()
    for a, b in re.findall(r"\*\*#(\d+)(?:\s*[–-]\s*#(\d+))?\*\*", text):
        prs.update(range(int(a), int(b or a) + 1))
    return prs


def check_changelog(root):
    path = os.path.join(root, "CHANGELOG.md")
    if not os.path.exists(path):
        return ["CHANGELOG.md is missing"]
    out = subprocess.run(["git", "log", "--format=%s"], cwd=root, capture_output=True, text=True)
    merged = {int(m) for m in re.findall(r"\(#(\d+)\)\s*$", out.stdout, re.M)}
    missing = sorted(merged - changelog_prs(open(path, encoding="utf-8").read()))
    return [f"CHANGELOG.md: no entry for merged PR #{n}" for n in missing]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = os.path.abspath(argv[0] if argv else os.path.join(os.path.dirname(__file__), ".."))
    files = tracked(root)
    errs = (check_links(root, files) + check_archive_index(root, files)
            + check_stale(root, files) + check_changelog(root))
    for e in errs:
        print(e)
    print(f"check_docs: {len(errs)} problem(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
