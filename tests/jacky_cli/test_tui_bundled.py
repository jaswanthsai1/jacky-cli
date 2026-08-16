

def test_tui_finds_bundled_entry_js(tmp_path):
    """_find_bundled_tui finds entry.js bundled in the package."""
    tui_dist = tmp_path / "jacky_cli" / "tui_dist"
    tui_dist.mkdir(parents=True)
    entry = tui_dist / "entry.js"
    entry.write_text("// bundled TUI", encoding="utf-8")

    from jacky_cli.main import _find_bundled_tui
    result = _find_bundled_tui(jacky_cli_dir=tmp_path / "jacky_cli")
    assert result is not None
    assert result.name == "entry.js"


def test_tui_returns_none_when_no_bundle(tmp_path):
    """_find_bundled_tui returns None when no bundle exists."""
    from jacky_cli.main import _find_bundled_tui
    result = _find_bundled_tui(jacky_cli_dir=tmp_path / "jacky_cli")
    assert result is None
