"""JS generator: ES classes + frozen enum objects + CBOR codec (CommonJS),
forward-compat residual."""

import itertools
import json
from pathlib import Path
import random
import shutil
import subprocess
import textwrap

import pytest
from taut import cli, ext
from taut.corpus.build import IR_PATH
from taut.corpus import parity, parity_js, toolchains
from taut.corpus import resext_build as rb
from taut.gen import js, scaffold
from taut.ir import options
from taut.ir.dsl import (
    BOOL, FLOAT, INT, MISSING_OK, STR, F, List, Map, Msg, Ref, extension, option, schema as mk,
)
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
LATE = mk(Msg("Late", F("note", 1, STR, optional=MISSING_OK)),
          Msg("Opt", F("note", 1, STR, optional=True)))
PAIRS = mk(Msg("Pairs", F("by_name", 1, Map(STR, INT))))
# `Note` holds a str field, and `Keyed` a map of each key type D24 allows.
TEXT_AND_KEYS = mk(Msg("Note", F("text", 1, STR)),
                   Msg("Keyed",
                       F("by_name", 1, Map(STR, INT)),
                       F("by_id", 2, Map(INT, INT)),
                       F("by_flag", 3, Map(BOOL, INT))))
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

    # Baseline smoke test: pin the reviewed set; `lead` rows belong to the
    # governed `tautc parity` gate (corpus/parity/gen_vectors.py).
    int_vectors = json.loads(PARITY_INT_VECTORS.read_text())
    int_vectors["vectors"] = [r for r in int_vectors["vectors"] if not r.get("lead")]
    malformed_vectors = json.loads(PARITY_MALFORMED_VECTORS.read_text())
    malformed_vectors["vectors"] = [r for r in malformed_vectors["vectors"] if not r.get("lead")]
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


_DECODE_PRELUDE = r'''
"use strict";
const api = require("./api.js");
const { decode, encode } = require("./cbor.js");

function fromHex(hex) {
  return Uint8Array.from(hex.match(/../g) || [], (x) => parseInt(x, 16));
}

function toHex(bytes) {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

// Decode `hex` as `message` and show the result, or the DecodeError as the parity
// gate reports it (`Tag;field=value`). Anything else that escapes fails the script.
function decodeAs(message, hex, show) {
  try {
    return show(api[message].fromCbor(decode(fromHex(hex))));
  } catch (e) {
    if (e == null || e.name !== "DecodeError") {
      throw e;
    }
    const fields = ["key", "expected"].filter((f) => e[f] !== undefined);
    return [e.tag, ...fields.map((f) => `${f}=${e[f]}`)].join(";");
  }
}

// A call's outcome as the parity gate reports one: `ok` and the hex of `show(value)`, or the
// DecodeError's `Tag;field=value...` with every payload field, or `untyped` for anything else.
const PAYLOAD = ["info", "major", "key", "expected", "enum", "value", "len", "limit"];
function outcome(call, show) {
  let value;
  try {
    value = call();
  } catch (e) {
    if (e == null || e.name !== "DecodeError" || typeof e.tag !== "string") {
      return `untyped ${e && e.name}: ${e && e.message}`;
    }
    return [e.tag, ...PAYLOAD.filter((f) => e[f] !== undefined).map((f) => `${f}=${e[f]}`)].join(";");
  }
  return `ok ${toHex(show(value))}`;
}
'''


