"""JS generator: ES classes + frozen enum objects + CBOR codec (CommonJS),
forward-compat residual."""

import json
from pathlib import Path
import random
import shutil
import subprocess
import textwrap

import pytest
from taut import cli, ext
from taut.corpus.build import IR_PATH
from taut.corpus import resext_build as rb
from taut.gen import js
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec

ROOT = IR_PATH.parent.parent
RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
RESEXT = load_schema(rb.IR_PATH)
FLOATY = mk(Msg("Floaty",
                F("x", 1, FLOAT),
                F("xs", 2, List(FLOAT)),
                F("by_id", 3, Map(INT, FLOAT))))
PARITY_IR = ROOT / "ir" / "parity_int.taut.py"
PARITY_INT_VECTORS = ROOT / "corpus" / "parity" / "int.vectors.json"
PARITY_MALFORMED_VECTORS = ROOT / "corpus" / "parity" / "malformed.vectors.json"
RESEXT_FUZZ_SEED = 0x55_0004


def test_emits_classes_enums_and_codec():
    s = js.emit_types(RAZEL)
    assert 'require("./cbor.js")' in s
    assert "class BuildResult {" in s
    assert "const BuildStatus = Object.freeze({" in s
    assert "toCbor() {" in s
    assert "static fromCbor(c) {" in s
    assert "module.exports = {" in s


def test_optional_is_nullable():
    assert "this.message != null ?" in js.emit_types(RAZEL)


def test_forward_compat_residual():
    s = js.emit_types(RAZEL, forward_compat=True)
    assert "this.wireResidual" in s
    assert "wireResidual" not in js.emit_types(RAZEL)  # off by default


def test_float_scalar_shape():
    s = js.emit_types(FLOATY)
    assert "CFloat" in s
    assert "[1, CFloat(this.x)]" in s
    assert "CArr(this.xs.map((e) => CFloat(e)))" in s
    assert "CMap([[1, CInt(k)], [2, CFloat(v)]])" in s
    assert "v.x = expectFloat(cget(c, 1));" in s
    assert "v.xs = expectArray(cget(c, 2)).map((e) => expectFloat(e));" in s


def test_js_i64_bigint_and_fail_closed_parity(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    cli.main([
        "gen", str(PARITY_IR), "-o", str(tmp_path), "--lang", "js",
        "--api-only", "--with-runtime",
    ])
    js_dir = tmp_path / "js"
    assert (js_dir / "api.js").exists()
    assert (js_dir / "cbor.js").exists()

    int_vectors = json.loads(PARITY_INT_VECTORS.read_text())
    malformed_vectors = json.loads(PARITY_MALFORMED_VECTORS.read_text())
    harness = js_dir / "parity_i64.test.js"
    harness.write_text(textwrap.dedent(f"""
        "use strict";

        const test = require("node:test");
        const assert = require("node:assert/strict");
        const {{ IntBox, ModeFromCbor }} = require("./api.js");
        const {{ DecodeError, EncodeError, decode, encode }} = require("./cbor.js");

        const intVectors = {json.dumps(int_vectors)};
        const malformedVectors = {json.dumps(malformed_vectors)};

        function bytesFromHex(hex) {{
          const out = new Uint8Array(hex.length / 2);
          for (let i = 0; i < out.length; i++) {{
            out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
          }}
          return out;
        }}

        function hexFromBytes(bytes) {{
          return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
        }}

        function intBoxFromVector(row) {{
          return new IntBox({{
            n: BigInt(row.value.n),
            by_id: new Map(row.value.by_id.map(([k, v]) => [BigInt(k), BigInt(v)])),
          }});
        }}

        function vectorEntries(box) {{
          return Array.from(box.by_id.entries(), ([k, v]) => [k.toString(), v.toString()]);
        }}

        function checkError(err, row) {{
          assert.ok(err instanceof DecodeError || err instanceof EncodeError, `${{row.name}}: typed error`);
          assert.equal(err.tag, row.expect.tag, `${{row.name}}: tag`);
          for (const [key, value] of Object.entries(row.expect)) {{
            if (key === "tag") continue;
            assert.equal(String(err[key]), String(value), `${{row.name}}: payload ${{key}}`);
          }}
          return true;
        }}

        test("round-trip i64 vectors use bigint and match canonical CBOR", () => {{
          for (const row of intVectors.vectors.filter((r) => r.kind === "round_trip")) {{
            const box = intBoxFromVector(row);
            const encoded = hexFromBytes(encode(box.toCbor()));
            assert.equal(encoded, row.cbor, `${{row.name}}: encode`);

            const decoded = IntBox.fromCbor(decode(bytesFromHex(row.cbor)));
            assert.equal(typeof decoded.n, "bigint", `${{row.name}}: n carrier`);
            assert.equal(decoded.n, BigInt(row.value.n), `${{row.name}}: n`);
            assert.deepEqual(vectorEntries(decoded), row.value.by_id, `${{row.name}}: by_id`);
            assert.equal(hexFromBytes(encode(decoded.toCbor())), row.cbor, `${{row.name}}: re-encode`);
          }}
        }});

        test("out-of-subset encode vectors are typed errors", () => {{
          for (const row of intVectors.vectors.filter((r) => r.kind === "encode_fail")) {{
            assert.throws(() => encode(intBoxFromVector(row).toCbor()), (err) => checkError(err, row), row.name);
          }}
        }});

        test("malformed decode vectors are typed fail-closed errors", () => {{
          for (const row of malformedVectors.vectors) {{
            const bytes = bytesFromHex(row.bytes);
            let fn;
            if (row.stage === "raw_decode") {{
              fn = () => decode(bytes);
            }} else if (row.stage === "from_cbor") {{
              fn = () => IntBox.fromCbor(decode(bytes));
            }} else if (row.stage === "from_wire") {{
              fn = () => ModeFromCbor(decode(bytes));
            }} else {{
              throw new Error(`unknown stage ${{row.stage}}`);
            }}
            assert.throws(fn, (err) => checkError(err, row), row.name);
          }}
        }});
    """))

    subprocess.run([node, "--test", str(harness)], check=True)


def test_js_float_runtime_parity():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    script = Path(__file__).with_name("js_float_parity.js")
    subprocess.run([node, str(script)], check=True)


def _random_cbor_value(rng: random.Random):
    kind = rng.choice(["int", "text", "bytes", "array"])
    if kind == "int":
        return rng.randint(-10000, 10000)
    if kind == "text":
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 10)))
    if kind == "bytes":
        return bytes(rng.randrange(256) for _ in range(rng.randint(0, 8)))
    return [rng.choice([rng.randint(-50, 50), "".join(rng.choice("abcxyz") for _ in range(3))])
            for _ in range(rng.randint(0, 4))]


