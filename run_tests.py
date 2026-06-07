#!/usr/bin/env python3
"""Prism builder: regenerate artifacts, then run the test suite (CBOR, corpus,
validator, regen gate, compat gate, CRDT). Cross-platform. Run: python run_tests.py"""

import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(SRC))


def main() -> None:
    run([sys.executable, "-m", "prism.corpus.build"])
    run([sys.executable, "-m", "pytest", "tests", "-q"])


if __name__ == "__main__":
    main()
