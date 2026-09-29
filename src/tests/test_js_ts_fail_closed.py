"""JavaScript and TypeScript fail closed (TautCheckedDecode.md CD-E3, CD-E4): for any input
bytes, every decode entry point returns a value or throws a DecodeError, recognised by name and
tag, and nothing else, and it reports what Python, the reference, reports.

The parity rows pin chosen inputs; this audit runs many, all deterministic (AUDIT_SEED): the
parity corpus's bytes; the fixture's messages, valid and with a value replaced, a key dropped or
a key added; each of those cut short, with a byte changed or with a head spliced in; and random
bytes. Each input goes through every entry point: the raw decode, each message's typed decode,
the enum's, TypeScript's `decodeRef` at roots that are not messages, and the three extension
helpers with the input as their host. Deep nesting is TooDeep in both, which each language's D1
bounded.
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from taut import cli, ext
from taut.ir.export import export_to
from taut.ir.load import load_schema
from taut.ir.model import EnumRef, ListOf, MapOf, MsgRef, Scalar, TypeRef
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec

ROOT = Path(__file__).resolve().parents[2]
PARITY_IR = ROOT / "ir" / "parity_int.taut.py"
VECTORS = [ROOT / "corpus" / "parity" / name for name in ("int.vectors.json", "malformed.vectors.json")]
SCHEMA = load_schema(PARITY_IR)
# The fixture's messages and enum at the default bounds. The bounds rows' messages declare
# their own bounds, which JavaScript and TypeScript apply only from D1, so they are D1's.
MESSAGES = ("IntBox", "EnumBox", "OptBox", "Empty", "Late", "Shapes", "Names")
ENUMS = ("Mode",)
AUDIT_SEED = 0xD2_0FC
EXT_TAG = BAND_START + 1
# A DecodeError's payload fields, in the order a harness reports them: the gate's, then D1's
# `limit` and `len` (TautCheckedDecode.md CD-E1).
PAYLOAD = ("info", "major", "key", "expected", "enum", "value", "limit", "len")
# Roots that are not a message or an enum, as an RPC slot's may be (TypeScript's decodeRef):
# each as the IR's TypeRef and as TypeScript's.
ROOTS: dict[str, tuple[TypeRef, dict[str, Any]]] = {
    "list<EnumBox>": (ListOf(MsgRef("EnumBox")), {"k": "list", "elem": {"k": "msg", "name": "EnumBox"}}),
    "map<str,int>": (MapOf(Scalar("str"), Scalar("int")),
                     {"k": "map", "key": {"k": "scalar", "scalar": "str"}, "value": {"k": "scalar", "scalar": "int"}}),
}
# 100,000 nested arrays, and as many nested maps, around an int: far past any bound, and past
# node's stack.
DEEP = ["81" * 100_000 + "00", "a101" * 100_000 + "00"]
D1_DEPTH = ("D1 (TautV010Plan.md Phase D): deep nesting overflows node's stack, a RangeError, "
            "until the depth bound makes it TooDeep")

# The values a mutation puts in a message's place: one of each CBOR type, empty and not.
_ODD = [0, -1, 2**63 - 1, "x", b"\x01", True, None, 1.5, [], {}, [1, "a"], {1: 2}, {1: "a", 2: 1}]
# Heads a byte mutation splices in: 8-byte arguments at their extremes, a float, a tag, a
# break, undefined, reserved info, an open map and array, bad UTF-8, and map keys at the edges.
_HEADS = [bytes.fromhex(h) for h in (
    "1bffffffffffffffff", "3bffffffffffffffff", "5b0020000000000000", "7bffffffffffffffff",
    "9bffffffffffffffff", "bbffffffffffffffff", "f97e00", "fa7fc00000", "fb", "c0", "ff", "f7",
    "1c", "a1", "81", "61ff", "a11b0020000000000000", "a120", "a16178")]
# Valid at the roots that are not messages: a Mode, a list<EnumBox>, a map<str,int>.
_ROOT_SEEDS = [cbor.dumps(v) for v in (0, 1, [], [{1: 1}], [{1: "a", 2: 5}])]


def _native(rng: random.Random, t: TypeRef) -> Any:
    """A random valid native value of type `t`."""
    if isinstance(t, Scalar):
        return rng.choice({
            "int": [0, -1, 23, 2**53, -(2**63), 2**63 - 1],
            "float": [0.0, -0.0, 1.5, float("inf")],
            "str": ["", "a", "é", "\U00010000"],
            "bytes": [b"", b"\x00\xff"],
            "bool": [False, True],
        }[t.kind])
    if isinstance(t, EnumRef):
        return rng.choice(list(SCHEMA.enums[t.name].members))
    if isinstance(t, ListOf):
        return [_native(rng, t.elem) for _ in range(rng.randrange(3))]
    if isinstance(t, MapOf):
        return {_native(rng, t.key): _native(rng, t.value) for _ in range(rng.randrange(3))}
    return {f.name: None if f.optional and rng.random() < 0.3 else _native(rng, f.type)
            for f in SCHEMA.messages[t.name].wire_fields()}


def _mutated(rng: random.Random, tree: Any) -> Any:
    """A copy of `tree`, a decoded message, with one change at a random place: a value
    replaced, or in a map a key dropped or one added."""
    tree = cbor.loads(cbor.dumps(tree))
    spots: list[tuple[Any, Any]] = []

    def walk(node: Any) -> None:
        items = node.items() if isinstance(node, dict) else enumerate(node) if isinstance(node, list) else ()
        for key, value in list(items):
            spots.append((node, key))
            walk(value)

    walk(tree)
    if not spots:
        return rng.choice(_ODD)
    node, key = rng.choice(spots)
    change = rng.randrange(3)
    if change == 1 and isinstance(node, dict):
        del node[key]
    elif change == 2 and isinstance(node, dict):
        node[rng.choice([0, 3, 99, EXT_TAG, 2**53])] = rng.choice(_ODD)
    else:
        node[key] = rng.choice(_ODD)
    return tree


def _cut_changed_or_spliced(rng: random.Random, data: bytes) -> bytes:
    """`data` cut short, with a byte changed, or with a head or random bytes spliced in."""
    out = bytearray(data)
    change = rng.randrange(4)
    at = rng.randrange(len(out) + 1)
    if change == 0:
        del out[at:]
    elif change == 1 and out:
        out[rng.randrange(len(out))] = rng.randrange(256)
    elif change == 2:
        out[at:at] = rng.choice(_HEADS)
    else:
        out[at:at] = rng.randbytes(rng.randrange(1, 4))
    return bytes(out)


def _audit_inputs() -> list[bytes]:
    rng = random.Random(AUDIT_SEED)
    seeds = [bytes.fromhex(row["bytes"] if "bytes" in row else row["cbor"])
             for path in VECTORS for row in json.loads(path.read_text())["vectors"]
             if "bytes" in row or "cbor" in row]
    seeds += _ROOT_SEEDS
    for name in MESSAGES:
        for _ in range(40):
            tree = cbor.loads(codec.encode(SCHEMA, name, _native(rng, MsgRef(name))))
            seeds += [cbor.dumps(tree), cbor.dumps(_mutated(rng, tree))]
    inputs = set(seeds)
    for data in seeds:
        inputs.update(_cut_changed_or_spliced(rng, data) for _ in range(2))
    inputs.update(rng.randbytes(rng.randrange(12)) for _ in range(200))
    return sorted(inputs)


def _outcome(fn: Any, *args: Any) -> str:
    """`fn(*args)`'s outcome as a harness reports it: `ok`, or a DecodeError's tag and payload.
    Python is the reference, so anything else it raises fails the test."""
    try:
        fn(*args)
    except cbor.DecodeError as exc:
        return exc.tag + "".join(f";{name}={exc.payload[name]}" for name in PAYLOAD if name in exc.payload)
    return "ok"


def _python(data: bytes) -> dict[str, str]:
    """Python's outcome for `data` at each entry point a harness calls. The extension helpers
    of JavaScript and TypeScript never decode the extension, so `ext_clear` is theirs."""
    seen = {"raw": _outcome(cbor.loads, data), "ext": _outcome(ext.ext_clear, data, EXT_TAG)}
    for name in MESSAGES:
        seen[name] = _outcome(codec.decode, SCHEMA, name, data)
    for name in ENUMS:
        seen[name] = _outcome(codec.decode_ref, SCHEMA, EnumRef(name), data)
    for name, (tref, _) in ROOTS.items():
        seen[name] = _outcome(codec.decode_ref, SCHEMA, tref, data)
    return seen


def _js_view(seen: dict[str, str]) -> dict[str, str]:
    """The entry points JavaScript has: every one but decodeRef's other roots."""
    return {point: outcome for point, outcome in seen.items() if point not in ROOTS}


