"""tools/check_docs.py catches each policy breach (README.md, "How documents work")."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import check_docs  # noqa: E402


def make(tmp_path, files):
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return check_docs.main([str(tmp_path)])


CLEAN = {
    "README.md": "See [guide](research/orb_breakout/SETUP_GUIDE.md).\n",
    "CHANGELOG.md": "- **#1–#3** first\n- **#4** next\n",
    "research/orb_breakout/SETUP_GUIDE.md": "Current state only.\n",
    "research/orb_breakout/ops/weekly_reviews.md": "~~records may strike~~\n",
    "archive/README.md": "| `research/old.md` | ... |\n",
    "archive/research/old.md": "~~frozen~~ [dead](nowhere.md)\n",
}


def test_clean_tree_passes(tmp_path):
    assert make(tmp_path, CLEAN) == 0


def test_broken_link_fails(tmp_path, capsys):
    assert make(tmp_path, dict(CLEAN, **{"README.md": "[x](missing.md)\n"})) == 1
    assert "broken link" in capsys.readouterr().out


def test_links_in_code_and_urls_are_ignored(tmp_path):
    text = "`[x](missing.md)`\n```\n[y](gone.md)\n```\n[z](https://a.b) [w](#top)\n"
    assert make(tmp_path, dict(CLEAN, **{"README.md": text})) == 0


def test_unindexed_archive_file_fails(tmp_path, capsys):
    assert make(tmp_path, dict(CLEAN, **{"archive/research/other.md": "x"})) == 1
    assert "no row in archive/README.md" in capsys.readouterr().out


def test_strikethrough_and_outdated_in_live_doc_fail(tmp_path, capsys):
    guide = "research/orb_breakout/SETUP_GUIDE.md"
    assert make(tmp_path, dict(CLEAN, **{guide: "~~old~~ new\n"})) == 1
    assert make(tmp_path, dict(CLEAN, **{guide: "*(outdated: see top)*\n"})) == 1
    assert make(tmp_path, dict(CLEAN, **{"research/orb_breakout/ops/GO_NO_GO.md":
                                         "**Status update (2026-01-01)**\n"})) == 1
    assert "live document" in capsys.readouterr().out


def test_changelog_ranges_parsed():
    assert check_docs.changelog_prs("- **#1–#4** a\n- **#17** b\n") == {1, 2, 3, 4, 17}


def test_this_repo_passes():
    root = os.path.join(os.path.dirname(__file__), "..")
    assert check_docs.main([root]) == 0
