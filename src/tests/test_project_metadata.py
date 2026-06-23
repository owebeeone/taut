from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def test_release_version_is_next_minor():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"$', text)

    assert match is not None
    assert match.group(1) == "0.6.0"
