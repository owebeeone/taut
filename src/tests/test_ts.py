"""TypeScript runtime-resource ResExt tests."""

from __future__ import annotations

import json
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from taut import cli, ext
from taut.corpus import resext_build as rb
from taut.ir.export import export_to
from taut.ir.load import load_schema
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

test("extension accessors reject below-band tags before host decode", () => {
  const invalidHost = hexToBytes("ff");
  const nested = new Map();
  assert.throws(() => extSet(invalidHost, BAND_START - 1, nested), /below the band/);
  assert.throws(() => extGet(invalidHost, BAND_START - 1), /below the band/);
  assert.throws(() => extClear(invalidHost, BAND_START - 1), /below the band/);
});

test("extension accessors reject non-map hosts", () => {
  const scalarHost = hexToBytes("01");
  const nested = new Map();
  assert.throws(() => extSet(scalarHost, BAND_START + 1, nested), /top-level CBOR map/);
  assert.throws(() => extGet(scalarHost, BAND_START + 1), /top-level CBOR map/);
  assert.throws(() => extClear(scalarHost, BAND_START + 1), /top-level CBOR map/);
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
