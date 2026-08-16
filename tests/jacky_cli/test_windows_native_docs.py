from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    assert "%LOCALAPPDATA%\\jacky\\jacky-agent\\venv\\Scripts" in doc
    assert "Get-Command jacky        # should print C:\\Users\\<you>\\AppData\\Local\\jacky\\jacky-agent\\venv\\Scripts\\jacky.exe" in doc
    assert '$jackyBin = "$InstallDir\\venv\\Scripts"' in install
