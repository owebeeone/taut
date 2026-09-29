"""TypeScript runtime-resource ResExt tests."""

from __future__ import annotations

import copy
import itertools
import json
import random
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from taut import cli, ext
from taut.corpus import parity, parity_typescript, toolchains
from taut.corpus import resext_build as rb
from taut.gen import scaffold
from taut.ir.dsl import (
    BOOL, BYTES, INT, MISSING_OK, STR, F, List, Map, Msg, Params, Ref, method, option, schema, service,
)
from taut.ir.export import export_to
from taut.ir.load import load_schema
from taut.ir.model import ListOf, MsgRef, Scalar, TypeRef
from taut.ir.options import DEFAULT_MAX_DEPTH, MAX_DEPTH_CEILING, effective_map
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec


SEED = 0x7A17_2E57
FUZZ_ITERS = 1000
ROOT = Path(__file__).resolve().parents[2]
PARITY_IR_PATH = ROOT / "ir" / "parity_int.taut.py"
PARITY_INT_VECTORS = ROOT / "corpus" / "parity" / "int.vectors.json"
PARITY_MALFORMED_VECTORS = ROOT / "corpus" / "parity" / "malformed.vectors.json"


def _rand_scalar(rng: random.Random) -> Any:
    choice = rng.randrange(6)
    if choice == 0:
        return rng.randrange(-5000, 5001)
    if choice == 1:
        return f"s{rng.randrange(10000)}"
    if choice == 2:
        return bytes(rng.randrange(256) for _ in range(rng.randrange(0, 8)))
    if choice == 3:
        return rng.choice([True, False])
    if choice == 4:
        return None
    return [rng.randrange(-20, 21), f"a{rng.randrange(100)}"]


def _random_host_map(rng: random.Random, *, avoid: set[int] | None = None) -> dict[int, Any]:
    avoid = avoid or set()
    host: dict[int, Any] = {
        1: rng.randrange(0, 100000),
        2: f"name-{rng.randrange(100000)}",
        5: rng.randrange(-1000, 1001),
    }
    host[3] = _rand_scalar(rng)  # required interleaved unknown between known tags 2 and 5
    band = BAND_START + rng.randrange(1, 50000)
    if band not in avoid:
        host[band] = _rand_scalar(rng)  # required band-tag residual
    for _ in range(rng.randrange(0, 4)):
        tag = rng.randrange(0, 2**21)
        if tag in {1, 2, 3, 5} or tag in avoid:
            continue
        host[tag] = _rand_scalar(rng)
    return host


def _resext_fuzz_rows(schema: Any) -> dict[str, Any]:
    rng = random.Random(SEED)
    residual_rows = []
    ext_rows = []
    for i in range(FUZZ_ITERS):
        residual_host = _random_host_map(rng)
        residual_wire = cbor.dumps(residual_host)
        residual_rows.append({
            "note": f"seed={SEED} iter={i}",
            "message": "Host",
            "wire": residual_wire.hex(),
        })

        tag = BAND_START + 1 + rng.randrange(0, 100000)
        ext_host = _random_host_map(rng, avoid={tag})
        host_wire = cbor.dumps(ext_host)
        decision = {"backend": f"b{rng.randrange(100000)}", "hops": rng.randrange(0, 100)}
        set_expect = ext.ext_set(schema, host_wire, "Decision", tag, decision)
        got = ext.ext_get(schema, set_expect, "Decision", tag)
        assert got == decision
        clear_expect = ext.ext_clear(set_expect, tag)
        ext_rows.append({
            "note": f"seed={SEED} iter={i}",
            "host": host_wire.hex(),
            "tag": tag,
            "value": codec.encode(schema, "Decision", decision).hex(),
            "set_expect": set_expect.hex(),
            "get_expect": codec.encode(schema, "Decision", got).hex(),
            "clear_expect": clear_expect.hex(),
        })
    return {"seed": SEED, "residual": residual_rows, "ext": ext_rows}


def _write_resext_harness(ts_dir: Path) -> Path:
    harness = ts_dir / "resext.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { CborFloat, decode as cborDecode, encode as cborEncode } from "./cbor.ts";
import { decode, decodeRef, encode, encodeRef } from "./codec.ts";
import { loadSchema } from "./schema.ts";
import { BAND_START, extClear, extGet, extSet } from "./ext.ts";

const schema = loadSchema(JSON.parse(readFileSync("resext.ir.json", "utf8")));
const vectors = JSON.parse(readFileSync("resext_vectors.json", "utf8"));
const decisionRef = { k: "msg", name: "Decision" } as const;

function hexToBytes(hex: string): Uint8Array {
  return Uint8Array.from(Buffer.from(hex, "hex"));
}

function bytesToHex(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString("hex");
}

function nestedDecisionFromWire(hex: string) {
  const decision = decodeRef(schema, decisionRef, hexToBytes(hex));
  return cborDecode(encodeRef(schema, decisionRef, decision));
}

function decisionWireFromNested(value: unknown): string {
  const decision = decodeRef(schema, decisionRef, cborEncode(value as never));
  return bytesToHex(encodeRef(schema, decisionRef, decision));
}

test("vendored TypeScript runtime encodes deterministic CBOR", () => {
  const input = new Map([[3, new CborFloat(1.5)], [1, "ok"]]);
  const encoded = cborEncode(input);
  assert.equal(bytesToHex(encoded), "a201626f6b03f93e00");

  const decoded = cborDecode(encoded);
  assert.ok(decoded instanceof Map);
  assert.equal(decoded.get(1), "ok");
  assert.ok(decoded.get(3) instanceof CborFloat);
  assert.equal(decoded.get(3).value, 1.5);
});

test("ResExt residual corpus round-trips byte-for-byte", () => {
  for (const row of vectors.residual) {
    const native = decode(schema, row.message, hexToBytes(row.wire));
    assert.equal(bytesToHex(encode(schema, row.message, native)), row.wire, row.note);
  }
});

test("ResExt extension corpus matches the Python oracle", () => {
  for (const row of vectors.ext) {
    const host = hexToBytes(row.host);
    if (row.op === "set") {
      const nested = nestedDecisionFromWire(row.value);
      const wire = extSet(host, row.tag, nested);
      assert.equal(bytesToHex(wire), row.expect, row.note);

      const decoded = cborDecode(wire);
      assert.ok(decoded instanceof Map, row.note);
      const bandValue = decoded.get(row.tag);
      assert.ok(bandValue instanceof Map, `${row.note}: band value must be a nested map`);
      assert.ok(!(bandValue instanceof Uint8Array), `${row.note}: band value must not be bytes`);
    } else if (row.op === "get") {
      const got = extGet(host, row.tag);
      if (row.expect === "null") {
        assert.equal(got, null, row.note);
      } else {
        assert.notEqual(got, null, row.note);
        assert.equal(decisionWireFromNested(got), row.expect, row.note);
      }
    } else if (row.op === "clear") {
      assert.equal(bytesToHex(extClear(host, row.tag)), row.expect, row.note);
    } else {
      assert.fail(`unknown op ${row.op}`);
    }
  }
});

// A tag below the band is the caller's error, a RangeError thrown before the host is read
// (TautCheckedDecode.md CD-E4).
test("extension accessors reject below-band tags before host decode", () => {
  const invalidHost = hexToBytes("ff");
  const nested = new Map();
  const belowBand = { name: "RangeError", message: /below the band/ };
  assert.throws(() => extSet(invalidHost, BAND_START - 1, nested), belowBand);
  assert.throws(() => extGet(invalidHost, BAND_START - 1), belowBand);
  assert.throws(() => extClear(invalidHost, BAND_START - 1), belowBand);
});