# Each harness reports, per input, each entry point's outcome as `_outcome` does, and an
# untyped description for anything but a DecodeError. The three extension helpers read a host
# alike, so they report one outcome, or each of theirs if they differ. The same source serves
# both harnesses: node strips types without checking them.
_OUTCOME = """
function outcome(call) {
  try {
    call();
  } catch (e) {
    if (e == null || e.name !== "DecodeError" || typeof e.tag !== "string") {
      return `untyped ${e && e.name}: ${e && e.message}`;
    }
    return e.tag + payload.filter((f) => e[f] !== undefined).map((f) => `;${f}=${String(e[f])}`).join("");
  }
  return "ok";
}

function hostOutcome(data, emptyMap) {
  const seen = new Set([
    outcome(() => extGet(data, extTag)),
    outcome(() => extSet(data, extTag, emptyMap)),
    outcome(() => extClear(data, extTag)),
  ]);
  return [...seen].join(" | ");
}
"""

_JS_HARNESS = """
"use strict";
const api = require("./api.js");
const { CMap, decode } = require("./cbor.js");
const { extClear, extGet, extSet } = require("./ext.js");
const { inputs, messages, enums, extTag, payload } = require("./audit.json");
""" + _OUTCOME + """
const report = inputs.map((hex) => {
  const data = Uint8Array.from(Buffer.from(hex, "hex"));
  const seen = { raw: outcome(() => decode(data)), ext: hostOutcome(data, CMap([])) };
  for (const name of messages) {
    seen[name] = outcome(() => api[name].decode(data));
  }
  for (const name of enums) {
    seen[name] = outcome(() => api[`${name}FromCbor`](decode(data)));
  }
  return seen;
});
console.log(JSON.stringify(report));
"""

