"""Toolchain finders for the parity gate's runners (`taut.corpus.parity_<target>`).

Each finder returns the path of a toolchain that runs, or None when there is none.
A runner turns None into a skip with a reason, and nothing else skips: a build that
fails is RED (TautCheckedDecode.md §5.4).

The Java and Kotlin search orders copy the per-language tests
(`src/tests/test_java.py::_find_java_tools`, `src/tests/test_kotlin.py::_find_kotlinc`
and `_find_java`): JAVA_HOME, then Android Studio's bundled JBR, then PATH; KOTLINC,
then Android Studio's Kotlin plugin, then PATH.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

ANDROID_STUDIO_JBR = Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home")
ANDROID_STUDIO_KOTLINC = Path(
    "/Applications/Android Studio.app/Contents/plugins/Kotlin/kotlinc/bin/kotlinc"
)
_PROBE_TIMEOUT = 120  # seconds; kotlinc starts a JVM


def _runs(argv: list[str], env: dict[str, str] | None = None) -> bool:
    """True when `argv` runs and exits 0 (a stub or broken install does not)."""
    try:
        subprocess.run(argv, check=True, capture_output=True, env=env, timeout=_PROBE_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def _on_path(name: str, *version_args: str) -> str | None:
    path = shutil.which(name)
    if path is None or not _runs([path, *version_args]):
        return None
    return path


def find_rustc() -> str | None:
    return _on_path("rustc", "--version")


def find_node() -> str | None:
    return _on_path("node", "--version")


def find_node_for_typescript() -> str | None:
    """node that runs `.ts` directly (`--experimental-strip-types`, node >= 22.6)."""
    node = find_node()
    if node is None or not _runs([node, "--experimental-strip-types", "-e", ""]):
        return None
    return node


def find_go() -> str | None:
    return _on_path("go", "version")


def find_swiftc() -> str | None:
    return _on_path("swiftc", "--version")


def find_cxx() -> str | None:
    """A C++ compiler: c++, then clang++, then g++ (as src/tests/test_cpp.py)."""
    for name in ("c++", "clang++", "g++"):
        path = _on_path(name, "--version")
        if path is not None:
            return path
    return None


# --- Java: JAVA_HOME, Android Studio's JBR, PATH ----------------------------------

def _java_pair_candidates() -> Iterator[tuple[Path, Path]]:
    def pair(home: Path) -> tuple[Path, Path]:
        return home / "bin" / "javac", home / "bin" / "java"

    if os.environ.get("JAVA_HOME"):
        yield pair(Path(os.environ["JAVA_HOME"]))
    yield pair(ANDROID_STUDIO_JBR)
    javac = shutil.which("javac")
    java_bin = shutil.which("java")
    if javac and java_bin:
        yield Path(javac), Path(java_bin)


def find_java_tools() -> tuple[str, str] | None:
    """(javac, java) from one JDK that runs."""
    for javac, java_bin in _java_pair_candidates():
        if not javac.is_file() or not java_bin.is_file():
            continue
        if _runs([str(javac), "-version"]) and _runs([str(java_bin), "-version"]):
            return str(javac), str(java_bin)
    return None


# --- Kotlin: KOTLINC, Android Studio's plugin, PATH; and the java it runs with ---

def _kotlinc_candidates() -> Iterator[Path]:
    seen: set[str] = set()
    for raw in (os.environ.get("KOTLINC"), ANDROID_STUDIO_KOTLINC, shutil.which("kotlinc")):
        if not raw:
            continue
        path = Path(raw)
        if path.is_dir():
            path = path / "bin" / "kotlinc"
        key = os.fspath(path)
        if key not in seen:
            seen.add(key)
            yield path


def _kotlin_java_candidates(kotlinc: str) -> Iterator[Path]:
    seen: set[str] = set()
    candidates: list[Path] = []
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]) / "bin" / "java")
    for parent in Path(kotlinc).resolve().parents:
        for rel in ("jbr/Contents/Home/bin/java", "jbr/bin/java",
                    "jdk/Contents/Home/bin/java", "jdk/bin/java"):
            candidates.append(parent / rel)
    java_bin = shutil.which("java")
    if java_bin:
        candidates.append(Path(java_bin))
    for path in candidates:
        key = os.fspath(path)
        if key not in seen:
            seen.add(key)
            yield path


def find_kotlin_java(kotlinc: str) -> str | None:
    """The java to run kotlinc and its jars with: JAVA_HOME, a JBR/JDK beside kotlinc, PATH."""
    for java_bin in _kotlin_java_candidates(kotlinc):
        if java_bin.is_file() and _runs([str(java_bin), "-version"]):
            return str(java_bin)
    return None


def find_kotlin_tools() -> tuple[str, str] | None:
    """(kotlinc, java): the first kotlinc that runs under the java found for it.

    The candidates and their order are the tests'; unlike `_find_kotlinc`, the
    probe runs kotlinc with that java's environment, so an Android Studio install
    needs no JAVA_HOME."""
    for kotlinc in _kotlinc_candidates():
        if not kotlinc.is_file():
            continue
        java_bin = find_kotlin_java(str(kotlinc))
        if java_bin is None:
            continue
        if _runs([str(kotlinc), "-version"], env=java_env(java_bin)):
            return str(kotlinc), java_bin
    return None


def find_kotlinc() -> str | None:
    tools = find_kotlin_tools()
    return None if tools is None else tools[0]


def java_env(java_bin: str) -> dict[str, str]:
    """This process's environment with JAVA_HOME and PATH pointing at `java_bin`'s JDK."""
    env = os.environ.copy()
    path = Path(java_bin).resolve()
    if path.name == "java" and path.parent.name == "bin":
        env["JAVA_HOME"] = os.fspath(path.parent.parent)
        env["PATH"] = os.fspath(path.parent) + os.pathsep + env.get("PATH", "")
    return env