// A host that is not a map is WrongType{map}, a DecodeError like any bad host (CD-E4).
test("extension accessors reject non-map hosts with WrongType{map}", () => {
  const nested = new Map();
  const notAMap = { name: "DecodeError", tag: "WrongType", expected: "map" };
  for (const hex of ["01", "20", "80", "6161", "41ff", "f5", "f6", "f93e00"]) {
    const host = hexToBytes(hex);
    assert.throws(() => extSet(host, BAND_START + 1, nested), notAMap, hex);
    assert.throws(() => extGet(host, BAND_START + 1), notAMap, hex);
    assert.throws(() => extClear(host, BAND_START + 1), notAMap, hex);
  }
});

test("fixed-seed ResExt fuzz matches the Python oracle", () => {
  assert.equal(vectors.fuzz.seed, 0x7A172E57);
  assert.ok(vectors.fuzz.residual.length >= 1000);
  assert.ok(vectors.fuzz.ext.length >= 1000);

  for (const row of vectors.fuzz.residual) {
    const native = decode(schema, row.message, hexToBytes(row.wire));
    assert.equal(bytesToHex(encode(schema, row.message, native)), row.wire, row.note);
  }

  for (const row of vectors.fuzz.ext) {
    const nested = nestedDecisionFromWire(row.value);
    const setWire = extSet(hexToBytes(row.host), row.tag, nested);
    assert.equal(bytesToHex(setWire), row.set_expect, row.note);

    const decoded = cborDecode(setWire);
    assert.ok(decoded instanceof Map, row.note);
    const bandValue = decoded.get(row.tag);
    assert.ok(bandValue instanceof Map, `${row.note}: band value must be a nested map`);
    assert.ok(!(bandValue instanceof Uint8Array), `${row.note}: band value must not be bytes`);

    const got = extGet(setWire, row.tag);
    assert.notEqual(got, null, row.note);
    assert.equal(decisionWireFromNested(got), row.get_expect, row.note);
    assert.equal(bytesToHex(extClear(setWire, row.tag)), row.clear_expect, row.note);
  }
});
""".lstrip()
    )
    return harness


def _write_parity_harness(ts_dir: Path) -> Path:
    harness = ts_dir / "parity.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { decode as cborDecode } from "./cbor.ts";
import { decode, decodeRef, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("parity_int.ir.json", "utf8")));
const intVectors = JSON.parse(readFileSync("int.vectors.json", "utf8"));
const malformedVectors = JSON.parse(readFileSync("malformed.vectors.json", "utf8"));

function hexToBytes(hex: string): Uint8Array {
  return Uint8Array.from(Buffer.from(hex, "hex"));
}

function bytesToHex(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString("hex");
}

function intBox(value: { n: string; by_id: [string, string][] }) {
  return {
    n: BigInt(value.n),
    by_id: new Map(value.by_id.map(([k, v]) => [BigInt(k), BigInt(v)])),
  };
}

function assertParityError(fn: () => unknown, expect: Record<string, unknown>, note: string): void {
  let thrown: any = null;
  try {
    fn();
  } catch (e) {
    thrown = e;
  }
  assert.notEqual(thrown, null, `${note}: expected an error`);
  assert.equal(thrown.tag, expect.tag, `${note}: tag`);
  for (const [key, value] of Object.entries(expect)) {
    if (key === "tag") continue;
    assert.equal(String(thrown[key]), String(value), `${note}: ${key}`);
  }
}

test("shared i64 vectors round-trip exactly with bigint carriers", () => {
  for (const row of intVectors.vectors) {
    const native = intBox(row.value);
    if (row.kind === "round_trip") {
      const encoded = encode(schema, row.message, native);
      assert.equal(bytesToHex(encoded), row.cbor, row.name);
      const decoded = decode(schema, row.message, hexToBytes(row.cbor));
      assert.deepEqual(decoded, native, row.name);
      assert.equal(bytesToHex(encode(schema, row.message, decoded)), row.cbor, row.name);
    } else if (row.kind === "encode_fail") {
      assertParityError(() => encode(schema, row.message, native), row.expect, row.name);
    } else {
      assert.fail(`unknown vector kind ${row.kind}`);
    }
  }
});

test("shared malformed vectors fail closed with typed tags", () => {
  for (const row of malformedVectors.vectors) {
    assertParityError(() => {
      const data = hexToBytes(row.bytes);
      if (row.stage === "raw_decode") {
        return cborDecode(data);
      }
      if (row.stage === "from_cbor") {
        return decode(schema, row.schema, data);
      }
      if (row.stage === "from_wire") {
        return decodeRef(schema, { k: "enum", name: row.schema }, data);
      }
      assert.fail(`unknown vector stage ${row.stage}`);
    }, row.expect, row.name);
  }
});
""".lstrip()
    )
    return harness


def test_typescript_codec_parity_i64_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    schema = load_schema(PARITY_IR_PATH)
    assert cli.main([
        "gen",
        str(PARITY_IR_PATH),
        "-o",
        str(tmp_path),
        "--lang",
        "typescript",
        "--api-only",
        "--with-runtime",
    ]) == 0

    ts_dir = tmp_path / "typescript"
    api = (ts_dir / "api.ts").read_text()
    assert "n: bigint;" in api
    assert "by_id: Map<bigint, bigint>;" in api

    export_to(schema, ts_dir / "parity_int.ir.json")
    # Baseline smoke test: pin the reviewed set; `lead` rows belong to the
    # governed `tautc parity` gate (corpus/parity/gen_vectors.py).
    for name, src in [("int.vectors.json", PARITY_INT_VECTORS), ("malformed.vectors.json", PARITY_MALFORMED_VECTORS)]:
        doc = json.loads(src.read_text())
        doc["vectors"] = [r for r in doc["vectors"] if not r.get("lead")]
        (ts_dir / name).write_text(json.dumps(doc))
    harness = _write_parity_harness(ts_dir)

    subprocess.run(
        [node, "--experimental-strip-types", "--test", str(harness.name)],
        cwd=ts_dir,
        check=True,
        text=True,
        capture_output=True,
    )


def test_typescript_runtime_resext_phase2_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    schema = load_schema(rb.IR_PATH)
    assert cli.main([
        "gen",
        str(rb.IR_PATH),
        "-o",
        str(tmp_path),
        "--lang",
        "typescript",
        "--api-only",
        "--with-runtime",
        "--forward-compat",
    ]) == 0

    ts_dir = tmp_path / "typescript"
    assert (ts_dir / "ext.ts").exists()
    export_to(schema, ts_dir / "resext.ir.json")
    (ts_dir / "resext_vectors.json").write_text(json.dumps({
        "residual": json.loads(rb.RESIDUAL_PATH.read_text()),
        "ext": json.loads(rb.EXT_PATH.read_text()),
        "fuzz": _resext_fuzz_rows(schema),
    }))
    harness = _write_resext_harness(ts_dir)

    subprocess.run(
        [node, "--experimental-strip-types", "--test", str(harness.name)],
        cwd=ts_dir,
        check=True,
        text=True,
        capture_output=True,
    )


def _late_schema():
    """`Late` opts in to MISSING_OK (TautCheckedDecode.md M16, M17); `Opt`, a plain
    optional field, is the contrast (M11)."""
    return schema(
        Msg("Late", F("note", 1, STR, optional=MISSING_OK), next_id=2),
        Msg("Opt", F("note", 1, STR, optional=True), next_id=2),
    )


def _emit_ts(s: Any, out_dir: Path, ir_name: str) -> Path:
    """Generate TypeScript for `s` with the runtime, beside its IR as `ir_name`."""
    scaffold.emit(s, out_dir, langs=["typescript"], services=[], runtime=True)
    ts_dir = out_dir / "typescript"
    export_to(s, ts_dir / ir_name)
    return ts_dir


