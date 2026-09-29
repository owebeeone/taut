"""Shared codec-parity gate — the leading cross-language conformance corpus.

Phase 0 of `dev-docs/TautCodecParityPlan.md`, hardened by its §8 P1. Two
language-neutral vector files (`corpus/parity/{int,malformed}.vectors.json`,
produced by `gen_vectors.py`) are replayed through **every codec that has a
runner**. A target is **gated** (must pass) unless it appears in `allowlist.json`,
in which case it is **allowlisted**: its runner still RUNS and REPORTS observed
failures (xfail-that-runs), it just doesn't fail CI. Governance is the inverse
check too — CI fails if an *allowlisted* target passes fully (a green target must
be de-listed) or a *gated* target fails.

Runners. `python` replays in-process (`run_python`). Any other target has a runner
exactly when the module `taut.corpus.parity_<target>` exists and exposes
`run() -> TargetReport`: `_RUNNERS` resolves it, so adding a target is adding that
module and deleting its allowlist entry. `parity_rust.py` is the model a compiled
runner copies: find the toolchain (`toolchains.py`), generate the fixture's code,
build, run. A missing toolchain is the only skip; a failed generation or build is
RED (TautCheckedDecode.md §5.4).

Runner protocol (TautCheckedDecode.md CD-C4). A runner prints one line per row,
`name<TAB>outcome<TAB>detail`:
  - an int row: `pass`, `fail` or `type-satisfied`; the runner checks the round
    trip itself;
  - a malformed row: `ok` when it decoded without error; `err` with the detail
    `Tag;field=value...`, one `;field=value` for each payload field its DecodeError
    carries (`PAYLOAD_FIELDS`); or `untyped`, with a description, when anything
    other than the language's DecodeError escapes.
The gate, not the runner, judges a malformed row (`judge`): an `{"accept": true}`
row passes only on `ok`; a `{"tag": ...}` row passes when the tag matches and every
payload field it names matches when compared as a string (`PAYLOAD_EXEMPT` lists
the fields a runtime does not carry). A row never reported fails, and a runner that
exits non-zero fails its target (`parse_report`).

This corpus **SUPPLEMENTS** `tautc corpus` / the message golden corpora; it never
replaces them. Entry point: `tautc parity`.

`lead` rows (see `gen_vectors.py`) are replayed by this gate but skipped by the
per-language *baseline* smoke tests in `src/tests/test_{rust,ts,js,go,...}.py`.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import subprocess
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..ir.load import load_schema
from ..wire import cbor, codec

ROOT = Path(__file__).resolve().parents[3]
PARITY_DIR = ROOT / "corpus" / "parity"
INT_VECTORS = PARITY_DIR / "int.vectors.json"
MALFORMED_VECTORS = PARITY_DIR / "malformed.vectors.json"
ALLOWLIST = PARITY_DIR / "allowlist.json"

INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1

TARGETS = ("rust", "python", "typescript", "js", "cpp", "swift", "go", "kotlin", "java")
DECODE_TAGS = {
    "Truncated",
    "TrailingBytes",
    "InvalidUtf8",
    "UnsupportedInfo",
    "UnsupportedMajor",
    "NonIntegerMapKey",
    "IntOverflow",
    "DuplicateMapKey",
    "MissingKey",
    "WrongType",
    "UnknownEnum",
    "NonCanonicalInt",
    "NegativeMapKey",
}
ENCODE_TAGS = {"IntOutOfSubset"}
# The payload fields a malformed row may name and a runner reports, in report order.
PAYLOAD_FIELDS = ("info", "major", "key", "expected", "enum", "value")
# Per target, the (tag, field) payloads its runtime does not carry; the gate does
# not compare them (CD-C4).
PAYLOAD_EXEMPT: dict[str, frozenset[tuple[str, str]]] = {
    "rust": frozenset({("IntOverflow", "value")}),  # DecodeError::IntOverflow has no value
}
BUILD_TIMEOUT = 600  # seconds, per build step
RUN_TIMEOUT = 300    # seconds, per runner


class ParityValidationError(ValueError):
    """A committed parity artifact is malformed or stale."""


@dataclass(frozen=True)
class ParityStatus:
    target: str
    status: str
    reason: str
    phase: str = ""
    owner: str = ""


# --- artifact validation ------------------------------------------------------

def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ParityValidationError(f"missing parity artifact: {path}") from exc


def _as_int(value: Any, where: str) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            raise ParityValidationError(f"{where}: expected integer string, got {value!r}") from exc
    raise ParityValidationError(f"{where}: expected integer string, got {type(value).__name__}")


def _hex(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise ParityValidationError(f"{where}: hex value must be a string")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise ParityValidationError(f"{where}: invalid hex {value!r}") from exc
    return value


def _native_intbox(value: dict[str, Any], where: str) -> dict[str, Any]:
    by_id = value.get("by_id")
    if not isinstance(by_id, list):
        raise ParityValidationError(f"{where}: by_id must be a list of [key, value] pairs")
    pairs: list[tuple[int, int]] = []
    seen_keys: set[int] = set()
    for index, pair in enumerate(by_id):
        if not isinstance(pair, list) or len(pair) != 2:
            raise ParityValidationError(f"{where}.by_id[{index}]: expected [key, value]")
        key = _as_int(pair[0], f"{where}.by_id[{index}].key")
        val = _as_int(pair[1], f"{where}.by_id[{index}].value")
        if key in seen_keys:
            raise ParityValidationError(f"{where}.by_id[{index}]: duplicate key {key}")
        seen_keys.add(key)
        pairs.append((key, val))
    return {"n": _as_int(value.get("n"), f"{where}.n"), "by_id": dict(pairs)}


def _check_expect(expect: Any, where: str) -> None:
    """`{"accept": true}`, or a known decode tag with known payload fields (CD-C2)."""
    if not isinstance(expect, dict):
        raise ParityValidationError(f"{where}: expect must be an object")
    if "accept" in expect:
        if expect != {"accept": True}:
            raise ParityValidationError(f"{where}: an accept row expects exactly {{\"accept\": true}}")
        return
    tag = expect.get("tag")
    if tag not in DECODE_TAGS:
        raise ParityValidationError(f"{where}: unknown decode tag {tag!r}")
    unknown = sorted(set(expect) - {"tag", *PAYLOAD_FIELDS})
    if unknown:
        raise ParityValidationError(f"{where}: unknown payload field(s) {unknown}")


def validate_int_vectors(path: Path = INT_VECTORS) -> int:
    data = _load_json(path)
    if data.get("version") != 1:
        raise ParityValidationError(f"{path}: unsupported version {data.get('version')!r}")
    schema = load_schema(ROOT / data["schema_path"])
    count = 0
    names: set[str] = set()
    for row in data.get("vectors", []):
        name = row.get("name", "<unnamed>")
        if name in names:
            raise ParityValidationError(f"{path}:{name}: duplicate row name")
        names.add(name)
        kind = row.get("kind")
        message = row.get("message")
        if message not in schema.messages:
            raise ParityValidationError(f"{path}:{name}: unknown message {message!r}")
        value = _native_intbox(row.get("value", {}), f"{path}:{name}.value")
        if kind == "round_trip":
            expected = _hex(row.get("cbor"), f"{path}:{name}.cbor")
            actual = codec.encode(schema, message, value).hex()
            if actual != expected:
                raise ParityValidationError(f"{path}:{name}: cbor mismatch {actual} != {expected}")
        elif kind == "encode_fail":
            tag = row.get("expect", {}).get("tag")
            if tag not in ENCODE_TAGS:
                raise ParityValidationError(f"{path}:{name}: unknown encode tag {tag!r}")
            ints = [value["n"], *value["by_id"].keys(), *value["by_id"].values()]
            if all(INT_MIN <= item <= INT_MAX for item in ints):
                raise ParityValidationError(f"{path}:{name}: encode_fail value is inside i64 range")
        else:
            raise ParityValidationError(f"{path}:{name}: unknown kind {kind!r}")
        count += 1
    return count


def validate_malformed_vectors(path: Path = MALFORMED_VECTORS) -> int:
    data = _load_json(path)
    if data.get("version") != 1:
        raise ParityValidationError(f"{path}: unsupported version {data.get('version')!r}")
    schema = load_schema(ROOT / data["schema_path"])
    count = 0
    names: set[str] = set()
    for row in data.get("vectors", []):
        name = row.get("name", "<unnamed>")
        if name in names:
            raise ParityValidationError(f"{path}:{name}: duplicate row name")
        names.add(name)
        stage = row.get("stage")
        if stage not in {"raw_decode", "from_cbor", "from_wire"}:
            raise ParityValidationError(f"{path}:{name}: bad stage {stage!r}")
        _hex(row.get("bytes"), f"{path}:{name}.bytes")
        _check_expect(row.get("expect"), f"{path}:{name}.expect")
        entrypoint = row.get("schema")
        if stage == "from_cbor" and entrypoint not in schema.messages:
            raise ParityValidationError(f"{path}:{name}: unknown message {entrypoint!r}")
        if stage == "from_wire" and entrypoint not in schema.enums:
            raise ParityValidationError(f"{path}:{name}: unknown enum {entrypoint!r}")
        if not row.get("why"):
            raise ParityValidationError(f"{path}:{name}: missing why")
        count += 1
    return count


def target_statuses(path: Path = ALLOWLIST) -> list[ParityStatus]:
    data = _load_json(path)
    if data.get("version") != 1:
        raise ParityValidationError(f"{path}: unsupported version {data.get('version')!r}")
    entries: dict[str, dict[str, Any]] = {}
    for row in data.get("targets", []):
        target = row.get("target")
        if target in entries:
            raise ParityValidationError(f"{path}: duplicate target {target}")
        entries[target] = row
    unknown = sorted(set(entries) - set(TARGETS))
    if unknown:
        raise ParityValidationError(f"{path}: unknown target(s) {unknown}")
    statuses: list[ParityStatus] = []
    for target in TARGETS:
        row = entries.get(target)
        if row is None:
            statuses.append(ParityStatus(target, "gated", "shared replay harness enforced"))
            continue
        for key in ("reason", "phase", "owner"):
            if not isinstance(row.get(key), str) or not row[key]:
                raise ParityValidationError(f"{path}: {target} has no allowlist {key}")
        statuses.append(ParityStatus(target, "allowlisted", row["reason"], row["phase"], row["owner"]))
    return statuses


def allowlisted_targets(path: Path = ALLOWLIST) -> set[str]:
    return {s.target for s in target_statuses(path) if s.status == "allowlisted"}


# --- reports --------------------------------------------------------------------

PASS, FAIL, TYPE_SATISFIED = "pass", "fail", "type-satisfied"  # a judged row's status
OK, ERR, UNTYPED = "ok", "err", "untyped"                      # a malformed row's outcome
NO_REPORT = "no report"


@dataclass(frozen=True)
class VectorResult:
    name: str
    kind: str          # "round_trip" | "encode_fail" | "malformed"
    expected_tag: str  # the expected tag; "accept" for an accept row; "" for round_trip
    status: str        # PASS | FAIL | TYPE_SATISFIED
    detail: str
    lead: bool


@dataclass
class TargetReport:
    target: str
    available: bool
    skip_reason: str = ""
    results: list[VectorResult] = field(default_factory=list)
    # A target-level failure (generation, build, exit status, stray report lines);
    # its first line labels it. Any fault makes the target RED.
    fault: str = ""

    @property
    def failures(self) -> list[VectorResult]:
        return [r for r in self.results if r.status == FAIL]

    @property
    def green(self) -> bool:
        return self.available and not self.fault and not self.failures

    @property
    def failed_tags(self) -> list[str]:
        return sorted({(r.expected_tag or r.name) for r in self.failures})


# --- what a runner needs: rows, dispatch, report parsing, the comparator ----------

def parity_schema() -> Any:
    """The fixture the vector files name (`ir/parity_int.taut.py`)."""
    data = _load_json(INT_VECTORS)
    return load_schema(ROOT / data["schema_path"])


def int_rows() -> list[dict]:
    return _load_json(INT_VECTORS)["vectors"]


def malformed_rows() -> list[dict]:
    return _load_json(MALFORMED_VECTORS)["vectors"]


@dataclass(frozen=True)
class Dispatch:
    """The fixture's typed entry points: a `from_cbor` row names a message and a
    `from_wire` row names an enum. Runners build their dispatch from this."""

    messages: tuple[str, ...]
    enums: tuple[str, ...]


def fixture_dispatch(schema: Any | None = None) -> Dispatch:
    schema = parity_schema() if schema is None else schema
    return Dispatch(tuple(schema.messages), tuple(schema.enums))


def write_json_rows(dest: Path, schema: Any | None = None) -> None:
    """For a runner that reads JSON: the two vector files and `dispatch.json`."""
    dispatch = fixture_dispatch(schema)
    (dest / "int.vectors.json").write_text(INT_VECTORS.read_text())
    (dest / "malformed.vectors.json").write_text(MALFORMED_VECTORS.read_text())
    (dest / "dispatch.json").write_text(
        json.dumps({"messages": list(dispatch.messages), "enums": list(dispatch.enums)}))


def format_error(tag: str, payload: Mapping[str, Any]) -> str:
    """An `err` detail: the tag, then `;field=value` for each payload field present."""
    return tag + "".join(f";{name}={payload[name]}" for name in PAYLOAD_FIELDS if name in payload)


def parse_error(detail: str) -> tuple[str, dict[str, str]]:
    tag, *fields = detail.split(";")
    payload: dict[str, str] = {}
    for item in fields:
        name, _, value = item.partition("=")
        payload[name] = value
    return tag, payload


def judge(target: str, row: Mapping[str, Any], outcome: str, detail: str) -> tuple[str, str]:
    """The comparator: (PASS or FAIL, why) for one malformed row's observation."""
    expect = row["expect"]
    want = "accept" if expect.get("accept") else format_error(expect["tag"], expect)
    if outcome == OK:
        return (PASS, "") if want == "accept" else (FAIL, f"decoded ok, expected {want}")
    if outcome == UNTYPED:
        return FAIL, f"untyped {detail}, expected {want}"
    if outcome != ERR:
        return FAIL, f"unknown outcome {outcome!r}, expected {want}"
    if want == "accept":
        return FAIL, f"got {detail}, expected accept"
    tag, payload = parse_error(detail)
    exempt = PAYLOAD_EXEMPT.get(target, frozenset())
    drift = [name for name in expect
             if name != "tag" and (tag, name) not in exempt and payload.get(name) != str(expect[name])]
    if tag != expect["tag"] or drift:
        return FAIL, f"got {detail}, expected {want}"
    return PASS, ""