def _resext_fuzz_rows(count: int = 1000) -> list[dict[str, str | int]]:
    rng = random.Random(RESEXT_FUZZ_SEED)
    rows = []
    tag = BAND_START + 1
    for i in range(count):
        host_map = {
            1: rng.randint(0, 100000),
            2: f"n{rng.randint(0, 9999)}",
            5: rng.randint(-1000, 1000),
            3: _random_cbor_value(rng),                    # interleaved unknown
            BAND_START + 2 + rng.randrange(1000): _random_cbor_value(rng),  # band unknown
        }
        for _ in range(rng.randrange(4)):
            unknown = rng.randrange(0, 2 ** 21)
            if unknown not in {1, 2, 3, 5, tag}:
                host_map[unknown] = _random_cbor_value(rng)
        if i % 3 == 0:
            host_map[tag] = codec.encode_struct(
                RESEXT, "Decision", {"backend": f"old{i % 17}", "hops": i % 11}
            )

        value = {"backend": f"b{rng.randrange(10000)}", "hops": rng.randrange(256)}
        host = cbor.dumps(host_map)
        value_wire = codec.encode(RESEXT, "Decision", value)
        set_wire = ext.ext_set(RESEXT, host, "Decision", tag, value)
        rows.append({
            "note": f"seed={RESEXT_FUZZ_SEED} i={i}",
            "host": host.hex(),
            "tag": tag,
            "value": value_wire.hex(),
            "expect_set": set_wire.hex(),
            "expect_get": value_wire.hex(),
            "expect_clear": ext.ext_clear(set_wire, tag).hex(),
        })
    return rows