def _emit_late(out_dir: Path) -> Path:
    """Generate TypeScript for `_late_schema` with the runtime, beside its IR."""
    return _emit_ts(_late_schema(), out_dir, "late.ir.json")


def _run_node_tests(node: str, ts_dir: Path, harness: Path) -> None:
    result = subprocess.run(
        [node, "--experimental-strip-types", "--test", harness.name],
        cwd=ts_dir,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# One helper for every harness below: the error must be a DecodeError, recognised
# by name and a string tag (TautCheckedDecode.md CD-E3), and is reported as its tag
# and payload fields, as strings, the way the parity gate compares them (CD-C4).
_TS_OUTCOME = """
const PAYLOAD = ["info", "major", "key", "expected", "enum", "value", "len", "limit"];

function hexToBytes(hex: string): Uint8Array {
  return Uint8Array.from(Buffer.from(hex, "hex"));
}

function bytesToHex(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString("hex");
}

function outcome(fn: () => unknown): Record<string, string> {
  try {
    fn();
  } catch (e: any) {
    assert.equal(e?.name, "DecodeError", String(e));
    assert.equal(typeof e.tag, "string", String(e));
    const seen: Record<string, string> = { tag: e.tag };
    for (const field of PAYLOAD) {
      if (e[field] !== undefined) {
        seen[field] = String(e[field]);
      }
    }
    return seen;
  }
  return { accept: "true" };
}
"""


def test_typescript_missing_ok_reads_absent_and_null_alike_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    ts_dir = _emit_late(tmp_path)
    api = (ts_dir / "api.ts").read_text()
    # A MISSING_OK field is typed like any optional one.
    assert "export interface Late {\n  note: string | null;\n}" in api
    assert "export interface Opt {\n  note: string | null;\n}" in api

    harness = ts_dir / "missing_ok.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { decode, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("late.ir.json", "utf8")));
""".lstrip()
        + _TS_OUTCOME
        + """
test("a MISSING_OK field reads an absent key and a present null alike as null", () => {
  assert.deepEqual(decode(schema, "Late", hexToBytes("a0")), { note: null });
  assert.deepEqual(decode(schema, "Late", hexToBytes("a101f6")), { note: null });
  assert.deepEqual(decode(schema, "Late", hexToBytes("a1016161")), { note: "a" });
});

test("a MISSING_OK field still refuses a wrong type and a message that is not a map", () => {
  assert.deepEqual(outcome(() => decode(schema, "Late", hexToBytes("a10101"))), { tag: "WrongType", expected: "text" });
  assert.deepEqual(outcome(() => decode(schema, "Late", hexToBytes("00"))), { tag: "WrongType", expected: "map" });
});

test("a MISSING_OK field is still written, as null when unset", () => {
  assert.equal(bytesToHex(encode(schema, "Late", {})), "a101f6");
  assert.equal(bytesToHex(encode(schema, "Late", { note: null })), "a101f6");
});

test("a plain optional field absent is MissingKey, and present as null is null", () => {
  assert.deepEqual(outcome(() => decode(schema, "Opt", hexToBytes("a0"))), { tag: "MissingKey", key: "1" });
  assert.deepEqual(decode(schema, "Opt", hexToBytes("a101f6")), { note: null });
});
"""
    )
    _run_node_tests(node, ts_dir, harness)


# Raw inputs where the order of checks decides (TautCheckedDecode.md CD-E5): lengths
# and counts beyond the input, map keys up to the i64 edge. TypeScript must report
# what Python, the reference, reports.
_RAW_EDGES = [
    "5b001fffffffffffff",  # a bytes length of 2^53 - 1, beyond the input
    "7b0020000000000000",  # a text length of 2^53, beyond the input
    "7bffffffffffffffff",  # a text length of 2^64 - 1
    "9b0020000000000000c0",  # an array count of 2^53: its first item decides
    "bb0020000000000000c0",  # a map count of 2^53: its first key decides
    "bbffffffffffffffff01",  # a map count of 2^64 - 1: a key, then no value
    "a11b001fffffffffffff00",  # a key of 2^53 - 1
    "a11b002000000000000000",  # a key of 2^53
    "a11b7fffffffffffffff00",  # a key of 2^63 - 1
    "a11b800000000000000000",  # a key of 2^63
    "a21b0020000000000000001b002000000000000001",  # a repeated key of 2^53
    "a21b001fffffffffffff001b002000000000000000",  # keys of 2^53 - 1 and 2^53
]


def _python_outcome(call: Callable[[], Any]) -> dict[str, str]:
    """`call()`'s outcome as `_TS_OUTCOME`'s `outcome` reports one: a DecodeError's tag and
    payload, as strings, or accept."""
    try:
        call()
    except cbor.DecodeError as exc:
        return {"tag": exc.tag, **{name: str(value) for name, value in exc.payload.items()}}
    return {"accept": "true"}


def _python_raw_outcome(hex_bytes: str, limits: dict[str, Any] | None = None) -> dict[str, str]:
    return _python_outcome(lambda: cbor.loads(bytes.fromhex(hex_bytes), **(limits or {})))


def test_typescript_checked_decode_matches_python_on_lengths_counts_and_keys_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    ts_dir = _emit_late(tmp_path)
    cases = [{"hex": h, "expect": _python_raw_outcome(h)} for h in _RAW_EDGES]
    assert {c["expect"].get("tag", "accept") for c in cases} == {
        "Truncated", "UnsupportedMajor", "IntOverflow", "DuplicateMapKey", "accept"}
    (ts_dir / "raw_edges.json").write_text(json.dumps(cases))

    harness = ts_dir / "checked_decode.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { decode as cborDecode, encode as cborEncode } from "./cbor.ts";
import { decode, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("late.ir.json", "utf8")));
const cases = JSON.parse(readFileSync("raw_edges.json", "utf8"));
""".lstrip()
        + _TS_OUTCOME
        + """
test("raw decode reports what Python reports", () => {
  for (const c of cases) {
    assert.deepEqual(outcome(() => cborDecode(hexToBytes(c.hex))), c.expect, c.hex);
  }
});

test("a map key is a number up to 2^53 - 1 and an exact bigint above, and re-encodes as read", () => {
  for (const c of cases.filter((c: any) => c.expect.accept)) {
    const value = cborDecode(hexToBytes(c.hex));
    assert.ok(value instanceof Map, c.hex);
    for (const key of value.keys()) {
      assert.equal(typeof key, BigInt(key) > BigInt(Number.MAX_SAFE_INTEGER) ? "bigint" : "number", c.hex);
    }
    assert.equal(bytesToHex(cborEncode(value)), c.hex);
  }
  const both = cborDecode(hexToBytes("a21b001fffffffffffff001b002000000000000000")) as Map<unknown, unknown>;
  assert.deepEqual([...both.keys()], [2 ** 53 - 1, 2n ** 53n]);
});

test("a message keeps an unknown tag above 2^53 and re-encodes it", () => {
  const wire = "a201f61b002000000000000000";
  const value = decode(schema, "Opt", hexToBytes(wire));
  assert.equal(value.note, null);
  assert.deepEqual([...value.__unknown__.keys()], [2n ** 53n]);
  assert.equal(bytesToHex(encode(schema, "Opt", value)), wire);
});

test("the encoder refuses a map key in any other form", () => {
  for (const key of [-1, 1.5, 2 ** 53, 5n, 2n ** 63n]) {
    assert.throws(() => cborEncode(new Map([[key, 0n]]) as never), /invalid CBOR map key/, String(key));
  }
});
"""
    )
    _run_node_tests(node, ts_dir, harness)