def _row_index() -> dict[str, tuple[str, dict]]:
    """name -> (kind, row), int rows then malformed rows, in corpus order."""
    index: dict[str, tuple[str, dict]] = {}
    for kind, row in [*((r["kind"], r) for r in int_rows()), *(("malformed", r) for r in malformed_rows())]:
        if row["name"] in index:
            raise ParityValidationError(f"row name {row['name']!r} appears twice in the corpus")
        index[row["name"]] = (kind, row)
    return index


def _result(kind: str, row: Mapping[str, Any], status: str, detail: str) -> VectorResult:
    expect = row.get("expect", {})
    expected = "accept" if expect.get("accept") else expect.get("tag", "")
    return VectorResult(row["name"], kind, expected, status, detail, bool(row.get("lead")))


def _excerpt(text: str, limit: int = 800) -> str:
    """The start of a tool's output (where compilers and panics put the first error)."""
    text = (text or "").strip()
    if not text:
        return ""
    return "\n" + (text if len(text) <= limit else text[:limit] + " ...")


def parse_report(target: str, stdout: str, *, returncode: int = 0, stderr: str = "") -> TargetReport:
    """Judge a runner's report. Every row is reported exactly once, or it fails;
    a runner that exits non-zero, or reports rows the corpus lacks, fails its target."""
    rows = _row_index()
    judged: dict[str, VectorResult] = {}
    stray: list[str] = []
    for line in stdout.splitlines():
        if "\t" not in line:
            continue
        name, _, rest = line.partition("\t")
        outcome, _, detail = rest.partition("\t")
        if name not in rows:
            stray.append(name)
            continue
        kind, row = rows[name]
        if name in judged:
            judged[name] = _result(kind, row, FAIL, "reported more than once")
        elif kind == "malformed":
            judged[name] = _result(kind, row, *judge(target, row, outcome, detail))
        elif outcome in (PASS, FAIL, TYPE_SATISFIED):
            judged[name] = _result(kind, row, outcome, detail)
        else:
            judged[name] = _result(kind, row, FAIL, f"unknown outcome {outcome!r}")
    report = TargetReport(target, available=True)
    report.results = [judged.get(name) or _result(kind, row, FAIL, NO_REPORT)
                      for name, (kind, row) in rows.items()]
    faults = []
    if returncode != 0:
        faults.append(f"runner exited {returncode}{_excerpt(stderr)}")
    if stray:
        faults.append(f"runner reported rows the corpus lacks: {sorted(set(stray))}")
    report.fault = "\n".join(faults)
    return report