def test_js_resext_residual_and_extension_parity(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    cli.main([
        "gen", str(rb.IR_PATH), "-o", str(tmp_path), "--lang", "js",
        "--api-only", "--with-runtime", "--forward-compat",
    ])
    js_dir = tmp_path / "js"
    assert (js_dir / "api.js").exists()
    assert (js_dir / "cbor.js").exists()
    assert (js_dir / "ext.js").exists()

    residual_rows = json.loads(rb.RESIDUAL_PATH.read_text())
    ext_rows = json.loads(rb.EXT_PATH.read_text())
    fuzz_rows = _resext_fuzz_rows()
    harness = js_dir / "resext_parity.js"
    harness.write_text(textwrap.dedent(f"""
        "use strict";

        const {{ Host, Decision }} = require("./api.js");
        const {{ CInt, CMap, decode, encode }} = require("./cbor.js");
        const {{ extSet, extGet, extClear }} = require("./ext.js");

        const residualRows = {json.dumps(residual_rows)};
        const extRows = {json.dumps(ext_rows)};
        const fuzzRows = {json.dumps(fuzz_rows)};
        const seed = {RESEXT_FUZZ_SEED};

        function bytesFromHex(hex) {{
          const out = new Uint8Array(hex.length / 2);
          for (let i = 0; i < out.length; i++) {{
            out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
          }}
          return out;
        }}

        function hexFromBytes(bytes) {{
          return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
        }}

        function assertEq(got, want, note) {{
          if (got !== want) throw new Error(`${{note}}: got ${{got}}, want ${{want}}`);
        }}

        function expectThrows(fn, fragment, note) {{
          try {{
            fn();
          }} catch (err) {{
            const message = String(err && err.message ? err.message : err);
            if (message.includes(fragment)) return;
            throw new Error(`${{note}}: wrong error ${{message}}`);
          }}
          throw new Error(`${{note}}: did not throw`);
        }}

        if (typeof extSet !== "function" || typeof extGet !== "function" || typeof extClear !== "function") {{
          throw new Error("extension accessors are not exported");
        }}

        for (const row of residualRows) {{
          const decoded = Host.fromCbor(decode(bytesFromHex(row.wire)));
          assertEq(hexFromBytes(encode(decoded.toCbor())), row.wire, `residual corpus ${{row.note}}`);
        }}

        for (const row of extRows) {{
          const host = bytesFromHex(row.host);
          if (row.op === "set") {{
            const value = Decision.fromCbor(decode(bytesFromHex(row.value))).toCbor();
            assertEq(hexFromBytes(extSet(host, row.tag, value)), row.expect, `ext corpus ${{row.note}}`);
          }} else if (row.op === "get") {{
            const got = extGet(host, row.tag);
            if (row.expect === "null") {{
              if (got !== null) throw new Error(`ext corpus ${{row.note}}: got non-null`);
            }} else {{
              const value = Decision.fromCbor(got);
              assertEq(hexFromBytes(encode(value.toCbor())), row.expect, `ext corpus ${{row.note}}`);
            }}
          }} else if (row.op === "clear") {{
            assertEq(hexFromBytes(extClear(host, row.tag)), row.expect, `ext corpus ${{row.note}}`);
          }} else {{
            throw new Error(`unknown op ${{row.op}}`);
          }}
        }}

        expectThrows(
          () => extGet(new Uint8Array([0xff]), 1),
          "below the band",
          "below-band validation happens before host decode",
        );
        expectThrows(
          () => extSet(encode(CInt(7)), 1048577, CMap([])),
          "top-level CBOR map",
          "non-map host rejection",
        );

        let mismatches = 0;
        for (const row of fuzzRows) {{
          try {{
            const host = bytesFromHex(row.host);
            const decoded = Host.fromCbor(decode(host));
            assertEq(hexFromBytes(encode(decoded.toCbor())), row.host, `fuzz residual ${{row.note}}`);

            const value = Decision.fromCbor(decode(bytesFromHex(row.value))).toCbor();
            const setHex = hexFromBytes(extSet(host, row.tag, value));
            assertEq(setHex, row.expect_set, `fuzz extSet ${{row.note}}`);

            const got = Decision.fromCbor(extGet(bytesFromHex(row.expect_set), row.tag));
            assertEq(hexFromBytes(encode(got.toCbor())), row.expect_get, `fuzz extGet ${{row.note}}`);
            assertEq(
              hexFromBytes(extClear(bytesFromHex(row.expect_set), row.tag)),
              row.expect_clear,
              `fuzz extClear ${{row.note}}`,
            );
          }} catch (err) {{
            mismatches += 1;
            console.error(`seed=${{seed}} mismatch input=${{row.host}} error=${{err.message}}`);
          }}
        }}
        if (mismatches !== 0) throw new Error(`seed=${{seed}} mismatches=${{mismatches}}`);

        console.log(
          `js resext parity: residual=${{residualRows.length}} ext=${{extRows.length}} ` +
          `fuzz=${{fuzzRows.length}} seed=${{seed}} mismatches=${{mismatches}}`,
        );
    """))

    result = subprocess.run([node, str(harness)], check=True, text=True, capture_output=True)
    assert f"seed={RESEXT_FUZZ_SEED}" in result.stdout
    assert "mismatches=0" in result.stdout