def _text_schema():
    """`Note` holds a str field, and `Keyed` a map of each key type D24 allows: str, int
    and bool."""
    return schema(
        Msg("Note", F("text", 1, STR), next_id=2),
        Msg("Keyed",
            F("by_name", 1, Map(STR, INT)),
            F("by_id", 2, Map(INT, INT)),
            F("by_flag", 3, Map(BOOL, INT)),
            next_id=4),
    )


# U+FEFF opening a text string is ordinary text (the parity row text-leading-bom): a
# UTF-8 decoder must not strip it as a byte-order mark. One after the start, or a
# second one, is the contrast: no decoder strips those.
_BOM_TEXTS = ["﻿a", "﻿", "﻿﻿a", "a﻿"]


def test_typescript_text_keeps_a_leading_bom_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    s = _text_schema()
    ts_dir = _emit_ts(s, tmp_path, "text.ir.json")
    cases = [{"text": t, "raw": cbor.dumps(t).hex(), "typed": codec.encode(s, "Note", {"text": t}).hex()}
             for t in _BOM_TEXTS]
    invalid = "64efbbbfff"  # a U+FEFF, then a byte that is never UTF-8
    assert _python_raw_outcome(invalid) == {"tag": "InvalidUtf8"}
    (ts_dir / "bom.json").write_text(json.dumps({"cases": cases, "invalid": invalid}))

    harness = ts_dir / "bom.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { decode as cborDecode, encode as cborEncode } from "./cbor.ts";
import { decode, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("text.ir.json", "utf8")));
const { cases, invalid } = JSON.parse(readFileSync("bom.json", "utf8"));
""".lstrip()
        + _TS_OUTCOME
        + """
test("a leading U+FEFF is ordinary text: decode keeps it and re-encoding writes it back", () => {
  for (const c of cases) {
    const raw = cborDecode(hexToBytes(c.raw));
    assert.equal(raw, c.text, c.raw);
    assert.equal(bytesToHex(cborEncode(raw)), c.raw, c.raw);
    const note = decode(schema, "Note", hexToBytes(c.typed));
    assert.deepEqual(note, { text: c.text }, c.typed);
    assert.equal(bytesToHex(encode(schema, "Note", note)), c.typed, c.typed);
  }
});

test("the decoder is still fatal: invalid UTF-8 after a U+FEFF is InvalidUtf8", () => {
  assert.deepEqual(outcome(() => cborDecode(hexToBytes(invalid))), { tag: "InvalidUtf8" });
});
"""
    )
    _run_node_tests(node, ts_dir, harness)


# A map<K,V> field's entries are sorted by key (D24), in the order Python's `sorted`
# gives. A str key sorts by code point, which is its UTF-8 byte order. UTF-16 code unit
# order differs only where U+E000..U+FFFF meets a character above U+FFFF, a surrogate
# pair (d800-dfff). `row` holds the parity row map-str-key-order's keys; `d7ff`,
# `same-lead` and `prefix` are orders both agree on; int and bool keys keep their order.
_KEY_SETS = {
    "row": ("by_name", ["￿", "\U00010000", "a"]),
    "e000": ("by_name", ["\U00010000", ""]),
    "top": ("by_name", ["\U0010ffff", "￿"]),
    "after-a-prefix": ("by_name", ["a\U00010000", "a￿"]),
    "d7ff": ("by_name", ["\U00010000", "퟿"]),
    "same-lead": ("by_name", ["\U00010001", "\U00010000"]),
    "prefix": ("by_name", ["ab", "a", ""]),
    "int": ("by_id", [10, 9, -1, 0, 2 ** 53, -(2 ** 63), 2 ** 63 - 1]),
    "bool": ("by_flag", [True, False]),
}


def _keyed_cases(s: Any) -> list[dict[str, Any]]:
    """Each key set inserted in every order (forwards and backwards, above three keys),
    each key valued by its place in the set, with the bytes Python encodes: the same
    for every order. An int key travels as a string, exact above 2^53."""
    cases = []
    for name, (field, keys) in _KEY_SETS.items():
        value = {k: i + 1 for i, k in enumerate(keys)}
        orders = list(itertools.permutations(keys)) if len(keys) <= 3 else [keys, keys[::-1]]
        wire = codec.encode(s, "Keyed", {"by_name": {}, "by_id": {}, "by_flag": {}, field: value}).hex()
        for n, order in enumerate(orders):
            entries = [[str(k) if field == "by_id" else k, value[k]] for k in order]
            cases.append({"name": f"{name}/{n}", "field": field, "entries": entries, "hex": wire})
    return cases


def test_typescript_map_keys_encode_in_code_point_order_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    assert sorted(_KEY_SETS["row"][1]) == ["a", "￿", "\U00010000"]  # the reference order
    s = _text_schema()
    ts_dir = _emit_ts(s, tmp_path, "text.ir.json")
    (ts_dir / "keyed.json").write_text(json.dumps(_keyed_cases(s)))

    harness = ts_dir / "keyed.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { decode, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("text.ir.json", "utf8")));
const cases = JSON.parse(readFileSync("keyed.json", "utf8"));
""".lstrip()
        + _TS_OUTCOME
        + """
function native(c: any): any {
  const value: any = { by_name: new Map(), by_id: new Map(), by_flag: new Map() };
  for (const [k, v] of c.entries) {
    value[c.field].set(c.field === "by_id" ? BigInt(k) : k, BigInt(v));
  }
  return value;
}

test("map keys encode in Python's order, str keys by code point, whatever the insertion order", () => {
  for (const c of cases) {
    assert.equal(bytesToHex(encode(schema, "Keyed", native(c))), c.hex, c.name);
  }
});

test("each case's bytes decode and re-encode to themselves (D2)", () => {
  for (const c of cases) {
    assert.equal(bytesToHex(encode(schema, "Keyed", decode(schema, "Keyed", hexToBytes(c.hex)))), c.hex, c.name);
  }
});
"""
    )
    _run_node_tests(node, ts_dir, harness)


# An int key is a number up to 2^53 - 1 or a bigint, the only form above that, and one
# map may hold both. Its keys still sort by value, where String() order puts 10 before 9,
# and 10^16 (above 2^53) before 9. Each set lists its keys with the form each is built in.
_MIXED_INT_KEY_SETS = {
    "9-number-10-bigint": [(9, "number"), (10, "bigint")],
    "9-bigint-10-number": [(9, "bigint"), (10, "number")],
    "above-2^53": [(9, "number"), (10, "bigint"), (10 ** 16, "bigint")],
}


def test_typescript_int_map_keys_sort_by_value_in_either_form_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    assert 10 ** 16 > 2 ** 53
    s = _text_schema()
    ts_dir = _emit_ts(s, tmp_path, "text.ir.json")
    cases = []
    for name, keys in _MIXED_INT_KEY_SETS.items():
        value = {k: i + 1 for i, (k, _) in enumerate(keys)}
        wire = codec.encode(s, "Keyed", {"by_name": {}, "by_id": value, "by_flag": {}}).hex()
        for n, order in enumerate(itertools.permutations(keys)):
            entries = [[str(k), form, value[k]] for k, form in order]
            cases.append({"name": f"{name}/{n}", "entries": entries, "hex": wire})
    (ts_dir / "mixed.json").write_text(json.dumps(cases))

    harness = ts_dir / "mixed.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("text.ir.json", "utf8")));
const cases = JSON.parse(readFileSync("mixed.json", "utf8"));
""".lstrip()
        + _TS_OUTCOME
        + """
function keyed(byId: Map<unknown, bigint>): any {
  return { by_name: new Map(), by_id: byId, by_flag: new Map() };
}

