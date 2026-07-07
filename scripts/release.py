#!/usr/bin/env python3
"""Cut a taut-proto PyPI release from ``main``.

taut-proto uses setuptools-scm, so the package version comes from the release
tag. There is no version file to bump. This script gates the local tree, builds
and smoke-tests a PyPI distribution for the requested version, creates an
immutable lightweight tag, and optionally pushes it.

PyPI publishing is handled by ``.github/workflows/publish.yml`` when a GitHub
Release is published. With ``--push`` this script also creates that GitHub
Release by default, so the standard release command is:

    python scripts/release.py --push vX.Y.Z

Use ``--no-github-release`` if you only want to push ``main`` and the tag.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "dist"
PACKAGE_NAME = "taut-proto"
IMPORT_NAME = "taut"
PRETEND_VERSION_ENV = "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TAUT_PROTO"


def fail(msg: str):
    print(f"release: error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def log(msg: str):
    print(f"release: {msg}")


def run(
    cmd: list[object],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    printable = " ".join(str(c) for c in cmd)
    log(f"$ {printable}")
    result = subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd) if cwd is not None else None,
        capture_output=capture,
        text=True,
        env=env,
    )
    if check and result.returncode != 0:
        if capture and result.stdout:
            print(result.stdout)
        if capture and result.stderr:
            print(result.stderr, file=sys.stderr)
        fail(f"command failed ({result.returncode}): {printable}")
    return result


def git(args: list[object], **kw) -> subprocess.CompletedProcess:
    return run(["git", "-C", REPO, *args], **kw)


def current_branch() -> str:
    result = git(["branch", "--show-current"], capture=True)
    branch = result.stdout.strip()
    if not branch:
        fail("detached HEAD -- switch to main before releasing")
    return branch


def warn_if_behind_upstream(branch: str):
    upstream = git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{u}}"],
        capture=True,
        check=False,
    )
    if upstream.returncode != 0 or not upstream.stdout.strip():
        return
    name = upstream.stdout.strip()
    behind = git(["rev-list", "--count", f"{branch}..{name}"], capture=True, check=False)
    count = behind.stdout.strip()
    if count and count != "0":
        log(
            f"WARNING: local {branch} is {count} commit(s) behind {name} "
            f"(tracking ref; run `git fetch` for current state) -- releasing local {branch}"
        )


def working_tree_clean():
    status = git(["status", "--porcelain"], capture=True).stdout
    if status.strip():
        fail("working tree is not clean -- commit or stash changes first:\n" + status.rstrip())


def tag_commit(tag: str) -> str | None:
    existing = git(
        ["rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}"],
        capture=True,
        check=False,
    )
    if existing.returncode != 0:
        return None
    return existing.stdout.strip()


def ensure_tag(tag: str, target: str):
    existing = tag_commit(tag)
    if existing is not None:
        if existing == target:
            log(f"tag {tag} already points at {target[:10]} -- leaving it")
            return
        fail(
            f"tag {tag} already exists at {existing[:10]}, not the release commit "
            f"{target[:10]} -- refusing to move a release tag"
        )
    git(["tag", tag, target])
    log(f"created tag {tag} -> {target[:10]}")


def parse_version(tag: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        fail(f"tag must look like vX.Y.Z, got {tag!r}")
    return tuple(int(p) for p in match.groups())


def assert_tag_is_next_release(tag: str):
    requested = parse_version(tag)
    tags = git(["tag", "--list", "v[0-9]*.[0-9]*.[0-9]*"], capture=True).stdout.splitlines()
    versions = []
    for existing in tags:
        try:
            versions.append((parse_version(existing), existing))
        except SystemExit:
            continue
    if not versions:
        return
    latest, latest_tag = max(versions)
    if requested <= latest and tag_commit(tag) is None:
        fail(f"requested {tag} is not newer than latest release tag {latest_tag}")


def python_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(REPO / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def assert_pyproject_metadata():
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    if not re.search(rf'(?m)^name\s*=\s*"{re.escape(PACKAGE_NAME)}"$', text):
        fail(f"expected project.name {PACKAGE_NAME!r} in pyproject.toml")
    if not re.search(r'(?m)^dynamic\s*=\s*\["version"\]$', text):
        fail("pyproject.toml must keep version dynamic for setuptools-scm")
    if not re.search(r'(?m)^tautc\s*=\s*"taut\.cli:main"$', text):
        fail("expected project.scripts.tautc = 'taut.cli:main'")


def assert_python_module(module: str, install_hint: str):
    result = run(
        [sys.executable, "-c", f"import {module}"],
        cwd=REPO,
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        fail(f"Python module {module!r} is not installed -- {install_hint}")


def run_gates(*, no_test: bool, no_parity: bool):
    assert_pyproject_metadata()
    if no_test:
        log("skipping pytest")
    else:
        run([sys.executable, "-m", "pytest", "src/tests", "-q"], cwd=REPO, env=python_env())

    if no_parity:
        log("skipping `tautc parity`")
    else:
        run([sys.executable, "-m", "taut.cli", "parity"], cwd=REPO, env=python_env())


def clean_dist():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()


def build_env(version: str) -> dict[str, str]:
    env = os.environ.copy()
    env[PRETEND_VERSION_ENV] = version
    return env


def build_and_check(version: str, *, keep_dist: bool, no_smoke: bool):
    assert_python_module("build", "run `python -m pip install build twine`")
    assert_python_module("twine", "run `python -m pip install build twine`")
    if not keep_dist:
        clean_dist()

    run([sys.executable, "-m", "build"], cwd=REPO, env=build_env(version))
    artifacts = sorted(DIST.glob("*"))
    if not artifacts:
        fail("build produced no files in dist/")
    bad = [p.name for p in artifacts if version not in p.name]
    if bad:
        fail(f"built artifacts do not contain version {version}: {bad}")

    run([sys.executable, "-m", "twine", "check", *artifacts], cwd=REPO)

    wheels = sorted(DIST.glob("*.whl"))
    if len(wheels) != 1:
        fail(f"expected exactly one wheel, found {[p.name for p in wheels]}")
    if no_smoke:
        log("skipping wheel smoke test")
    else:
        smoke_wheel(wheels[0], version)


def venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def venv_script(venv: Path, name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    bindir = "Scripts" if os.name == "nt" else "bin"
    return venv / bindir / f"{name}{suffix}"


def smoke_wheel(wheel: Path, version: str):
    with tempfile.TemporaryDirectory(prefix="taut-release-smoke-") as tmp:
        root = Path(tmp)
        venv = root / "venv"
        run([sys.executable, "-m", "venv", venv])
        py = venv_python(venv)
        run([py, "-m", "pip", "install", wheel])
        code = (
            "import importlib.metadata as md; "
            f"assert md.version({PACKAGE_NAME!r}) == {version!r}; "
            f"import {IMPORT_NAME}, taut.cli; "
            "print('import/version OK')"
        )
        run([py, "-c", code])
        out = root / "smoke"
        run(
            [
                venv_script(venv, "tautc"),
                "gen",
                REPO / "ir" / "griplab.taut.py",
                "-o",
                out,
                "--lang",
                "rust",
                "--api-only",
            ],
            cwd=REPO,
        )
        generated = out / "rust" / "api.rs"
        if not generated.is_file():
            fail(f"wheel smoke test did not create {generated}")
        log("wheel smoke test passed")


def push_release(branch: str, tag: str):
    result = run(
        ["git", "-C", REPO, "push", "--atomic", "origin", branch, tag],
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        fail(
            f"`git push --atomic origin {branch} {tag}` failed -- with --atomic the remote is left "
            "unchanged; inspect `git ls-remote origin` and retry"
        )
    log(f"pushed {branch} + {tag} to origin (atomic)")


def publish_github_release(tag: str, version: str):
    if not shutil.which("gh"):
        fail(
            "`gh` is not on PATH, so the GitHub Release was not published. "
            "Install GitHub CLI or rerun with --no-github-release and publish the release manually."
        )
    existing = run(["gh", "release", "view", tag], cwd=REPO, capture=True, check=False)
    if existing.returncode == 0:
        log(f"GitHub Release {tag} already exists -- leaving it")
        return
    notes = (
        f"taut-proto {version}\n\n"
        "Publishing this GitHub Release triggers the PyPI Trusted Publishing workflow."
    )
    run(["gh", "release", "create", tag, "--title", tag, "--notes", notes], cwd=REPO)
    log(f"published GitHub Release {tag}; PyPI workflow should start")


def main():
    parser = argparse.ArgumentParser(
        description="Cut a taut-proto PyPI release tag from main."
    )
    parser.add_argument("tag", nargs="?", help="release tag, e.g. v0.7.0")
    parser.add_argument("--branch", default="main", help="branch to release from (default: main)")
    parser.add_argument("--push", action="store_true", help="push branch + tag, then publish GitHub Release")
    parser.add_argument("--no-test", action="store_true", help="skip full pytest suite")
    parser.add_argument("--no-parity", action="store_true", help="skip `tautc parity`")
    parser.add_argument("--no-build", action="store_true", help="skip PyPI build/twine/smoke checks")
    parser.add_argument("--no-smoke", action="store_true", help="skip installing and smoke-testing the wheel")
    parser.add_argument("--keep-dist", action="store_true", help="do not delete existing dist/ before build")
    parser.add_argument(
        "--no-github-release",
        action="store_true",
        help="with --push, only push git refs; do not create the GitHub Release",
    )
    args = parser.parse_args()

    if not args.tag:
        fail("missing release tag; standard usage is `python scripts/release.py --push vX.Y.Z`")
    tag = args.tag
    version_tuple = parse_version(tag)
    version = ".".join(str(part) for part in version_tuple)
    assert_tag_is_next_release(tag)

    for tool in ("git",):
        if not shutil.which(tool):
            fail(f"`{tool}` not found on PATH")

    branch = current_branch()
    if branch != args.branch:
        fail(f"on branch {branch!r} but releases are cut from {args.branch!r} -- switch first")
    warn_if_behind_upstream(args.branch)
    working_tree_clean()

    head = git(["rev-parse", "HEAD"], capture=True).stdout.strip()
    existing = tag_commit(tag)
    if existing is not None and existing != head:
        fail(
            f"tag {tag} already exists at {existing[:10]} but {args.branch} HEAD is "
            f"{head[:10]} -- resolve the tag manually before re-running"
        )

    if existing == head:
        log(f"{tag} already exists at {args.branch} HEAD ({head[:10]}); release already cut locally")
    else:
        run_gates(no_test=args.no_test, no_parity=args.no_parity)
        if args.no_build:
            log("skipping PyPI build/twine/smoke checks")
        else:
            build_and_check(version, keep_dist=args.keep_dist, no_smoke=args.no_smoke)
        ensure_tag(tag, head)

    if args.push:
        push_release(args.branch, tag)
        if args.no_github_release:
            log("GitHub Release not created because --no-github-release was supplied")
            log(f"manual PyPI trigger: publish a GitHub Release for {tag}")
        else:
            publish_github_release(tag, version)
    else:
        log("next step (not done without --push):")
        log(f"  git -C {REPO} push origin {args.branch} {tag}")
        log(f"  gh release create {tag} --title {tag} --notes 'taut-proto {version}'")


if __name__ == "__main__":
    main()