_TS_HARNESS = """
import { readFileSync } from "node:fs";
import { decode as cborDecode } from "./cbor.ts";
import { decode, decodeRef } from "./codec.ts";
import { extClear, extGet, extSet } from "./ext.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("parity_int.ir.json", "utf8")));
const { inputs, messages, enums, roots, extTag, payload } = JSON.parse(readFileSync("audit.json", "utf8"));
""" + _OUTCOME + """
const report = inputs.map((hex: string) => {
  const data = Uint8Array.from(Buffer.from(hex, "hex"));
  const seen: Record<string, string> = { raw: outcome(() => cborDecode(data)), ext: hostOutcome(data, new Map()) };
  for (const name of messages) {
    seen[name] = outcome(() => decode(schema, name, data));
  }
  for (const name of enums) {
    seen[name] = outcome(() => decodeRef(schema, { k: "enum", name }, data));
  }
  for (const [name, ref] of Object.entries(roots)) {
    seen[name] = outcome(() => decodeRef(schema, ref as any, data));
  }
  return seen;
});
console.log(JSON.stringify(report));
"""


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    return node


def _report(cwd: Path, argv: list[str], inputs: list[str]) -> list[dict[str, str]]:
    """Run a harness in `cwd` over `inputs` and return its report."""
    (cwd / "audit.json").write_text(json.dumps({
        "inputs": inputs,
        "messages": list(MESSAGES),
        "enums": list(ENUMS),
        "roots": {name: ref for name, (_, ref) in ROOTS.items()},
        "extTag": EXT_TAG,
        "payload": list(PAYLOAD),
    }))
    done = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    report = json.loads(done.stdout)
    assert len(report) == len(inputs)
    return report


