"""Identify the uncommitted review object without making commits/worktrees."""
from pathlib import Path
import argparse
import hashlib
import json

HERE = Path(__file__).resolve().parent
TAUT = HERE.parents[2]
LIMBO = TAUT.parents[1]
SHAPE = TAUT.parent / "taut-shape-py"


def snapshot():
    paths = set((TAUT / "src/taut").rglob("*.py"))
    paths.update((TAUT / "src/tests").glob("*.py"))
    paths.update((SHAPE / "src").rglob("*.py"))
    paths.add(SHAPE / "tools/regenerate_python_facts.py")
    paths.update(HERE.glob("*.py"))
    paths.update(HERE.glob("*.ps1"))
    paths.update((HERE / "goldens").glob("*.py"))
    paths.update([HERE / "README.md", TAUT / "dev-docs/PythonOneOfCheckpoint-Draft.md",
                  TAUT / "dev-docs/OneOf-ExplicitValidation-BuildProposal.md"])
    files = {p.relative_to(LIMBO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"digest": digest, "files": files,
            "heads": {"taut": "2cfee5d6156b0179066dc4eed70f60cde489a422",
                      "taut-shape-py": "da79bfb74376802edcd25049ed4ce29de814db44"}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    current = snapshot()
    if args.check:
        old = json.loads(args.check.read_text(encoding="utf-8"))
        assert old == current, "review object changed"
    if args.write:
        args.write.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(current["digest"], len(current["files"]), "files")