test("int map keys encode by value, as numbers, bigints or both", () => {
  for (const c of cases) {
    const byId = new Map<unknown, bigint>();
    for (const [k, form, v] of c.entries) {
      byId.set(form === "number" ? Number(k) : BigInt(k), BigInt(v));
    }
    assert.equal(bytesToHex(encode(schema, "Keyed", keyed(byId))), c.hex, c.name);
  }
});

test("a number key above 2^53 - 1 is refused: only a bigint holds it exactly", () => {
  const byId = new Map<unknown, bigint>([[9, 1n], [2 ** 53, 2n]]);
  assert.throws(() => encode(schema, "Keyed", keyed(byId)), { name: "EncodeError", tag: "IntOutOfSubset" });
});
"""
    )
    _run_node_tests(node, ts_dir, harness)


# IR version 2 (TautOptions.md OPT-I1, OPT-I2, OPT-F4): loadSchema reads versions 1 and 2, and
# exposes each root's effective values, the ones Python resolved, through SchemaIndex (OPT-L6).
def _bounds_schema():
    """File-level bounds; `Tree` declares its own depth, `Blob` its own length, and `Plain`
    inherits the file's (OPT-D3)."""
    return schema(
        option.max_depth(16), option.max_encoded_len(4096),
        Msg("Tree", option.max_depth(64), F("children", 1, List(Ref("Tree"))), next_id=2),
        Msg("Blob", option.max_encoded_len(2**20), F("data", 1, BYTES), next_id=2),
        Msg("Plain", F("x", 1, INT), next_id=2),
    )


def _as_version_1(ir: dict) -> dict:
    """`ir` as taut wrote it before version 2: version 1, no options, no effective values."""
    old = copy.deepcopy(ir)
    old["version"] = 1
    levels = [old, *old["enums"], *old["messages"], *old["services"]]
    levels += [f for m in old["messages"] for f in m["fields"]]
    levels += [mt for s in old["services"] for mt in s["methods"]]
    for level in levels:
        for key in ("options", "effective", "member_options"):
            level.pop(key, None)
    return old


def _refused_irs(v2: dict) -> list[dict[str, Any]]:
    """IR documents loadSchema refuses: `v2` with one edit each, and the error each names."""
    def file(ir: dict) -> dict:
        return ir["effective"]

    def tree(ir: dict) -> dict:
        return ir["messages"][0]["effective"]

    depth = "message Tree: effective max_depth must be an integer from 1 to 128"
    length = "the file: effective max_encoded_len must be null or an integer from 1 to 2147483647"
    edits = [
        ("version 3", lambda ir: ir.update(version=3),
         "unsupported IR version 3: this runtime reads versions 1 and 2"),
        ("version 0", lambda ir: ir.update(version=0), "unsupported IR version 0"),
        ("version 2.5", lambda ir: ir.update(version=2.5), "unsupported IR version 2.5"),
        ('version "2"', lambda ir: ir.update(version="2"), 'unsupported IR version "2"'),
        ("no version", lambda ir: ir.pop("version"), "unsupported IR version none"),
        ("no effective for the file", lambda ir: ir.pop("effective"),
         "the file: a version 2 IR carries effective values"),
        ("no effective for a message", lambda ir: ir["messages"][0].pop("effective"),
         "message Tree: a version 2 IR carries effective values"),
        ("an effective that is no object", lambda ir: ir.update(effective=[16]),
         "the file: effective must be an object"),
        ("an unknown option in the file's", lambda ir: file(ir).update(max_frames=8),
         "the file: effective names max_frames, an option this runtime does not know"),
        ("an unknown option in a message's", lambda ir: tree(ir).update(max_frames=8),
         "message Tree: effective names max_frames, an option this runtime does not know"),
        ("no max_depth", lambda ir: tree(ir).pop("max_depth"), "message Tree: effective lacks max_depth"),
        ("no max_encoded_len", lambda ir: file(ir).pop("max_encoded_len"),
         "the file: effective lacks max_encoded_len"),
        *[(f"max_depth {v!r}", lambda ir, v=v: tree(ir).update(max_depth=v), depth)
          for v in (0, 129, 1.5, "16", True, None)],
        *[(f"max_encoded_len {v!r}", lambda ir, v=v: file(ir).update(max_encoded_len=v), length)
          for v in (0, 2**31, 1.5, "1k", False)],
    ]
    cases = []
    for note, edit, error in edits:
        ir = copy.deepcopy(v2)
        edit(ir)
        cases.append({"note": note, "ir": ir, "error": error})
    for note, where, error in [
        ("a version 1 IR with the file's effective values", None, "the file"),
        ("a version 1 IR with a message's effective values", 0, "message Tree"),
    ]:
        v1 = _as_version_1(v2)
        level = v1 if where is None else v1["messages"][where]
        level["effective"] = {"max_depth": 32, "max_encoded_len": None}
        cases.append({"note": note, "ir": v1,
                      "error": f"{error}: a version 1 IR carries no effective values"})
    return cases


def test_typescript_load_schema_reads_version_2_and_refuses_what_it_cannot_honour_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    s = _bounds_schema()
    ts_dir = _emit_ts(s, tmp_path, "bounds.ir.json")
    v2 = json.loads((ts_dir / "bounds.ir.json").read_text())
    assert v2["version"] == 2
    (ts_dir / "cases.json").write_text(json.dumps({
        "v1": _as_version_1(v2),
        "file": effective_map(s),
        "messages": {name: effective_map(s, message=name) for name in s.messages},
        "refused": _refused_irs(v2),
    }))

    harness = ts_dir / "ir_version.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { decode, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const v2 = JSON.parse(readFileSync("bounds.ir.json", "utf8"));
const cases = JSON.parse(readFileSync("cases.json", "utf8"));
const DEFAULTS = { max_depth: 32, max_encoded_len: null };

test("version 2: each message's effective values are the ones Python resolved", () => {
  const schema = loadSchema(v2);
  assert.deepEqual(schema.effective(), { max_depth: 16, max_encoded_len: 4096 });
  assert.deepEqual(schema.effective(), cases.file);
  assert.deepEqual(schema.effective("Tree"), { max_depth: 64, max_encoded_len: 4096 });
  assert.deepEqual(schema.effective("Blob"), { max_depth: 16, max_encoded_len: 1048576 });
  for (const [name, values] of Object.entries(cases.messages)) {
    assert.deepEqual(schema.effective(name), values, name);
    assert.deepEqual(schema.rootEffective({ k: "msg", name }), values, name);
  }
  assert.throws(() => schema.effective("Nope"), /unknown message Nope/);
});

test("a call rooted at a type other than a message takes the file's values", () => {
  const schema = loadSchema(v2);
  const tree = { k: "msg", name: "Tree" } as const;
  assert.deepEqual(schema.rootEffective({ k: "list", elem: tree }), cases.file);
  assert.deepEqual(schema.rootEffective({ k: "scalar", scalar: "int" }), cases.file);
});

test("the effective values are read-only", () => {
  const schema = loadSchema(v2);
  assert.throws(() => {
    (schema.effective("Tree") as any).max_depth = 128;
  }, TypeError);
  assert.equal(schema.effective("Tree").max_depth, 64);
});

test("version 2 still drives the codec", () => {
  const schema = loadSchema(v2);
  const wire = encode(schema, "Plain", { x: 5n });
  assert.equal(Buffer.from(wire).toString("hex"), "a10105");
  assert.deepEqual(decode(schema, "Plain", wire), { x: 5n });
});

test("version 1 declares nothing, so every root has the defaults", () => {
  const schema = loadSchema(cases.v1);
  assert.deepEqual(schema.effective(), DEFAULTS);
  for (const name of Object.keys(cases.messages)) {
    assert.deepEqual(schema.effective(name), DEFAULTS, name);
  }
});

