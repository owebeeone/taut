from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_readme_omits_test_result_claims():
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()

    banned = [
        "tests green",
        "test green",
        "tests passed",
        "test passed",
    ]
    for phrase in banned:
        assert phrase not in text
