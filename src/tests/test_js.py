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
from taut.corpus import resext_build as rb
from taut.gen import js, scaffold
from taut.ir.dsl import BOOL, FLOAT, INT, MISSING_OK, STR, F, List, Map, Msg, schema as mk
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