test("loadSchema refuses a version, or an effective value, that it cannot honour", () => {
  assert.ok(cases.refused.length >= 20);
  for (const c of cases.refused) {
    assert.throws(() => loadSchema(c.ir), new RegExp(c.error), c.note);
  }
  assert.throws(() => loadSchema(null), /a taut IR is a JSON object/);
  assert.throws(() => loadSchema([]), /a taut IR is a JSON object/);
});
""".lstrip()
    )
    _run_node_tests(node, ts_dir, harness)


# Decode bounds (TautCheckedDecode.md §3; TautV010Plan.md D1). Raw decode's (CD-B1-B5, question
# 1): the default depth where a call passes none, the caller's depth capped at the ceiling, and
# the caller's length, each at its bound and one beyond it, with the order of checks around them
# (CD-E5). TypeScript must report what Python, the reference, reports.
_RAW_BOUNDS: list[tuple[str, str, dict[str, Any]]] = [
    ("32 arrays, the default bound", "81" * 31 + "80", {}),
    ("33 arrays", "81" * 32 + "80", {}),
    ("32 maps", "a100" * 31 + "a0", {}),
    ("33 maps", "a100" * 32 + "a0", {}),
    ("an int inside the 32nd array adds no depth", "81" * 32 + "00", {}),
    ("the 33rd head complete and its item missing", "81" * 33, {}),
    ("the 33rd head torn", "81" * 32 + "9b00", {}),
    ("100,000 arrays", "81" * 99_999 + "80", {}),
    ("100,000 maps", "a100" * 99_999 + "a0", {}),
    ("an array as a map key, at the default", "a18000", {}),
    ("depth 1: an empty array", "80", {"max_depth": 1}),
    ("depth 1: a map of ints", "a10100", {"max_depth": 1}),
    ("depth 1: an array in an array", "8180", {"max_depth": 1}),
    ("depth 1: an array as a map value", "a10180", {"max_depth": 1}),
    ("depth 1: an array as a map key, depth before the key's type", "a18000", {"max_depth": 1}),
    ("depth 64", "81" * 63 + "80", {"max_depth": 64}),
    ("depth 64, one beyond", "81" * 64 + "80", {"max_depth": 64}),
    ("the ceiling", "81" * 127 + "80", {"max_depth": 128}),
    ("the ceiling, one beyond", "81" * 128 + "80", {"max_depth": 128}),
    ("above the ceiling applies the ceiling", "81" * 128 + "80", {"max_depth": 129}),
    ("far above the ceiling applies the ceiling", "81" * 128 + "80", {"max_depth": 2**53 - 1}),
    ("100,000 arrays at the ceiling", "81" * 99_999 + "80", {"max_depth": 1000}),
    ("a length at its bound", "83010203", {"max_encoded_len": 4}),
    ("a length one beyond", "83010203", {"max_encoded_len": 3}),
    ("a length beyond, before any byte is read", "c0c0c0c0", {"max_encoded_len": 3}),
    ("empty at length 0", "", {"max_encoded_len": 0}),
    ("one byte at length 0", "00", {"max_encoded_len": 0}),
    ("length before depth", "8180", {"max_depth": 1, "max_encoded_len": 1}),
    ("depth once the length passes", "8180", {"max_depth": 1, "max_encoded_len": 2}),
    ("null is no length bound", "8180", {"max_encoded_len": None}),
]


def test_typescript_raw_decode_bounds_depth_and_length_as_python_does_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    ts_dir = _emit_late(tmp_path)
    cases = [{"note": note, "hex": h, "limits": limits, "expect": _python_raw_outcome(h, limits)}
             for note, h, limits in _RAW_BOUNDS]
    assert {c["expect"].get("tag", "accept") for c in cases} == {
        "accept", "TooDeep", "TooLarge", "Truncated", "NonIntegerMapKey"}
    (ts_dir / "raw_bounds.json").write_text(json.dumps({
        "cases": cases,
        "numbers": {"default_max_depth": DEFAULT_MAX_DEPTH, "max_depth_ceiling": MAX_DEPTH_CEILING},
    }))

    harness = ts_dir / "raw_bounds.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DEFAULT_MAX_DEPTH, MAX_DEPTH_CEILING, decode as cborDecode, encode as cborEncode } from "./cbor.ts";

const { cases, numbers } = JSON.parse(readFileSync("raw_bounds.json", "utf8"));
""".lstrip()
        + _TS_OUTCOME
        + """
// A case's limits as its call passes them; a limit the case leaves out is not passed.
function limitsOf(c: any): { maxDepth?: number; maxEncodedLen?: number | null } {
  const limits: { maxDepth?: number; maxEncodedLen?: number | null } = {};
  if ("max_depth" in c.limits) {
    limits.maxDepth = c.limits.max_depth;
  }
  if ("max_encoded_len" in c.limits) {
    limits.maxEncodedLen = c.limits.max_encoded_len;
  }
  return limits;
}

function thrown(fn: () => unknown): any {
  try {
    fn();
  } catch (e) {
    return e;
  }
  assert.fail("expected an error");
}

test("the runtime exports taut's depth numbers: the default bound and the ceiling", () => {
  assert.equal(DEFAULT_MAX_DEPTH, numbers.default_max_depth);
  assert.equal(MAX_DEPTH_CEILING, numbers.max_depth_ceiling);
});

test("raw decode bounds depth and length as Python does", () => {
  for (const c of cases) {
    assert.deepEqual(outcome(() => cborDecode(hexToBytes(c.hex), limitsOf(c))), c.expect, c.note);
  }
});

test("a value decoded at its bound re-encodes to its bytes", () => {
  for (const c of cases.filter((c: any) => c.expect.accept)) {
    assert.equal(bytesToHex(cborEncode(cborDecode(hexToBytes(c.hex), limitsOf(c)))), c.hex, c.note);
  }
});

test("TooDeep carries the bound applied, and TooLarge the input's length and the bound, as numbers", () => {
  const deep = thrown(() => cborDecode(hexToBytes("81".repeat(200) + "80"), { maxDepth: 500 }));
  assert.equal(deep.name, "DecodeError");
  assert.equal(deep.tag, "TooDeep");
  assert.equal(deep.limit, 128);
  assert.equal(deep.len, undefined);
  const large = thrown(() => cborDecode(hexToBytes("c0c0"), { maxEncodedLen: 1 }));
  assert.equal(large.name, "DecodeError");
  assert.equal(large.tag, "TooLarge");
  assert.equal(large.len, 2);
  assert.equal(large.limit, 1);
});

test("a bound out of range is the caller's error, thrown before a byte is read", () => {
  const data = hexToBytes("c0"); // never decodes: the caller's error comes first
  for (const maxDepth of [0, -1, 1.5, NaN, Infinity, -Infinity]) {
    assert.throws(() => cborDecode(data, { maxDepth }), RangeError, String(maxDepth));
  }
  for (const maxEncodedLen of [-1, 0.5, NaN, Infinity, -Infinity]) {
    assert.throws(() => cborDecode(data, { maxEncodedLen }), RangeError, String(maxEncodedLen));
  }
  for (const maxDepth of ["16", 16n, null, true]) {
    assert.throws(() => cborDecode(data, { maxDepth } as never), TypeError, String(maxDepth));
  }
  for (const maxEncodedLen of ["16", 16n, true]) {
    assert.throws(() => cborDecode(data, { maxEncodedLen } as never), TypeError, String(maxEncodedLen));
  }
});
"""
    )
    _run_node_tests(node, ts_dir, harness)