def _run_js(tmp_path, schema, body):
    """Generate `schema` for js with its runtime, run `body` after the prelude above
    and return the JSON it prints."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    scaffold.emit(schema, tmp_path, langs=["js"], services=[], runtime=True)
    script = tmp_path / "js" / "cases.js"
    script.write_text(_DECODE_PRELUDE + textwrap.dedent(body))
    result = subprocess.run([node, str(script)], check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def test_js_missing_ok_reads_an_absent_key_as_null(tmp_path):
    """optional=MISSING_OK (TautCheckedDecode.md CD-E5, M16-M17): an absent key and a
    present null both read as null, a wrong type or a non-map is still refused, and
    encode still writes the key. A plain optional field still needs its key."""
    got = _run_js(tmp_path, LATE, """
        const note = (m) => m.note;
        console.log(JSON.stringify({
          absent: decodeAs("Late", "a0", note),
          presentNull: decodeAs("Late", "a101f6", note),
          present: decodeAs("Late", "a1016178", note),
          wrongType: decodeAs("Late", "a10101", note),
          notAMap: decodeAs("Late", "00", note),
          encodeUnset: toHex(encode(new api.Late().toCbor())),
          optionalAbsent: decodeAs("Opt", "a0", note),
        }));
    """)
    assert got == {
        "absent": None,
        "presentNull": None,
        "present": "x",
        "wrongType": "WrongType;expected=text",
        "notAMap": "WrongType;expected=map",
        "encodeUnset": "a101f6",
        "optionalAbsent": "MissingKey;key=1",
    }


def test_js_map_field_checks_an_entry_before_decoding_it(tmp_path):
    """A map<K,V> field is an array of {1: key, 2: value} entries. Each entry must be a
    map holding keys 1 and 2, checked before either is decoded, and a repeated key
    is DuplicateMapKey before its value is read (CD-E5, M13-M14), as in Python."""
    cases = {
        "ok": {1: [{1: "a", 2: 1}, {1: "b", 2: 2}]},
        "notArray": {1: 5},
        "entryNotMap": {1: [5]},
        "noKey": {1: [{2: 1}]},
        "noValue": {1: [{1: 7}]},                               # its key is wrong too
        "repeated": {1: [{1: "a", 2: 1}, {1: "a", 2: "x"}]},    # its value is wrong too
        "wrongValue": {1: [{1: "a", 2: "x"}]},
    }
    got = _run_js(tmp_path, PAIRS, f"""
        const cases = {json.dumps({name: cbor.dumps(v).hex() for name, v in cases.items()})};
        const out = {{}};
        for (const [name, hex] of Object.entries(cases)) {{
          out[name] = decodeAs("Pairs", hex, (m) => toHex(encode(m.toCbor())));
        }}
        console.log(JSON.stringify(out));
    """)
    assert got == {
        "ok": cbor.dumps(cases["ok"]).hex(),
        "notArray": "WrongType;expected=array",
        "entryNotMap": "WrongType;expected=map",
        "noKey": "MissingKey;key=1",
        "noValue": "MissingKey;key=2",
        "repeated": "DuplicateMapKey;key=a",
        "wrongValue": "WrongType;expected=int",
    }
    for name, value in cases.items():
        if name == "ok":
            continue
        with pytest.raises(codec.DecodeError) as err:
            codec.decode(PAIRS, "Pairs", cbor.dumps(value))
        payload = [f"{k}={v}" for k, v in err.value.payload.items()]
        assert ";".join([err.value.tag, *payload]) == got[name], name


# U+FEFF opening a text string is ordinary text (the parity row text-leading-bom): a
# UTF-8 decoder must not strip it as a byte-order mark. One after the start, or a
# second one, is the contrast: no decoder strips those.
_BOM_TEXTS = ["﻿a", "﻿", "﻿﻿a", "a﻿"]


def test_js_text_keeps_a_leading_bom(tmp_path):
    """Decode keeps a leading U+FEFF and re-encoding writes it back, raw and in a str
    field, as in Python. The decoder is still fatal: invalid UTF-8 after a U+FEFF is
    InvalidUtf8."""
    raw = [cbor.dumps(t).hex() for t in _BOM_TEXTS]
    typed = [codec.encode(TEXT_AND_KEYS, "Note", {"text": t}).hex() for t in _BOM_TEXTS]
    invalid = "a10164efbbbfff"  # a Note whose text is a U+FEFF, then a byte never in UTF-8
    got = _run_js(tmp_path, TEXT_AND_KEYS, f"""
        const raw = {json.dumps(raw)};
        const typed = {json.dumps(typed)};
        console.log(JSON.stringify({{
          raw: raw.map((hex) => {{
            const c = decode(fromHex(hex));
            return [c.s, toHex(encode(c))];
          }}),
          typed: typed.map((hex) => decodeAs("Note", hex, (m) => [m.text, toHex(encode(m.toCbor()))])),
          invalid: decodeAs("Note", "{invalid}", (m) => m.text),
        }}));
    """)
    assert got == {
        "raw": [[t, h] for t, h in zip(_BOM_TEXTS, raw)],
        "typed": [[t, h] for t, h in zip(_BOM_TEXTS, typed)],
        "invalid": "InvalidUtf8",
    }
    with pytest.raises(codec.DecodeError) as err:
        codec.decode(TEXT_AND_KEYS, "Note", bytes.fromhex(invalid))
    assert err.value.tag == "InvalidUtf8"


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


def _keyed_cases():
    """Each key set inserted in every order (forwards and backwards, above three keys),
    each key valued by its place in the set, with the bytes Python encodes: the same
    for every order. An int key travels as a string, exact above 2^53."""
    cases = []
    for name, (field, keys) in _KEY_SETS.items():
        value = {k: i + 1 for i, k in enumerate(keys)}
        orders = list(itertools.permutations(keys)) if len(keys) <= 3 else [keys, keys[::-1]]
        wire = codec.encode(TEXT_AND_KEYS, "Keyed",
                            {"by_name": {}, "by_id": {}, "by_flag": {}, field: value}).hex()
        for n, order in enumerate(orders):
            entries = [[str(k) if field == "by_id" else k, value[k]] for k in order]
            cases.append({"name": f"{name}/{n}", "field": field, "entries": entries, "hex": wire})
    return cases


def test_js_map_keys_encode_in_code_point_order(tmp_path):
    """Map keys encode in Python's order, a str key by code point, whatever the
    insertion order; each case's bytes also decode and re-encode to themselves (D2)."""
    assert sorted(_KEY_SETS["row"][1]) == ["a", "￿", "\U00010000"]  # the reference order
    cases = _keyed_cases()
    got = _run_js(tmp_path, TEXT_AND_KEYS, f"""
        const cases = {json.dumps(cases)};
        const out = {{}};
        for (const c of cases) {{
          const value = new api.Keyed({{ by_name: new Map(), by_id: new Map(), by_flag: new Map() }});
          for (const [k, v] of c.entries) {{
            value[c.field].set(c.field === "by_id" ? BigInt(k) : k, BigInt(v));
          }}
          out[c.name] = [toHex(encode(value.toCbor())), decodeAs("Keyed", c.hex, (m) => toHex(encode(m.toCbor())))];
        }}
        console.log(JSON.stringify(out));
    """)
    assert got == {c["name"]: [c["hex"], c["hex"]] for c in cases}


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

        function expectThrows(fn, name, fragment, note) {{
          try {{
            fn();
          }} catch (err) {{
            const message = String(err && err.message ? err.message : err);
            if (err && err.name === name && message.includes(fragment)) {{
              return err;
            }}
            throw new Error(`${{note}}: wrong error ${{err && err.name}} ${{message}}`);
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

        // A tag below the band is the caller's error, a RangeError thrown before the host
        // is read. A host that is not a map is WrongType{{map}}, a DecodeError like any bad
        // host (TautCheckedDecode.md CD-E4).
        expectThrows(
          () => extGet(new Uint8Array([0xff]), 1),
          "RangeError",
          "below the band",
          "below-band validation happens before host decode",
        );
        for (const [op, call] of [
          ["extGet", (host) => extGet(host, 1048577)],
          ["extSet", (host) => extSet(host, 1048577, CMap([]))],
          ["extClear", (host) => extClear(host, 1048577)],
        ]) {{
          const err = expectThrows(() => call(encode(CInt(7))), "DecodeError", "expected map", `${{op}}: non-map host rejection`);
          if (err.tag !== "WrongType" || err.expected !== "map") {{
            throw new Error(`${{op}}: a non-map host is ${{err.tag}} ${{err.expected}}, not WrongType map`);
          }}
        }}

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


# --- bounds (D26: TautCheckedDecode.md §3, CD-E4; D27: TautOptions.md OPT-D4, OPT-L6, G3) ----

PARITY_FIXTURE = parity.parity_schema()
# A file that declares both bounds, a message that overrides one and one that inherits both (as
# in test_bounds.py), so the generated constants show `effective`'s inheritance.
FILED = mk(option.max_depth(3), option.max_encoded_len(16),
           Msg("Tree", F("kids", 1, List(Ref("Tree"))), option.max_depth(64), next_id=2),
           Msg("Plain", F("v", 1, List(INT)), next_id=2))
EXT_TAG = BAND_START + 1
# Python's side of the extension helpers: a file whose tight bounds no helper applies.
EXT = mk(option.max_depth(2), option.max_encoded_len(8),
         Msg("Host", F("id", 1, INT), next_id=2),
         Msg("Decision", F("backend", 1, STR), F("hops", 2, INT), next_id=3),
         extension("Decision", tag=EXT_TAG))


def _nest(opener: str, count: int, leaf: str) -> str:
    """`count` copies of `opener`, then `leaf`, as hex: `_nest("81", 31, "80")` is 32 arrays."""
    return opener * count + leaf


def _python_outcome(call, show) -> str:
    """What the prelude's `outcome` reports, from Python, the reference."""
    try:
        value = call()
    except cbor.DecodeError as exc:
        return parity.format_error(exc.tag, exc.payload)
    return f"ok {show(value).hex()}"


def _js_limits(limits: dict) -> dict:
    """A raw call's limits, named as Python's `loads` names them, as cbor.js's options (CD-B3)."""
    names = {"max_depth": "maxDepth", "max_encoded_len": "maxEncodedLen"}
    return {names[name]: value for name, value in limits.items()}


_BIG = cbor.dumps(b"x" * 100_000).hex()
# Raw inputs beyond the corpus's B rows (as test_cbor.py's), each with the limits its call passes.
RAW_BOUNDS = [
    ("", {}),
    *[(_nest(opener, 31, leaf), {}) for opener, leaf in (("81", "80"), ("a100", "a0"), ("81", "a0"))],
    *[(_nest(opener, 32, leaf), {})
      for opener, leaf in (("81", "80"), ("a100", "a0"), ("81", "a0"), ("a100", "80"), ("81", "00"), ("a100", "00"))],
    *[(_nest("81a100", 16, leaf), {}) for leaf in ("00", "80", "a0")],
    # a top-level container has depth 1, and a map's key is one of its items
    *[(hexed, {"max_depth": 1}) for hexed in ("00", "6161", "80", "a0", "8100", "a10000", "820102",
                                              "8180", "81a0", "a10080", "a100a0", "820180", "a18000")],
    ("a18000", {"max_depth": 2}),
    # a depth argument applies as given; above the ceiling, the ceiling
    *[(_nest("81", count, "80"), {"max_depth": depth})
      for depth in (1, 2, 5, 31, 33, 64, 127, 128) for count in (depth - 1, depth)],
    *[(_nest("81", count, "80"), {"max_depth": depth}) for depth in (129, 1000, 2**31, 2**64) for count in (127, 128)],
    # the depth is checked once a container's head is complete, before its first item
    (_nest("81", 33, ""), {}), (_nest("a100", 32, "a1"), {}),
    *[(_nest("81", 32, head), {}) for head in ("9bffffffffffffffff", "bbffffffffffffffff", "98", "9900",
                                               "9a000000", "9b00", "b8", "bb00000000000000", "9800", "9c", "bf")],
    # far past any bound, and past node's stack
    *[(_nest(opener, 100_000, leaf), limits) for opener, leaf in (("81", "80"), ("a100", "a0"), ("81a100", "80"))
      for limits in ({}, {"max_depth": 128}, {"max_depth": 10**9})],
    # the length bound, checked before any byte is read; none unless one is passed
    ("83010203", {"max_encoded_len": 4}), ("83010203", {"max_encoded_len": 2**40}),
    ("83010203", {"max_encoded_len": 3}), ("c0c0c0c0", {"max_encoded_len": 3}),
    (_nest("81", 40, "80"), {"max_encoded_len": 10}), (_nest("81", 40, "80"), {"max_depth": 1, "max_encoded_len": 10}),
    ("0000", {"max_encoded_len": 1}), ("", {"max_encoded_len": 0}), ("00", {"max_encoded_len": 0}),
    (_BIG, {}), (_BIG, {"max_encoded_len": len(_BIG) // 2}), (_BIG, {"max_encoded_len": len(_BIG) // 2 - 1}),
]


def test_js_raw_decode_applies_the_callers_bounds_as_python_does(tmp_path):
    """cbor.js's `decode(data, { maxDepth, maxEncodedLen })` (CD-B1-B5, CD-E5): a top-level array
    or map has depth 1, and one deeper than the bound is TooDeep{limit} once its head is complete;
    a depth above the ceiling applies the ceiling; a length bound refuses longer input as TooLarge
    before a byte is read. Each outcome is what Python's `cbor.loads`, the reference, reports."""
    cases = [[hexed, _js_limits(limits)] for hexed, limits in RAW_BOUNDS]
    got = _run_js(tmp_path, TEXT_AND_KEYS, f"""
        const cases = {json.dumps(cases)};
        console.log(JSON.stringify(cases.map(([hex, limits]) => outcome(() => decode(fromHex(hex), limits), encode))));
    """)
    want = [_python_outcome(lambda: cbor.loads(bytes.fromhex(hexed), **limits), cbor.dumps)
            for hexed, limits in RAW_BOUNDS]
    assert got == want
    assert {"TooDeep;limit=1", "TooDeep;limit=32", "TooDeep;limit=128", "TooLarge;len=4;limit=3",
            "Truncated"} <= set(want)


def test_js_raw_decode_refuses_a_bad_bound_as_the_callers_error(tmp_path):
    """A depth below 1 or a negative length is a RangeError; a bound that is not an integer, an
    option decode does not know, or options that are not an object, a TypeError. Each is the
    caller's error, never a DecodeError, thrown before any byte is read (Python's ValueError and
    TypeError). An absent option, and a null length, is the default."""
    got = _run_js(tmp_path, TEXT_AND_KEYS, """
        const refused = {
          depthZero: { maxDepth: 0 },
          depthNegative: { maxDepth: -1 },
          depthFarNegative: { maxDepth: -(2 ** 64) },
          lengthNegative: { maxEncodedLen: -1 },
          lengthFarNegative: { maxEncodedLen: -(2 ** 64) },
          depthNull: { maxDepth: null },
          depthFraction: { maxDepth: 32.5 },
          depthText: { maxDepth: "32" },
          depthBool: { maxDepth: true },
          depthBigInt: { maxDepth: 32n },
          depthNaN: { maxDepth: NaN },
          depthInfinite: { maxDepth: Infinity },
          lengthFraction: { maxEncodedLen: 4.5 },
          lengthText: { maxEncodedLen: "4" },
          lengthBool: { maxEncodedLen: false },
          lengthBigInt: { maxEncodedLen: 4n },
          lengthInfinite: { maxEncodedLen: Infinity },
          unknownOption: { max_depth: 5 },
          notAnObject: 32,
          nullOptions: null,
        };
        const out = {};
        for (const [name, options] of Object.entries(refused)) {
          out[name] = ["", "00", "c0c0c0c0"].map((hex) => {
            try {
              decode(fromHex(hex), options);
            } catch (e) {
              return e.name;
            }
            return "no error";
          });
        }
        const nested = fromHex("818100");
        out.defaults = [undefined, {}, { maxDepth: undefined, maxEncodedLen: undefined }, { maxEncodedLen: null }]
          .map((options) => outcome(() => decode(nested, options), encode));
        out.given = [{ maxDepth: 1 }, { maxDepth: 2 }, { maxEncodedLen: 2 }, { maxEncodedLen: 3 }]
          .map((options) => outcome(() => decode(nested, options), encode));
        console.log(JSON.stringify(out));
    """)
    ranges = ("depthZero", "depthNegative", "depthFarNegative", "lengthNegative", "lengthFarNegative")
    assert {name: got.pop(name) for name in ranges} == {name: ["RangeError"] * 3 for name in ranges}
    assert got.pop("defaults") == ["ok 818100"] * 4
    assert got.pop("given") == ["TooDeep;limit=1", "ok 818100", "TooLarge;len=3;limit=2", "ok 818100"]
    assert got == {name: ["TypeError"] * 3 for name in got} and len(got) == 15


def test_js_runtime_exports_the_two_depth_numbers(tmp_path):
    """cbor.js's DEFAULT_MAX_DEPTH and MAX_DEPTH_CEILING are taut's (CD-B3)."""
    got = _run_js(tmp_path, TEXT_AND_KEYS, """
        const { DEFAULT_MAX_DEPTH, MAX_DEPTH_CEILING } = require("./cbor.js");
        console.log(JSON.stringify([DEFAULT_MAX_DEPTH, MAX_DEPTH_CEILING]));
    """)
    assert got == [options.DEFAULT_MAX_DEPTH, options.MAX_DEPTH_CEILING] == [32, 128]


def test_js_messages_carry_their_effective_bounds_as_constants(tmp_path):
    """Each generated class has MAX_DEPTH and MAX_ENCODED_LEN, null for none: its effective values,
    as `taut.ir.options.effective` resolves them at generation, the file's where the message
    declares none (CD-B3, CD-V2; TautOptions.md OPT-D3). They are constants: assigning one throws
    in strict code and changes nothing."""
    for name, schema in (("fixture", PARITY_FIXTURE), ("filed", FILED)):
        got = _run_js(tmp_path / name, schema, """
            const bounds = {};
            for (const [name, value] of Object.entries(api)) {
              if (typeof value === "function" && typeof value.fromCbor === "function") {
                bounds[name] = [value.MAX_DEPTH, value.MAX_ENCODED_LEN];
              }
            }
            const first = Object.keys(bounds)[0];
            let assigned = "no error";
            try {
              api[first].MAX_DEPTH = 1;
            } catch (e) {
              assigned = e.name;
            }
            console.log(JSON.stringify({ bounds, assigned, after: api[first].MAX_DEPTH }));
        """)
        assert got["bounds"] == {message: [options.effective(schema, "max_depth", message=message),
                                           options.effective(schema, "max_encoded_len", message=message)]
                                 for message in schema.messages}, name
        first = next(iter(schema.messages))
        assert (got["assigned"], got["after"]) == ("TypeError", got["bounds"][first][0]), name
    assert got["bounds"] == {"Tree": [64, 16], "Plain": [3, 16]}


# Typed inputs beyond the corpus's B rows (as test_bounds.py's): a message's own bounds and its file's.
TYPED_BOUNDS = [
    (FILED, "Tree", "a10181a10180"),                    # Tree{[Tree{[]}]}: 4 deep, its own 64
    (FILED, "Plain", "a10181818100"),                   # 4 deep, the file's 3, before WrongType{int}
    (FILED, "Plain", "a1018d" + "00" * 13),             # 16 bytes, the file's length bound
    (FILED, "Plain", "a1018e" + "00" * 14),             # 17 bytes
    (FILED, "Tree", "a1018e" + "00" * 14),              # its own depth, the file's length
    *[(PARITY_FIXTURE, message, _nest(opener, 100_000, "80"))
      for message, opener in (("Tree64", "a10181"), ("Tree128", "a10181"), ("Holds64", "a10181"), ("IntBox", "81"))],
]


def test_js_typed_decode_applies_its_roots_bounds(tmp_path):
    """`X.decode(bytes)` applies X.MAX_DEPTH and X.MAX_ENCODED_LEN through the raw decode, then
    `fromCbor` (CD-B3; TautOptions.md OPT-D4, OPT-L6): the root's own bounds, else its file's, and
    input 100,000 deep is TooDeep at the root's bound. Each outcome is what Python's
    `codec.decode` reports."""
    for name, schema in (("fixture", PARITY_FIXTURE), ("filed", FILED)):
        cases = [[message, hexed] for owner, message, hexed in TYPED_BOUNDS if owner is schema]
        got = _run_js(tmp_path / name, schema, f"""
            const cases = {json.dumps(cases)};
            console.log(JSON.stringify(cases.map(([message, hex]) =>
              outcome(() => api[message].decode(fromHex(hex)), (value) => encode(value.toCbor())))));
        """)
        want = [_python_outcome(lambda: codec.decode(schema, message, bytes.fromhex(hexed)),
                                lambda value: codec.encode(schema, message, value))
                for message, hexed in cases]
        assert got == want, name
    assert want == ["ok a10181a10180", "TooDeep;limit=3", "ok a1018d" + "00" * 13,
                    "TooLarge;len=17;limit=16", "TooLarge;len=17;limit=16"]


def test_js_typed_decode_takes_no_bound(tmp_path):
    """No call can raise or lower its root's bounds (CD-B3): `decode` takes the bytes alone, and a
    second argument changes nothing."""
    row = next(row for row in parity.bounds_rows() if row["name"] == "depth-65-declared")
    got = _run_js(tmp_path, PARITY_FIXTURE, f"""
        const deep = fromHex("{parity.row_bytes(row).hex()}");
        console.log(JSON.stringify([
          api.Tree64.decode.length,
          outcome(() => api.Tree64.decode(deep, {{ maxDepth: 128 }}), (value) => encode(value.toCbor())),
        ]));
    """)
    assert got == [1, "TooDeep;limit=64"]


def _ext_host(arrays: int) -> bytes:
    """A host map whose unknown field 7 holds `arrays` nested arrays: 1 + `arrays` deep."""
    return bytes.fromhex("a107" + _nest("81", arrays - 1, "80"))


def test_js_extension_helpers_read_a_host_at_the_ceiling_with_no_length_bound(tmp_path):
    """The helpers cannot name the host's root, so they read it at the depth ceiling with no length
    bound, the only bounds every valid host meets (CD-E4; TautOptions.md G3), as Python's do: a
    host 128 deep is read and one 129 deep is TooDeep{128}, and a host of 100,000 bytes is read,
    whatever its file declares."""
    hosts = {"at-ceiling": _ext_host(127), "over-ceiling": _ext_host(128), "far-over": _ext_host(100_000),
             "big": cbor.dumps({1: 1, 7: b"x" * 100_000})}
    decision = {"backend": "b7", "hops": 1}
    got = _run_js(tmp_path, TEXT_AND_KEYS, f"""
        const {{ CInt, CMap, CText }} = require("./cbor.js");
        const {{ extClear, extGet, extSet }} = require("./ext.js");
        const hosts = {json.dumps({name: host.hex() for name, host in hosts.items()})};
        const out = {{}};
        for (const [name, hex] of Object.entries(hosts)) {{
          const host = fromHex(hex);
          out[name] = [
            outcome(() => extGet(host, {EXT_TAG}), (value) => (value === null ? new Uint8Array(0) : encode(value))),
            outcome(() => extSet(host, {EXT_TAG}, CMap([[1, CText("b7")], [2, CInt(1n)]])), (bytes) => bytes),
            outcome(() => extClear(host, {EXT_TAG}), (bytes) => bytes),
          ];
        }}
        console.log(JSON.stringify(out));
    """)
    want = {name: [
        _python_outcome(lambda: ext.ext_get(EXT, host, "Decision", EXT_TAG), lambda value: b""),
        _python_outcome(lambda: ext.ext_set(EXT, host, "Decision", EXT_TAG, decision), lambda wire: wire),
        _python_outcome(lambda: ext.ext_clear(host, EXT_TAG), lambda wire: wire),
    ] for name, host in hosts.items()}
    assert got == want
    assert got["over-ceiling"] == got["far-over"] == ["TooDeep;limit=128"] * 3
    assert got["big"][2] == f"ok {hosts['big'].hex()}"


def _needs_node() -> None:
    if toolchains.find_node() is None:
        pytest.skip("node is not installed")


@pytest.mark.gate
def test_js_parity_gate_is_green():
    """`tautc parity -t js`: every int, malformed and bounds row through the generated JS codec,
    as js and js/fc, each held to the gate's governance: GREEN, or RED and allowlisted."""
    _needs_node()
    reports, violations = parity.governed_variants(parity_js.run)
    assert violations == [], "\n".join(violations)
    assert [(report.target, report.available) for report in reports] == [("js", True), ("js/fc", True)]


def test_the_js_runner_reports_its_runtimes_own_constants(monkeypatch):
    """The #constants line comes from cbor.js's DEFAULT_MAX_DEPTH and MAX_DEPTH_CEILING (the bounds
    protocol, item 1), so a runtime whose default drifts fails its target."""
    _needs_node()
    generate = parity.generate

    def drifted(name, out_dir, **emit_options):
        failed = generate(name, out_dir, **emit_options)
        runtime = out_dir / "js" / "cbor.js"
        source = runtime.read_text()
        assert "const DEFAULT_MAX_DEPTH = 32;" in source
        runtime.write_text(source.replace("const DEFAULT_MAX_DEPTH = 32;", "const DEFAULT_MAX_DEPTH = 31;"))
        return failed

    monkeypatch.setattr(parity, "generate", drifted)
    report = parity_js.run()
    assert report.fault.splitlines()[0] == (
        "#constants default_max_depth=31;max_depth_ceiling=128, expected default_max_depth=32;max_depth_ceiling=128")


def test_the_js_runner_reports_a_row_that_expands_to_another_length_as_untyped(monkeypatch):
    """The runner expands a row's segments itself and reports an expansion whose length is not the
    row's `len` as untyped (the bounds protocol, item 5), a from_cbor row with its bounds."""
    _needs_node()
    write = parity.write_json_rows

    def misstated(dest, schema=None):
        write(dest, schema)
        path = dest / parity.BOUNDS_VECTORS.name
        data = json.loads(path.read_text())
        for row in data["vectors"]:
            if row["name"] in ("depth-33-arrays", "depth-2-declared"):
                row["len"] += 1
        path.write_text(json.dumps(data))

    monkeypatch.setattr(parity, "write_json_rows", misstated)
    report = parity_js.run()
    assert not report.fault
    assert {r.name: r.detail.split(" ")[0] for r in report.failures} == {
        "depth-33-arrays": "untyped", "depth-2-declared": "untyped"}