def _js_report(tmp_path: Path, inputs: list[str], *, forward_compat: bool = False) -> list[dict[str, str]]:
    node = _node()
    argv = ["gen", str(PARITY_IR), "-o", str(tmp_path), "--lang", "js", "--api-only", "--with-runtime"]
    assert cli.main(argv + (["--forward-compat"] if forward_compat else [])) == 0
    js_dir = tmp_path / "js"
    (js_dir / "audit.js").write_text(_JS_HARNESS)
    return _report(js_dir, [node, "audit.js"], inputs)


def _ts_report(tmp_path: Path, inputs: list[str]) -> list[dict[str, str]]:
    node = _node()
    argv = ["gen", str(PARITY_IR), "-o", str(tmp_path), "--lang", "typescript", "--api-only", "--with-runtime"]
    assert cli.main(argv) == 0
    ts_dir = tmp_path / "typescript"
    export_to(SCHEMA, ts_dir / "parity_int.ir.json")
    (ts_dir / "audit.ts").write_text(_TS_HARNESS)
    return _report(ts_dir, [node, "--experimental-strip-types", "audit.ts"], inputs)


def _mismatches(inputs: list[str], report: list[dict[str, str]],
                expected: list[dict[str, str]]) -> list[tuple[str, str, str | None, str | None]]:
    """(input, entry point, got, Python's) wherever a harness and Python differ."""
    out = []
    for hex_bytes, got, want in zip(inputs, report, expected):
        for point in sorted(set(got) | set(want)):
            if got.get(point) != want.get(point):
                out.append((hex_bytes[:60], point, got.get(point), want.get(point)))
    return out


@pytest.fixture(scope="module")
def audit() -> tuple[list[str], list[dict[str, str]]]:
    """The audit's inputs, as hex, and Python's outcomes for each."""
    inputs = _audit_inputs()
    return [data.hex() for data in inputs], [_python(data) for data in inputs]


def test_the_audit_reaches_every_tag_and_every_entry_point_accepts_some_input(audit):
    """Not vacuous: Python refuses the inputs with every tag, and accepts some at each point."""
    _, python = audit
    assert len(python) > 1500
    assert {outcome.split(";")[0] for seen in python for outcome in seen.values()} == {
        "ok", "Truncated", "TrailingBytes", "InvalidUtf8", "UnsupportedInfo", "UnsupportedMajor",
        "NonIntegerMapKey", "IntOverflow", "DuplicateMapKey", "MissingKey", "WrongType", "UnknownEnum",
        "NonCanonicalInt", "NegativeMapKey"}
    for point in python[0]:
        outcomes = {seen[point].split(";")[0] for seen in python}
        assert "ok" in outcomes and len(outcomes) > 2, point


@pytest.mark.parametrize("forward_compat", [False, True], ids=["js", "js-fc"])
def test_js_decode_entry_points_throw_only_what_python_raises(tmp_path, audit, forward_compat):
    inputs, python = audit
    report = _js_report(tmp_path, inputs, forward_compat=forward_compat)
    assert _mismatches(inputs, report, [_js_view(seen) for seen in python]) == []


def test_typescript_decode_entry_points_throw_only_what_python_raises(tmp_path, audit):
    inputs, python = audit
    assert _mismatches(inputs, _ts_report(tmp_path, inputs), python) == []


def test_js_deep_nesting_is_too_deep_at_every_entry_point(tmp_path):
    report = _js_report(tmp_path, DEEP)
    assert _mismatches(DEEP, report, [_js_view(_python(bytes.fromhex(h))) for h in DEEP]) == []


def test_typescript_deep_nesting_is_too_deep_at_every_entry_point(tmp_path):
    """TooDeep{32} at every root with the default bounds, and TooDeep{128} for the extension
    helpers, which read a host at the ceiling (TautOptions.md G3)."""
    report = _ts_report(tmp_path, DEEP)
    assert _mismatches(DEEP, report, [_python(bytes.fromhex(h)) for h in DEEP]) == []