# Typed decode's bounds (TautOptions.md OPT-D4, OPT-L6): a call applies its root's effective
# values, a message's own or, for any other root, the file's. `_bounds_schema`'s file declares
# depth 16 and length 4096, `Tree` depth 64, `Blob` length 2^20, and `Plain` nothing.
_TYPED_ROOTS: dict[str, tuple[TypeRef, dict[str, Any]]] = {
    "Tree": (MsgRef("Tree"), {"k": "msg", "name": "Tree"}),
    "Blob": (MsgRef("Blob"), {"k": "msg", "name": "Blob"}),
    "Plain": (MsgRef("Plain"), {"k": "msg", "name": "Plain"}),
    "list<Tree>": (ListOf(MsgRef("Tree")), {"k": "list", "elem": {"k": "msg", "name": "Tree"}}),
    "int": (Scalar("int"), {"k": "scalar", "scalar": "int"}),
}
_TYPED_BOUNDS: list[tuple[str, str, str]] = [
    ("Tree at its own depth, 64", "Tree", "a10181" * 31 + "a10180"),
    ("Tree one beyond", "Tree", "a10181" * 32 + "a10180"),
    ("list<Tree> at the file's depth, 16: the schema stage decides", "list<Tree>", "81" + "a10181" * 7 + "a0"),
    ("list<Tree> one beyond: the file's bound, not Tree's", "list<Tree>", "81" + "a10181" * 7 + "a10180"),
    ("list<Tree> within the file's depth", "list<Tree>", "81" + "a10181" * 6 + "a10180"),
    ("Plain at the file's depth, in an unknown field", "Plain", "a2010002" + "81" * 14 + "80"),
    ("Plain one beyond", "Plain", "a2010002" + "81" * 15 + "80"),
    ("Plain at the file's length", "Plain", "a201000259" + f"{4089:04x}" + "00" * 4089),
    ("Plain one byte beyond", "Plain", "a201000259" + f"{4090:04x}" + "00" * 4090),
    ("Plain beyond, before any byte is read", "Plain", "c0" * 4097),
    ("Tree takes the file's length", "Tree", "c0" * 4097),
    ("Blob beyond the file's length, within its own", "Blob", "a10159" + f"{4096:04x}" + "00" * 4096),
    ("an int root takes the file's length", "int", "c0" * 4097),
    ("an int root", "int", "00"),
]


def test_typescript_typed_decode_applies_its_roots_effective_bounds_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    s = _bounds_schema()
    ts_dir = _emit_ts(s, tmp_path, "bounds.ir.json")
    v2 = json.loads((ts_dir / "bounds.ir.json").read_text())
    cases = [{"note": note, "root": root, "hex": h,
              "expect": _python_outcome(lambda root=root, h=h: codec.decode_ref(
                  s, _TYPED_ROOTS[root][0], bytes.fromhex(h)))}
             for note, root, h in _TYPED_BOUNDS]
    assert {c["expect"].get("tag", "accept") for c in cases} == {"accept", "TooDeep", "TooLarge", "MissingKey"}
    assert {c["expect"].get("limit") for c in cases} == {None, "64", "16", "4096"}
    (ts_dir / "typed_bounds.json").write_text(json.dumps({
        "cases": cases,
        "roots": {name: ref for name, (_, ref) in _TYPED_ROOTS.items()},
        "v1": _as_version_1(v2),
    }))

    harness = ts_dir / "typed_bounds.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { decode, decodeRef, encodeRef } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("bounds.ir.json", "utf8")));
const { cases, roots, v1 } = JSON.parse(readFileSync("typed_bounds.json", "utf8"));
""".lstrip()
        + _TS_OUTCOME
        + """
test("typed decode applies its root's effective bounds, as Python does", () => {
  for (const c of cases) {
    const ref = roots[c.root];
    const data = hexToBytes(c.hex);
    assert.deepEqual(outcome(() => decodeRef(schema, ref, data)), c.expect, c.note);
    if (ref.k === "msg") {
      assert.deepEqual(outcome(() => decode(schema, ref.name, data)), c.expect, c.note);
    }
  }
});

test("a value decoded at its root's bounds re-encodes to its bytes", () => {
  for (const c of cases.filter((c: any) => c.expect.accept)) {
    const ref = roots[c.root];
    assert.equal(bytesToHex(encodeRef(schema, ref, decodeRef(schema, ref, hexToBytes(c.hex)))), c.hex, c.note);
  }
});

test("a version 1 IR declares nothing: every root decodes at depth 32 with no length bound", () => {
  const old = loadSchema(v1);
  const nested = (arrays: number) => hexToBytes("a2010002" + "81".repeat(arrays - 1) + "80");
  assert.deepEqual(outcome(() => decode(old, "Plain", nested(31))), { accept: "true" });
  assert.deepEqual(outcome(() => decode(old, "Plain", nested(32))), { tag: "TooDeep", limit: "32" });
  const list = { k: "list", elem: { k: "msg", name: "Tree" } } as const;
  const arrays = hexToBytes("81".repeat(32) + "80");
  assert.deepEqual(outcome(() => decodeRef(old, list, arrays)), { tag: "TooDeep", limit: "32" });
  const long = hexToBytes("c0".repeat(5000));
  assert.deepEqual(outcome(() => decode(old, "Plain", long)), { tag: "UnsupportedMajor", major: "6" });
});
"""
    )
    _run_node_tests(node, ts_dir, harness)


def test_typescript_extension_helpers_read_a_host_at_the_depth_ceiling_if_node(tmp_path):
    """TautOptions.md G3, TautCheckedDecode.md CD-E4: not knowing the host's root, the three
    helpers read it at the depth ceiling, 128, with no length bound, as Python's do."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    s = _late_schema()
    ts_dir = _emit_late(tmp_path)
    tag = BAND_START + 1
    cases = []
    for note, h in [
        ("a host nested to the ceiling", "a101" + "81" * 126 + "80"),
        ("a host one beyond", "a101" + "81" * 127 + "80"),
        ("a host 100,000 deep", "a101" + "81" * 99_999 + "80"),
        ("a host nested to the ceiling that is not a map", "81" * 127 + "80"),
        ("a host one beyond that is not a map", "81" * 128 + "80"),
    ]:
        host = bytes.fromhex(h)
        case = {"note": note, "hex": h, "expect": _python_outcome(lambda host=host: ext.ext_clear(host, tag))}
        if "accept" in case["expect"]:
            case["set"] = ext.ext_set(s, host, "Late", tag, {"note": None}).hex()
            case["clear"] = ext.ext_clear(host, tag).hex()
        cases.append(case)
    assert [c["expect"] for c in cases] == [
        {"accept": "true"}, {"tag": "TooDeep", "limit": "128"}, {"tag": "TooDeep", "limit": "128"},
        {"tag": "WrongType", "expected": "map"}, {"tag": "TooDeep", "limit": "128"}]
    (ts_dir / "ext_depth.json").write_text(json.dumps({"cases": cases, "tag": tag}))

    harness = ts_dir / "ext_depth.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { extClear, extGet, extSet } from "./ext.ts";

const { cases, tag } = JSON.parse(readFileSync("ext_depth.json", "utf8"));
const lateNull = new Map([[1, null]]); // a Late whose note is null
""".lstrip()
        + _TS_OUTCOME
        + """