def skipped(target: str, reason: str) -> TargetReport:
    """A missing toolchain: the only way a target skips."""
    return TargetReport(target, available=False, skip_reason=reason)


def red(target: str, fault: str) -> TargetReport:
    """A target whose rows could not run (generation or build failed): RED, never a skip."""
    report = parse_report(target, "")
    report.fault = fault
    return report


def generate(target: str, out_dir: Path, **emit_options: Any) -> TargetReport | None:
    """Generate the fixture's `target` code into `out_dir/<target>`; None on success,
    else the RED report (a generator that refuses the fixture fails its target)."""
    from ..gen import scaffold

    try:
        scaffold.emit(parity_schema(), out_dir, langs=[target], services=[], **emit_options)
    except Exception as exc:  # noqa: BLE001 — any generator failure makes the target RED
        return red(target, f"generation failed\n{type(exc).__name__}: {exc}")
    return None


def _decoded(output: str | bytes | None) -> str:
    if isinstance(output, bytes):
        return output.decode(errors="replace")
    return output or ""


def build(target: str, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None = None,
          timeout: float = BUILD_TIMEOUT) -> TargetReport | None:
    """Run one build step; None on success, else the RED report."""
    try:
        done = subprocess.run(list(argv), cwd=cwd, env=env, capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return red(target, f"build failed\n{exc}")
    if done.returncode != 0:
        return red(target, f"build failed (exit {done.returncode}){_excerpt(done.stderr or done.stdout)}")
    return None


def run_runner(target: str, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None = None,
               timeout: float = RUN_TIMEOUT) -> TargetReport:
    """Run a built runner and judge its report."""
    try:
        done = subprocess.run(list(argv), cwd=cwd, env=env, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        report = parse_report(target, _decoded(exc.stdout))
        report.fault = f"runner timed out after {timeout:g}s"
        return report
    except OSError as exc:
        return red(target, f"runner did not start\n{exc}")
    return parse_report(target, done.stdout, returncode=done.returncode, stderr=done.stderr)


# --- Python harness (in-process, no subprocess) -----------------------------------

def _observe_python(schema: Any, row: Mapping[str, Any]) -> tuple[str, str]:
    """One malformed row through wire.cbor/wire.codec: (outcome, detail) as a runner reports it."""
    from ..ir.model import EnumRef

    data = bytes.fromhex(row["bytes"])
    try:
        if row["stage"] == "raw_decode":
            cbor.loads(data)
        elif row["stage"] == "from_cbor":
            codec.decode(schema, row["schema"], data)
        else:  # from_wire
            codec._from_wire(schema, EnumRef(row["schema"]), cbor.loads(data), strict=True)
    except cbor.DecodeError as exc:
        return ERR, format_error(exc.tag, exc.payload)
    except Exception as exc:  # noqa: BLE001 — anything but DecodeError is untyped
        return UNTYPED, f"{type(exc).__name__}: {exc}"
    return OK, ""


def run_python() -> TargetReport:
    schema = parity_schema()
    report = TargetReport("python", available=True)

    for row in int_rows():
        value = {"n": int(row["value"]["n"]),
                 "by_id": {int(k): int(v) for k, v in row["value"]["by_id"]}}
        if row["kind"] == "round_trip":
            try:
                wire = codec.encode(schema, row["message"], value)
                if wire.hex() != row["cbor"]:
                    status, detail = FAIL, f"encode {wire.hex()} != {row['cbor']}"
                elif codec.decode(schema, row["message"], wire) != value:
                    status, detail = FAIL, "decode mismatch"
                else:
                    status, detail = PASS, ""
            except Exception as exc:  # noqa: BLE001 — fail-closed check
                status, detail = FAIL, f"raised {type(exc).__name__}: {exc}"
        else:  # encode_fail
            tag = row["expect"]["tag"]
            try:
                codec.encode(schema, row["message"], value)
                status, detail = FAIL, "encoded, expected IntOutOfSubset"
            except codec.EncodeError as exc:
                status, detail = (PASS, "") if exc.tag == tag else (FAIL, f"tag {exc.tag} != {tag}")
            except Exception as exc:  # noqa: BLE001
                status, detail = FAIL, f"raised {type(exc).__name__}"
        report.results.append(_result(row["kind"], row, status, detail))

    for row in malformed_rows():
        outcome, observed = _observe_python(schema, row)
        report.results.append(_result("malformed", row, *judge("python", row, outcome, observed)))

    return report


# --- the registry -------------------------------------------------------------------

def _runner_module(target: str) -> str:
    return f"{__package__}.parity_{target}"


class _Runners(Mapping[str, Callable[[], TargetReport]]):
    """target -> run(): `run_python` in-process, else `taut.corpus.parity_<target>.run`
    when that module exists. A target with neither has no runner and is not run."""

    def __contains__(self, target: object) -> bool:
        if target == "python":
            return True
        return (isinstance(target, str) and target in TARGETS
                and importlib.util.find_spec(_runner_module(target)) is not None)

    def __getitem__(self, target: str) -> Callable[[], TargetReport]:
        if target not in self:
            raise KeyError(target)
        if target == "python":
            return run_python
        return importlib.import_module(_runner_module(target)).run

    def __iter__(self) -> Iterator[str]:
        return (target for target in TARGETS if target in self)

    def __len__(self) -> int:
        return sum(1 for _ in self)


_RUNNERS: Mapping[str, Callable[[], TargetReport]] = _Runners()


def run_targets(targets: Iterable[str]) -> dict[str, TargetReport]:
    """Run each target that has a runner; a target without one is left out, and a
    runner that raises is RED rather than stopping the other targets."""
    reports: dict[str, TargetReport] = {}
    for target in targets:
        if target not in _RUNNERS:
            continue
        try:
            reports[target] = _RUNNERS[target]()
        except Exception as exc:  # noqa: BLE001 — one broken runner must not hide the others
            reports[target] = red(target, f"runner raised\n{type(exc).__name__}: {exc}")
    return reports


# --- governance + summary -----------------------------------------------------

def _verdict(rep: TargetReport) -> str:
    if rep.green:
        return "GREEN"
    return "RED " + (rep.fault.splitlines()[0] if rep.fault else ",".join(rep.failed_tags))


def governance(reports: dict[str, TargetReport], allow: set[str]) -> list[str]:
    """Return governance violations. Empty == clean gate."""
    violations: list[str] = []
    for target, rep in reports.items():
        if not rep.available:
            continue  # skip-with-reason: not evaluated, neither pass nor fail
        if rep.green and target in allow:
            violations.append(f"{target}: PASSES fully but is allowlisted — remove it from allowlist.json")
        if not rep.green and target not in allow:
            violations.append(f"{target}: {_verdict(rep)} and is not allowlisted")
    return violations


def _summary(reports: dict[str, TargetReport], statuses: list[ParityStatus],
             int_count: int, mal_count: int) -> list[str]:
    lines = [
        f"int vectors: {int_count}    malformed vectors: {mal_count}",
        "",
        f"{'target':<11} {'status':<12} {'pass':>4} {'fail':>4} {'skip/type':>9}  observed",
    ]
    status_by = {s.target: s for s in statuses}
    for target in TARGETS:
        st = status_by[target]
        rep = reports.get(target)
        if rep is None:
            lines.append(f"{target:<11} {st.status:<12} {'-':>4} {'-':>4} {'not run':>9}  {st.reason}")
            continue
        if not rep.available:
            lines.append(f"{target:<11} {st.status:<12} {'-':>4} {'-':>4} {'skipped':>9}  {rep.skip_reason}")
            continue
        npass = sum(1 for r in rep.results if r.status == PASS)
        nfail = len(rep.failures)
        ntype = sum(1 for r in rep.results if r.status == TYPE_SATISFIED)
        lines.append(f"{target:<11} {st.status:<12} {npass:>4} {nfail:>4} {ntype:>9}  {_verdict(rep)}")
    # per-vector detail for any red target
    for target, rep in reports.items():
        if not rep.available or rep.green:
            continue
        lines.append("")
        lines.append(f"{target} failures:")
        lines += [f"  ! {line}" for line in rep.fault.splitlines()]
        unreported = [r.name for r in rep.failures if r.detail == NO_REPORT]
        for r in rep.failures:
            if r.detail != NO_REPORT:
                mark = " (lead)" if r.lead else ""
                lines.append(f"  - {r.name}{mark}: {r.detail}")
        if unreported and len(unreported) == len(rep.results):
            lines.append(f"  - no row reported ({len(unreported)} rows)")
        elif unreported:
            lines.append(f"  - {len(unreported)} row(s) never reported: {', '.join(unreported)}")
    return lines


@dataclass
class GateOutcome:
    lines: list[str]
    violations: list[str]
    reports: dict[str, TargetReport]


def run_gate(*, target: str | None = None, run_compiled: bool = True) -> GateOutcome:
    """Validate the artifacts, run the runners and judge governance. By default every
    target that has a runner; `run_compiled=False` runs Python only."""
    if target is not None and target not in TARGETS:
        raise ParityValidationError(f"unknown target {target!r}; known: {', '.join(TARGETS)}")
    int_count = validate_int_vectors()
    mal_count = validate_malformed_vectors()
    statuses = target_statuses()
    allow = {s.target for s in statuses if s.status == "allowlisted"}

    if target is not None:
        wanted: tuple[str, ...] = (target,)
    elif run_compiled:
        wanted = TARGETS
    else:
        wanted = ("python",)
    reports = run_targets(wanted)

    violations = governance(reports, allow)
    lines = _summary(reports, statuses, int_count, mal_count)
    if violations:
        lines.append("")
        lines.append("GOVERNANCE VIOLATIONS (gate fails):")
        lines += [f"  - {v}" for v in violations]
    else:
        lines.append("")
        lines.append("governance: clean (no gated target failing, no green target allowlisted)")
    return GateOutcome(lines, violations, reports)


# --- back-compat: validate-only view (used by artifact tests) -----------------

def validate_all(*, target: str | None = None) -> list[str]:
    if target is not None and target not in TARGETS:
        raise ParityValidationError(f"unknown target {target!r}; known: {', '.join(TARGETS)}")
    int_count = validate_int_vectors()
    malformed_count = validate_malformed_vectors()
    statuses = [s for s in target_statuses() if target is None or s.target == target]
    lines = [f"int vectors: {int_count}", f"malformed vectors: {malformed_count}"]
    for status in statuses:
        lines.append(f"{status.target}: {status.status} - {status.reason}")
    return lines