test("each helper reads a host at the depth ceiling, as Python does", () => {
  for (const c of cases) {
    const host = hexToBytes(c.hex);
    for (const call of [() => extGet(host, tag), () => extSet(host, tag, lateNull), () => extClear(host, tag)]) {
      assert.deepEqual(outcome(call), c.expect, c.note);
    }
    if (c.expect.accept) {
      assert.equal(extGet(host, tag), null, c.note);
      assert.equal(bytesToHex(extSet(host, tag, lateNull)), c.set, c.note);
      assert.equal(bytesToHex(extClear(host, tag)), c.clear, c.note);
    }
  }
});
"""
    )
    _run_node_tests(node, ts_dir, harness)


# The gate's TypeScript runner (parity.py's bounds protocol, TautCheckedDecode.md CD-C4).
def _needs_node_for_typescript() -> None:
    if toolchains.find_node_for_typescript() is None:
        pytest.skip("node with --experimental-strip-types (node >= 22.6) not available")


def test_typescript_parity_runner_speaks_the_bounds_protocol_and_every_row_passes():
    """`tautc parity -t typescript`: the runner prints its runtime's constants once, passes a raw
    row's limits, decodes each from_cbor row through the typed entry point and reports the bounds
    it resolved, and expands segmented bytes itself. Every int, malformed and bounds row passes."""
    _needs_node_for_typescript()
    report = parity_typescript.run()
    assert report.green, "\n".join([report.fault, *(f"{r.name}: {r.detail}" for r in report.failures)])
    kinds = [r.kind for r in report.results]
    assert kinds.count("bounds") == len(parity.bounds_rows())
    assert kinds.count("malformed") == len(parity.malformed_rows())


def test_typescript_parity_runner_reports_an_expansion_that_is_not_len_as_untyped(tmp_path, monkeypatch):
    """The bounds protocol, item 5: a row whose bytes, segments or a hex string, expand to other
    than its `len` is reported `untyped`, not decoded."""
    _needs_node_for_typescript()
    doc = json.loads(parity.BOUNDS_VECTORS.read_text())
    for row in doc["vectors"]:
        if row["name"] in ("depth-100000-arrays", "size-at-limit"):
            row["len"] += 1
    doctored = tmp_path / parity.BOUNDS_VECTORS.name
    doctored.write_text(json.dumps(doc))
    monkeypatch.setattr(parity, "BOUNDS_VECTORS", doctored)
    report = parity_typescript.run()
    failed = {r.name: r.detail for r in report.failures}
    assert set(failed) == {"depth-100000-arrays", "size-at-limit"}, failed
    assert all(detail.startswith("untyped") for detail in failed.values()), failed
    assert report.fault == ""


# taut_client.ts (TautCheckedDecode.md CD-E3): a response that does not decode fails its call,
# and an event that does not decode fails its stream. The DecodeError reaches the caller
# itself, never escapes the socket's message handler, and is never made a plain Error.
def _service_schema():
    """`Item` behind a unary `get`, and a `watch` that streams it as a log's `append` events."""
    return schema(
        Msg("Item", F("n", 1, INT), next_id=2),
        service("Svc",
                method("get", role="out", params=Params(id=INT), out=Ref("Item")),
                method("watch", role="out", shape="log", params=Params(id=INT), out=Ref("Item"))),
    )


def test_typescript_client_fails_a_call_or_stream_whose_payload_does_not_decode_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    s = _service_schema()
    ts_dir = _emit_ts(s, tmp_path, "svc.ir.json")
    assert codec.encode(s, "Item", {"n": 5}).hex() == "a10105"
    with pytest.raises(codec.DecodeError) as err:
        codec.decode(s, "Item", bytes.fromhex("a1016178"))  # n is text: the payload used below
    assert (err.value.tag, err.value.payload) == ("WrongType", {"expected": "int"})

    harness = ts_dir / "client.test.ts"
    harness.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { loadSchema } from "./schema.ts";
import { tautClient } from "./taut_client.ts";

const schema = loadSchema(JSON.parse(readFileSync("svc.ir.json", "utf8")));
const GOOD = Buffer.from("a10105", "hex").toString("base64"); // { n: 5 }
const BAD = Buffer.from("a1016178", "hex").toString("base64"); // n is text: WrongType{int}

// A WebSocket stand-in: it opens at once, keeps what the client sends, and delivers a frame
// through the client's onmessage, which must return whatever the frame holds.
class FakeSocket {
  static last: FakeSocket;
  sent: any[] = [];
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;

  constructor(_url: string) {
    FakeSocket.last = this;
    queueMicrotask(() => this.onopen?.());
  }

  send(data: string): void {
    this.sent.push(JSON.parse(data));
  }

  close(): void {}

  deliver(env: Record<string, unknown>): void {
    assert.doesNotThrow(() => this.onmessage!({ data: JSON.stringify(env) }), JSON.stringify(env));
  }
}
(globalThis as any).WebSocket = FakeSocket;

async function connect() {
  const client = await tautClient.connect("ws://test", schema);
  return { client, ws: FakeSocket.last };
}

// How `p` stands once pending work has run: resolved, rejected or still pending.
function settled(p: Promise<unknown>): Promise<any> {
  return Promise.race([
    p.then((value) => ({ state: "resolved", value }), (error) => ({ state: "rejected", error })),
    new Promise((resolve) => setTimeout(() => resolve({ state: "pending" }), 20)),
  ]);
}

test("a response that does not decode rejects its call with the DecodeError itself", async () => {
  const { client, ws } = await connect();
  const call = client.call("get", { id: 1n });
  ws.deliver({ messageId: ws.sent[0].messageId, kind: "response", payload: { value: BAD } });
  const out = await settled(call);
  assert.equal(out.state, "rejected");
  assert.equal(out.error.name, "DecodeError");
  assert.equal(out.error.tag, "WrongType");
  assert.equal(out.error.expected, "int");
});

test("a response that decodes still resolves its call, and a server error still rejects it", async () => {
  const { client, ws } = await connect();
  const ok = client.call("get", { id: 1n });
  const failed = client.call("get", { id: 2n });
  ws.deliver({ messageId: ws.sent[0].messageId, kind: "response", payload: { value: GOOD } });
  ws.deliver({ messageId: ws.sent[1].messageId, kind: "error", error: { code: "gone", message: "no such item" } });
  assert.deepEqual(await ok, { n: 5n });
  await assert.rejects(failed, { name: "Error", message: "no such item" });
});

test("an event that does not decode ends its stream, as unsubscribing does, and goes to onError", async () => {
  const { client, ws } = await connect();
  const events: unknown[] = [];
  const errors: any[] = [];
  const stop = client.subscribe("watch", { id: 1n }, (event, value) => events.push([event, value]),
    (error) => errors.push(error));
  const { streamId } = ws.sent[0];
  const event = (value: string) => ({ messageId: "e", kind: "stream-event", streamId, event: "append", payload: { value } });
  ws.deliver(event(GOOD));
  ws.deliver(event(BAD));
  ws.deliver(event(GOOD)); // after the end: not delivered
  stop(); // already ended: the server is not told twice
  assert.deepEqual(events, [["append", { n: 5n }]]);
  assert.equal(errors.length, 1);
  assert.equal(errors[0].name, "DecodeError");
  assert.equal(errors[0].tag, "WrongType");
  assert.deepEqual(ws.sent.slice(1).map((m: any) => [m.method, m.streamId]), [["$unsubscribe", streamId]]);
});

test("without onError, an event that does not decode still ends its stream and escapes nowhere", async () => {
  const { client, ws } = await connect();
  const events: unknown[] = [];
  client.subscribe("watch", { id: 1n }, (event, value) => events.push([event, value]));
  const { streamId } = ws.sent[0];
  ws.deliver({ messageId: "e", kind: "stream-event", streamId, event: "append", payload: { value: BAD } });
  ws.deliver({ messageId: "e", kind: "stream-event", streamId, event: "append", payload: { value: GOOD } });
  assert.deepEqual(events, []);
  assert.deepEqual(ws.sent.slice(1).map((m: any) => m.method), ["$unsubscribe"]);
});
""".lstrip()
    )
    _run_node_tests(node, ts_dir, harness)
