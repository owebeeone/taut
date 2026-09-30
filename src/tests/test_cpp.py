import json
import random
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from taut import cli, ext
from taut.corpus import build, parity, parity_cpp
from taut.corpus import resext_build as resext
from taut.gen import cpp as cpp_gen
from taut.gen import scaffold
from taut.ir import options
from taut.ir.load import load_schema
from taut.ir.model import MsgRef
from taut.ir.shapes import BAND_START
from taut.ir.dsl import (
    BOOL, BYTES, FLOAT, INT, MISSING_OK, STR, Enum, F, List, Map, Msg, Ref, option, schema as mk,
)
from taut.ir.validate import validate
from taut.wire import cbor, codec


RUNTIME = Path(cpp_gen.__file__).resolve().parent / "runtime"

S_SCALAR_LIST = mk(Msg("M",
                       F("x", 1, FLOAT),
                       F("xs", 2, List(FLOAT))))

S_MAP_SHAPE = mk(Msg("M",
                     F("x", 1, FLOAT),
                     F("xs", 2, List(FLOAT)),
                     F("by_id", 3, Map(INT, FLOAT))))


def _cpp_bytes(data: bytes) -> str:
    escaped = "".join(f"\\x{b:02x}" for b in data)
    return f'std::string_view("{escaped}", {len(data)})'


def _ident(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z_]", "_", name)


def _cpp_compiler() -> str:
    compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
    if compiler is None:
        pytest.skip("no C++ compiler on PATH")
    return compiler


def _compile_and_run_cpp(tmp_path: Path, source: str, name: str) -> subprocess.CompletedProcess[str]:
    compiler = _cpp_compiler()
    src = tmp_path / f"{name}.cpp"
    src.write_text(source)
    exe = tmp_path / name
    result = subprocess.run(
        [compiler, "-std=c++20", "-I", str(tmp_path / "cpp"), str(src), "-o", str(exe)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, textwrap.dedent(f"""\
        command: {compiler} -std=c++20 -I {tmp_path / "cpp"} {src} -o {exe}
        stdout:
        {result.stdout}
        stderr:
        {result.stderr}
    """)
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, textwrap.dedent(f"""\
        command: {exe}
        stdout:
        {run.stdout}
        stderr:
        {run.stderr}
    """)
    return run


def _resext_schema():
    return load_schema(resext.IR_PATH)


def _resext_cpp_rows():
    s = _resext_schema()
    residual_rows = [
        {"note": r["note"], "wire": r["wire"]}
        for r in json.loads(resext.RESIDUAL_PATH.read_text())
    ]
    ext_rows = json.loads(resext.EXT_PATH.read_text())
    return s, residual_rows, ext_rows


def _fuzz_value(rng: random.Random, depth: int = 0):
    choice = rng.randrange(7 if depth == 0 else 6)
    if choice == 0:
        return rng.randint(-50, 200)
    if choice == 1:
        return rng.choice([True, False, None])
    if choice == 2:
        return f"s{rng.randrange(1000)}"
    if choice == 3:
        return bytes(rng.randrange(256) for _ in range(rng.randrange(0, 8)))
    if choice == 4:
        return [rng.randint(-10, 10) for _ in range(rng.randrange(0, 4))]
    if choice == 5:
        return [f"a{rng.randrange(100)}", rng.choice([True, False]), rng.randint(0, 9)]
    return rng.choice([0.0, -0.0, 0.5, 1.5, 100000.0])


def _cpp_string_literal(s: str) -> str:
    return json.dumps(s)


def _cpp_rows(rows: list[dict], keys: list[str]) -> str:
    rendered = []
    for row in rows:
        rendered.append("{" + ", ".join(_cpp_string_literal(str(row[k])) for k in keys) + "}")
    return ",\n".join(rendered)


def test_cpp_codegen_threads_float_scalar_and_list():
    hpp = cpp_gen._emit_types(S_SCALAR_LIST)
    assert "double x;" in hpp
    assert "std::vector<double> xs;" in hpp
    assert "__b.float_(x);" in hpp
    assert "for (const auto& __x : xs) { __b.float_(__x); }" in hpp
    assert ".try_float()" in hpp
    assert cpp_gen._render(S_SCALAR_LIST, FLOAT, -0.0) == "taut::f64_from_bits(0x8000000000000000ULL)"


def test_cpp_codegen_threads_float_map_string_shape_only():
    # Generated constexpr std::map iteration is not portable under C++20 libc++;
    # scalar/list float generated code is the compiled C++20 coverage below.
    hpp = cpp_gen._emit_types(S_MAP_SHAPE)
    assert "std::map<long long, double> by_id;" in hpp
    assert "for (const auto& [__k, __v] : by_id)" in hpp
    assert "__b.float_(__v);" in hpp
    assert "auto __decoded_3_v = (*__decoded_3_val_cbor.value).try_float();" in hpp


def test_cpp_codegen_emits_fallible_decode_path_for_i64_and_enums():
    root = Path(__file__).resolve().parents[2]
    schema = load_schema(root / "ir" / "parity_int.taut.py")
    hpp = cpp_gen._emit_types(schema)
    assert "inline constexpr DecodeResult<Mode> try_Mode_from_wire(long long v)" in hpp
    assert 'DecodeError::unknown_enum("Mode", v)' in hpp
    assert "static ::taut::DecodeResult<::taut::IntBox> try_from_cbor(const ::taut::Cbor& __c)" in hpp
    assert "auto __decoded_1 = (*__field_1.value).try_int();" in hpp
    assert "auto __decoded_2_arr = (*__field_2.value).try_array();" in hpp
    assert "auto __decoded_2_k = (*__decoded_2_key_cbor.value).try_int();" in hpp
    assert "auto __decoded_2_v = (*__decoded_2_val_cbor.value).try_int();" in hpp


def _struct_text(hpp: str, name: str) -> str:
    """The generated `struct name { ... }`."""
    start = hpp.index(f"struct {name} {{")
    return hpp[start:hpp.index("\n};", start)]


def test_cpp_codegen_emits_each_messages_bounds_and_typed_decode():
    """Each struct carries its effective bounds as constants, resolved at generation, and a
    `try_decode` from bytes that hands them to the raw decode and reads the tree with
    `try_from_cbor` (TautOptions.md OPT-L6); both constexpr where the struct is a literal type."""
    schema = parity.parity_schema()
    for forward_compat in (False, True):
        hpp = cpp_gen._emit_types(schema, forward_compat)
        for name, msg in schema.messages.items():
            text = _struct_text(hpp, name)
            depth = options.effective(schema, "max_depth", message=name)
            length = options.effective(schema, "max_encoded_len", message=name)
            qual = "constexpr " if cpp_gen._literal(schema, msg) else ""
            assert f"  static constexpr std::size_t max_depth = {depth};" in text
            assert ("  static constexpr std::optional<std::size_t> max_encoded_len = "
                    f"{'std::nullopt' if length is None else length};") in text
            assert (f"  static {qual}::taut::DecodeResult<::taut::{name}> try_decode(std::string_view __data) {{"
                    in text)
            assert f"::taut::try_decode(__data, ::taut::{name}::max_depth, ::taut::{name}::max_encoded_len)" in text
            assert f"return ::taut::{name}::try_from_cbor(__tree.value);" in text
    # The fixture's bounds messages: CD-C1's declarations, and the defaults elsewhere.
    hpp = cpp_gen._emit_types(schema)
    assert "max_depth = 64;" in _struct_text(hpp, "Tree64")
    assert "max_encoded_len = 8;" in _struct_text(hpp, "Sized8")
    assert "max_encoded_len = std::nullopt;" in _struct_text(hpp, "HoldsSized8")
    assert "static ::taut::DecodeResult<::taut::IntBox> try_decode(" in _struct_text(hpp, "IntBox")


def test_cpp_passes_the_parity_gate():
    """Every row of the shared corpus through the gate's C++ runner (`tautc parity -t cpp`),
    as cpp and cpp/fc, each held to the gate's governance: GREEN, or RED and allowlisted."""
    reports, violations = parity.governed_variants(parity_cpp.run)
    for report in reports:
        if not report.available:
            pytest.skip(report.skip_reason)
    assert violations == [], "\n".join(violations)
    # Only an encode-fail row may be satisfied by the type system; every other row ran.
    for report in reports:
        if not report.fault:
            satisfied = {r.name for r in report.results if r.status == parity.TYPE_SATISFIED}
            assert satisfied == {r["name"] for r in parity.int_rows() if r["kind"] == "encode_fail"}, \
                report.target


# Inputs beyond the shared corpus, each with the result Python (the reference) gives:
# CD-E5's order of checks and D2's strictness where the corpus has a single row. A row's bytes
# are hex or, as in bounds.vectors.json, a list of segments; a raw row may end with the limits
# its call passes.
BEYOND_THE_CORPUS = [
    # name, stage, schema, bytes, expected[, limits]
    ("map-key-is-a-tag", "raw_decode", "", "a1c000", "UnsupportedMajor;major=6"),
    ("map-key-reserved-info", "raw_decode", "", "a17f", "UnsupportedInfo;info=31"),
    ("map-key-invalid-utf8", "raw_decode", "", "a161ff00", "InvalidUtf8"),
    ("map-key-truncated-text", "raw_decode", "", "a16278", "Truncated"),
    ("map-key-bool", "raw_decode", "", "a1f500", "NonIntegerMapKey"),
    ("map-key-overflow", "raw_decode", "", "a13b800000000000000000", "IntOverflow;value=-9223372036854775809"),
    ("map-key-negative-after-an-entry", "raw_decode", "", "a2000020", "NegativeMapKey;key=-1"),
    ("nested-map-key-negative", "raw_decode", "", "a101a12000", "NegativeMapKey;key=-1"),
    ("non-canonical-negative-int", "raw_decode", "", "3800", "NonCanonicalInt;value=0"),
    ("non-canonical-4-byte-int", "raw_decode", "", "1a0000ffff", "NonCanonicalInt;value=65535"),
    ("non-canonical-8-byte-int", "raw_decode", "", "1b00000000ffffffff", "NonCanonicalInt;value=4294967295"),
    ("canonical-8-byte-int", "raw_decode", "", "1b0000000100000000", "accept"),
    ("non-canonical-text-length", "raw_decode", "", "5800", "NonCanonicalInt;value=0"),
    ("non-canonical-array-count", "raw_decode", "", "9817" + "00" * 23, "NonCanonicalInt;value=23"),
    ("non-canonical-map-count", "raw_decode", "", "b9000100f6", "NonCanonicalInt;value=1"),
    # Decode takes any float width; re-encode writes the shortest (G2, question 7, open).
    ("float-width-is-not-checked", "raw_decode", "", "fb0000000000000000", "accept;reencode=f90000"),
    ("simple-value-24", "raw_decode", "", "f818", "UnsupportedInfo;info=24"),
    ("simple-value-23", "raw_decode", "", "f7", "UnsupportedInfo;info=23"),
    ("indefinite-array", "raw_decode", "", "9f", "UnsupportedInfo;info=31"),
    ("tag-with-info-31", "raw_decode", "", "df", "UnsupportedMajor;major=6"),
    ("text-length-over-2^32", "raw_decode", "", "7b00000001000000006161", "Truncated"),
    ("array-count-over-2^32", "raw_decode", "", "9b000000010000000001", "Truncated"),
    ("text-truncated-before-utf8", "raw_decode", "", "62c3", "Truncated"),
    ("text-surrogate", "raw_decode", "", "63eda080", "InvalidUtf8"),
    ("empty-input", "raw_decode", "", "", "Truncated"),
    ("required-field-null", "from_cbor", "IntBox", "a201f60280", "WrongType;expected=int"),
    ("map-field-not-an-array", "from_cbor", "IntBox", "a2010002a0", "WrongType;expected=array"),
    ("map-entry-not-a-map", "from_cbor", "IntBox", "a20100028100", "WrongType;expected=map"),
    ("map-entry-key-1-first", "from_cbor", "IntBox", "a201000281a0", "MissingKey;key=1"),
    ("map-duplicate-before-its-value", "from_cbor", "IntBox", "a201000282a201050201a2010502f6",
     "DuplicateMapKey;key=5"),
    ("enum-field-unknown", "from_cbor", "EnumBox", "a1011863", "UnknownEnum;enum=Mode;value=99"),
    ("list-item-wrong-type", "from_cbor", "OptBox", "a201f6028101", "WrongType;expected=text"),
    ("message-not-a-map", "from_cbor", "OptBox", "80", "WrongType;expected=map"),
    # No `empty-message-ignores-unknown-fields` row (Empty, a10100): Python keeps an unknown
    # field (a10100) and C++ without forward-compat drops it (a0), so the corpus's
    # `unknown-field-*` rows pin it with `expect_dropping` (question 10).
    ("enum-wire-negative", "from_wire", "Mode", "20", "UnknownEnum;enum=Mode;value=-1"),
    ("enum-wire-not-an-int", "from_wire", "Mode", "f6", "WrongType;expected=int"),
    # The bounds (TautCheckedDecode.md §3) beyond B1-B30. The raw decode with the limits its
    # call passes: the least depth, a map's key and value each one deeper than the map, both
    # limits in one call (length first), and the head's own checks before depth.
    ("depth-1-flat-array", "raw_decode", "", "8100", "accept", {"max_depth": 1}),
    ("depth-1-nested-array", "raw_decode", "", "8180", "TooDeep;limit=1", {"max_depth": 1}),
    ("depth-1-map-in-an-array", "raw_decode", "", "81a0", "TooDeep;limit=1", {"max_depth": 1}),
    ("depth-1-map-key-container", "raw_decode", "", "a18000", "TooDeep;limit=1", {"max_depth": 1}),
    ("depth-2-map-value", "raw_decode", "", "a100a100a0", "TooDeep;limit=2", {"max_depth": 2}),
    ("length-before-depth", "raw_decode", "", "81818180", "TooLarge;len=4;limit=3",
     {"max_depth": 2, "max_encoded_len": 3}),
    ("depth-within-length", "raw_decode", "", "818180", "TooDeep;limit=2",
     {"max_depth": 2, "max_encoded_len": 3}),
    ("length-0-one-byte", "raw_decode", "", "00", "TooLarge;len=1;limit=0", {"max_encoded_len": 0}),
    ("non-canonical-count-before-depth", "raw_decode", "", [{"repeat": "81", "count": 32}, "9800"],
     "NonCanonicalInt;value=0"),
    ("raw-100000-deep-at-the-ceiling", "raw_decode", "", [{"repeat": "81", "count": 99999}, "80"],
     "TooDeep;limit=128", {"max_depth": 128}),
    # The typed decode from bytes, rooted at the bounds messages (and IntBox): each root's own
    # bounds, raw faults before the schema's, and the schema stage within the bounds.
    ("typed-100000-deep-unknown-field", "from_cbor", "IntBox",
     ["a30100028009", {"repeat": "81", "count": 99999}, "80"], "TooDeep;limit=32"),
    ("tree128-100000-deep", "from_cbor", "Tree128", [{"repeat": "a10181", "count": 99999}, "a10180"],
     "TooDeep;limit=128"),
    ("tree64-kid-not-a-map", "from_cbor", "Tree64", "a1018101", "WrongType;expected=map"),
    ("tree64-kids-absent", "from_cbor", "Tree64", "a0", "MissingKey;key=1"),
    ("flat2-item-not-an-int", "from_cbor", "Flat2", "a101816178", "WrongType;expected=int"),
    ("flat2-too-deep-before-not-a-map", "from_cbor", "Flat2", "818180", "TooDeep;limit=2"),
    ("sized8-length-before-parse", "from_cbor", "Sized8", "c0" * 9, "TooLarge;len=9;limit=8"),
    ("sized8-at-its-length-not-bytes", "from_cbor", "Sized8", "a101656162636465", "WrongType;expected=bytes"),
    ("holds64-tree-within-32", "from_cbor", "Holds64", ["a101", {"repeat": "a10181", "count": 14}, "a10180"],
     "accept"),
    ("holds-sized8-inner-not-bytes", "from_cbor", "HoldsSized8", "a101a10101", "WrongType;expected=bytes"),
]


def _beyond_rows(schema) -> list[dict]:
    """BEYOND_THE_CORPUS as corpus rows, each with its expanded `len` and, but for a from_wire
    row, the `bounds` it is decoded under (`parity.decoded_under`), which the gate compares with
    a from_cbor row's fourth column."""
    rows = []
    for name, stage, message, data, expected, *limits in BEYOND_THE_CORPUS:
        row = {"name": f"beyond-{name}", "stage": stage, "schema": message, "bytes": data,
               "why": "C++ decodes as Python does"}
        if limits:
            row["limits"] = limits[0]
        tag, payload = parity.parse_error(expected)
        if tag == "accept":
            row["expect"] = {"accept": True, **payload}  # `;reencode=` where it is not the input
        else:
            row["expect"] = {"tag": tag, **payload}
        row["len"] = len(parity.row_bytes(row))
        if stage != "from_wire":
            row["bounds"] = parity.decoded_under(schema, row)
        rows.append(row)
    return rows


def _python_resolved(schema, row: dict) -> str | None:
    """The fourth column Python's harness reports for `row`: a from_cbor row's bounds as
    `codec.bounds` resolves its message, and nothing for any other row."""
    if row["stage"] != "from_cbor":
        return None
    depth, length = codec.bounds(schema, MsgRef(row["schema"]))
    return parity.format_bounds({"max_depth": depth, "max_encoded_len": length})


def test_cpp_decode_matches_python_beyond_the_corpus(monkeypatch):
    """The gate's C++ runner, with the rows above appended to the corpus, stays green: the
    bounds rows run too, and each typed row beyond the corpus reports the bounds its root
    resolved, which the gate compares with the reference's."""
    schema = parity.parity_schema()
    extra = _beyond_rows(schema)
    # The table is the reference's behaviour, not a guess.
    observed = [(row["name"], parity._observe_python(schema, row)) for row in extra]
    assert [(name, outcome) for name, (outcome, _) in observed if outcome == parity.UNTYPED] == []
    assert [parity.judge("python", row, *seen, resolved=_python_resolved(schema, row))
            for row, (_, seen) in zip(extra, observed)] == [(parity.PASS, "")] * len(extra)
    # Every bounds message is a root here, beyond B17-B30.
    assert {row["schema"] for row in extra if row["stage"] == "from_cbor"} >= \
        {row["schema"] for row in parity.bounds_rows() if row["stage"] == "from_cbor"}

    listed = {s.target: s for s in parity.target_statuses() if s.status == "allowlisted"}
    if "cpp" in listed:  # the whole fixture must build and pass before the rows beyond it can
        pytest.skip(f"cpp is allowlisted in corpus/parity/allowlist.json (phase {listed['cpp'].phase}): "
                    f"{listed['cpp'].reason}")
    corpus = parity.malformed_rows()
    monkeypatch.setattr(parity, "malformed_rows", lambda: [*corpus, *extra])
    report = parity_cpp.run()
    if not report.available:
        pytest.skip(report.skip_reason)
    assert len(report.results) == \
        len(parity.int_rows()) + len(corpus) + len(extra) + len(parity.bounds_rows())
    failures = [f"{r.name}: {r.detail}" for r in report.failures]
    assert report.green, "\n".join([report.fault, *failures])


def test_cpp_runner_reports_a_row_whose_bytes_do_not_expand_to_its_len_as_untyped(monkeypatch):
    """The bounds protocol, item 5: the runner expands a row's segments itself and reports an
    expansion whose length is not the row's `len` as `untyped`, a typed row still with the
    bounds its entry point resolved; it prints its `#constants` line once."""
    rows = {row["name"]: row for row in parity.bounds_rows()}
    raw = {**rows["depth-33-arrays"], "len": 34}
    typed = {**rows["depth-64-declared"], "len": 1}
    monkeypatch.setattr(parity, "int_rows", lambda: [])
    monkeypatch.setattr(parity, "malformed_rows", lambda: [])
    monkeypatch.setattr(parity, "bounds_rows", lambda: [raw, typed])
    report = parity_cpp.run()
    if not report.available:
        pytest.skip(report.skip_reason)
    assert report.fault == ""
    assert [(r.name, r.status) for r in report.results] == [(raw["name"], parity.FAIL),
                                                             (typed["name"], parity.FAIL)]
    assert report.results[0].detail.startswith("untyped bytes expand to 33 bytes, len is 34")
    assert report.results[1].detail.startswith("untyped bytes expand to 96 bytes, len is 1")


# --- the bounds (D26: TautCheckedDecode.md §3; TautOptions.md OPT-D4, OPT-L6) ---------------

def _arrays(depth: int) -> bytes:
    """`depth` nested arrays, the innermost empty."""
    return b"\x81" * (depth - 1) + b"\x80"


def test_cpp_raw_decode_applies_its_bounds_at_compile_time(tmp_path):
    """The runtime's two depth numbers are taut's. Its raw decode counts depth from the top-level
    container, applies 32 or its caller's depth capped at 128, and checks a length bound before
    it reads a byte, all constexpr (CD-B1-B5, question 1). A depth below 1 is the caller's error,
    std::invalid_argument, not a DecodeError."""
    compiler = _cpp_compiler()
    (tmp_path / "taut").mkdir()
    (tmp_path / "taut" / "cbor.hpp").write_text((RUNTIME / "cbor.hpp").read_text())
    counted = _cpp_bytes(bytes.fromhex("83010203"))
    source = tmp_path / "raw_bounds.cpp"
    source.write_text(f"""
#include "taut/cbor.hpp"

#include <iostream>
#include <stdexcept>
#include <string_view>

using Tag = taut::DecodeErrorTag;

constexpr bool too_deep(const taut::DecodeResult<taut::Cbor>& r, std::size_t limit) {{
    return !r && r.error.tag == Tag::TooDeep && r.error.limit == limit;
}}

constexpr bool too_large(const taut::DecodeResult<taut::Cbor>& r, std::size_t len, std::size_t limit) {{
    return !r && r.error.tag == Tag::TooLarge && r.error.len == len && r.error.limit == limit;
}}

static_assert(taut::default_max_depth == {options.DEFAULT_MAX_DEPTH});
static_assert(taut::max_depth_ceiling == {options.MAX_DEPTH_CEILING});
// Depth: the default, a caller's, and a caller's above the ceiling, which applies the ceiling.
static_assert(taut::try_decode({_cpp_bytes(_arrays(32))}).ok);
static_assert(too_deep(taut::try_decode({_cpp_bytes(_arrays(33))}), 32));
static_assert(taut::try_decode({_cpp_bytes(_arrays(1))}, 1).ok);
static_assert(too_deep(taut::try_decode({_cpp_bytes(_arrays(2))}, 1), 1));
static_assert(too_deep(taut::try_decode({_cpp_bytes(_arrays(129))}, 1000), 128));
// Length: exactly at the bound, one byte over, before any byte is read, and nothing at 0.
static_assert(taut::try_decode({counted}, taut::default_max_depth, 4).ok);
static_assert(too_large(taut::try_decode({counted}, taut::default_max_depth, 3), 4, 3));
static_assert(too_large(taut::try_decode({_cpp_bytes(bytes.fromhex("c0c0c0c0"))}, 1, 3), 4, 3));
static_assert(taut::try_decode(std::string_view(), 1, 0).error.tag == Tag::Truncated);

int main() {{
    auto capped = taut::try_decode({_cpp_bytes(_arrays(128))}, 1000);
    std::cout << "depth-128-capped\\t" << (capped ? "ok" : "refused") << "\\n";
    try {{
        auto r = taut::try_decode({_cpp_bytes(_arrays(1))}, 0);
        std::cout << "depth-0\\t" << (r ? "ok" : "refused") << "\\n";
    }} catch (const std::invalid_argument&) {{
        std::cout << "depth-0\\tcaller-error\\n";
    }}
    return 0;
}}
""")
    exe = tmp_path / "raw_bounds"
    result = subprocess.run([compiler, "-std=c++20", "-I", str(tmp_path), str(source), "-o", str(exe)],
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout.splitlines() == ["depth-128-capped\tok", "depth-0\tcaller-error"]
    # The reference agrees: a depth below 1 is its caller's error too.
    with pytest.raises(ValueError, match="at least 1"):
        cbor.loads(_arrays(1), max_depth=0)


# A file that declares both bounds, a message that declares its own, and a tree at the ceiling.
S_BOUNDS = mk(option.max_depth(16), option.max_encoded_len(4096),
              Msg("Inherits", F("n", 1, INT)),
              Msg("Own", F("xs", 1, List(INT)), option.max_depth(3), option.max_encoded_len(64)),
              Msg("Deeper", F("kids", 1, List(Ref("Deeper"))), option.max_depth(128)))

# Inputs to each root's typed decode from bytes: message, hex.
S_BOUNDS_INPUTS = [
    ("Own", "a101820102"),                          # within both bounds
    ("Own", "a101818100"),                          # 3 deep, Own's bound: the schema refuses it
    ("Own", "a101818180"),                          # 4 deep: TooDeep{3}
    ("Own", "a101983c" + "00" * 60),                # 64 bytes, Own's length
    ("Own", "a101983d" + "00" * 61),                # 65 bytes: TooLarge{65, 64}
    ("Own", "c0" * 65),                             # length before a byte is read
    ("Own", "81818180"),                            # depth before the schema stage
    ("Inherits", "a101" + "81" * 14 + "80"),        # 16 deep, the file's bound: the schema refuses it
    ("Inherits", "a102" + "81" * 15 + "80"),        # 17 deep, an unknown field: TooDeep{16}
    ("Deeper", "a10181" * 63 + "a10180"),           # 128 deep, the ceiling
    ("Deeper", "a10181" * 64 + "a10180"),           # 129 deep: TooDeep{128}
]


def _literal_of(value) -> str:
    return "std::nullopt" if value is None else f"std::optional<std::size_t>({value})"


def test_cpp_messages_carry_their_effective_bounds_and_decode_under_them(tmp_path):
    """Each struct's `max_depth` and `max_encoded_len` are its effective values, resolved at
    generation by `options.effective` (the message's, else the file's, else the defaults), and
    its `try_decode` from bytes applies both (CD-B3, OPT-L6): as the reference does, and at
    compile time where the struct is a literal type."""
    assert validate(S_BOUNDS) == []
    constants = []
    for name in S_BOUNDS.messages:
        depth = options.effective(S_BOUNDS, "max_depth", message=name)
        length = options.effective(S_BOUNDS, "max_encoded_len", message=name)
        constants.append(f"static_assert(taut::{name}::max_depth == {depth});")
        constants.append(f"static_assert(taut::{name}::max_encoded_len == {_literal_of(length)});")
    assert "static_assert(taut::Inherits::max_depth == 16);" in constants  # the file's
    assert "static_assert(taut::Own::max_encoded_len == std::optional<std::size_t>(64));" in constants
    prints = [f'    std::cout << "{message} {hexed}\\t" << checked<taut::{message}>("{hexed}") << "\\n";'
              for message, hexed in S_BOUNDS_INPUTS]
    observed = _observe(tmp_path, S_BOUNDS, "\n".join([
        "#include <optional>",
        "#include <type_traits>",
        "",
        "static_assert(std::is_same_v<decltype(taut::Own::max_depth), const std::size_t>);",
        "static_assert(std::is_same_v<decltype(taut::Own::max_encoded_len), const std::optional<std::size_t>>);",
        *constants,
        "// Own holds no map, so its typed decode runs at compile time too.",
        "static_assert(taut::Own::try_decode(std::string_view(\"\\xa1\\x01\\x82\\x01\\x02\", 5)).ok);",
        "static_assert(taut::Own::try_decode(std::string_view(\"\\xa1\\x01\\x81\\x81\\x80\", 5)).error.tag",
        "              == taut::DecodeErrorTag::TooDeep);",
        "static_assert(taut::Own::try_decode(std::string_view(\"\\xa1\\x01\\x81\\x81\\x80\", 5)).error.limit == 3);",
        "",
        "int main() {",
        *prints,
        "    return 0;",
        "}",
    ]))
    expected = {f"{message} {hexed}": _reference_outcome(S_BOUNDS, message, bytes.fromhex(hexed))
                for message, hexed in S_BOUNDS_INPUTS}
    assert [expected[f"{message} {hexed}"].split(";")[0] for message, hexed in S_BOUNDS_INPUTS] == [
        f"ok {S_BOUNDS_INPUTS[0][1]}", "err WrongType", "err TooDeep", f"ok {S_BOUNDS_INPUTS[3][1]}",
        "err TooLarge", "err TooLarge", "err TooDeep", "err WrongType", "err TooDeep",
        f"ok {S_BOUNDS_INPUTS[9][1]}", "err TooDeep"]
    assert observed == expected


def _raw_reference(call) -> str:
    """A call's outcome as the C++ harness reports it: `ok`, or its DecodeError as
    `Tag;field=value` (`parity.format_error`)."""
    try:
        call()
    except cbor.DecodeError as exc:
        return parity.format_error(exc.tag, exc.payload)
    return "ok"


def test_cpp_nothing_escapes_a_100000_deep_input(tmp_path):
    """Input 100,000 deep is TooDeep, never a stack overflow, from every decode entry point
    (TautCheckedDecode.md CD-E4): the raw decode at its default bound, 32, and at the ceiling;
    a typed decode at its root's bound, unknown fields included; and the extension helpers,
    which read a host at the ceiling. Each outcome is the reference's."""
    s = parity.parity_schema()
    depth = 100_000
    arrays = _arrays(depth)
    trees = bytes.fromhex("a10181") * (depth - 1) + bytes.fromhex("a10180")
    unknown = bytes.fromhex("a30100028009") + arrays
    host = bytes.fromhex("a101") + arrays
    tag = BAND_START + 1
    reference = {
        "raw": _raw_reference(lambda: cbor.loads(arrays)),
        "raw-maps": _raw_reference(lambda: cbor.loads(bytes.fromhex("a100") * (depth - 1) + b"\xa0")),
        "raw-capped": _raw_reference(lambda: cbor.loads(arrays, max_depth=depth)),
        "IntBox": _raw_reference(lambda: codec.decode(s, "IntBox", unknown)),
        "Tree64": _raw_reference(lambda: codec.decode(s, "Tree64", trees)),
        "Tree128": _raw_reference(lambda: codec.decode(s, "Tree128", trees)),
        "ext_set": _raw_reference(lambda: ext.ext_set(s, host, "IntBox", tag, {"n": 0, "by_id": {}})),
        "ext_get": _raw_reference(lambda: ext.ext_get(s, host, "IntBox", tag)),
        "ext_clear": _raw_reference(lambda: ext.ext_clear(host, tag)),
    }
    assert reference == {"raw": "TooDeep;limit=32", "raw-maps": "TooDeep;limit=32",
                         "raw-capped": "TooDeep;limit=128", "IntBox": "TooDeep;limit=32",
                         "Tree64": "TooDeep;limit=64", "Tree128": "TooDeep;limit=128",
                         "ext_set": "TooDeep;limit=128", "ext_get": "TooDeep;limit=128",
                         "ext_clear": "TooDeep;limit=128"}
    observed = _observe(tmp_path, s, rf"""
#include "taut/ext.hpp"

template <class R>
std::string refusal(const R& r) {{
    if (r) {{
        return "ok";
    }}
    if (r.error.tag == taut::DecodeErrorTag::TooDeep) {{
        return "TooDeep;limit=" + std::to_string(r.error.limit);
    }}
    return describe(r.error);
}}

std::string repeat(std::string_view unit, std::size_t count, std::string_view last) {{
    std::string out;
    for (std::size_t i = 0; i < count; ++i) {{
        out += unit;
    }}
    out += last;
    return out;
}}

int main() {{
    const std::size_t depth = {depth};
    const std::string arrays = repeat("\x81", depth - 1, "\x80");
    const std::string maps = repeat(std::string_view("\xa1\x00", 2), depth - 1, "\xa0");
    const std::string trees = repeat("\xa1\x01\x81", depth - 1, "\xa1\x01\x80");
    const std::string unknown = std::string("\xa3\x01\x00\x02\x80\x09", 6) + arrays;
    const std::string host = "\xa1\x01" + arrays;
    const auto value = taut::try_decode(std::string_view("\xa1\x01\x82\x00\x80", 5));
    std::cout << "raw\t" << refusal(taut::try_decode(arrays)) << "\n";
    std::cout << "raw-maps\t" << refusal(taut::try_decode(maps)) << "\n";
    std::cout << "raw-capped\t" << refusal(taut::try_decode(arrays, depth)) << "\n";
    std::cout << "IntBox\t" << refusal(taut::IntBox::try_decode(unknown)) << "\n";
    std::cout << "Tree64\t" << refusal(taut::Tree64::try_decode(trees)) << "\n";
    std::cout << "Tree128\t" << refusal(taut::Tree128::try_decode(trees)) << "\n";
    std::cout << "ext_set\t" << refusal(taut::ext_set(host, {tag}, value.value)) << "\n";
    std::cout << "ext_get\t" << refusal(taut::ext_get(host, {tag})) << "\n";
    std::cout << "ext_clear\t" << refusal(taut::ext_clear(host, {tag})) << "\n";
    return 0;
}}
""")
    assert observed == reference


# Decode observations over one generated schema: `name<TAB>value` per line.
_OBSERVE = r"""
#include "api.hpp"

#include <iostream>
#include <list>
#include <string>
#include <string_view>

namespace {

// The input bytes outlive every decoded value, whose text views them.
std::string_view bytes_of(std::string_view hex) {
    static std::list<std::string> kept;
    std::string out;
    for (std::size_t i = 0; i + 1 < hex.size(); i += 2) {
        out.push_back(static_cast<char>(std::stoi(std::string(hex.substr(i, 2)), nullptr, 16)));
    }
    kept.push_back(std::move(out));
    return kept.back();
}

std::string hexof(const taut::Buf& b) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string out;
    for (std::size_t i = 0; i < b.n; ++i) {
        out.push_back(digits[b.d[i] >> 4]);
        out.push_back(digits[b.d[i] & 0x0f]);
    }
    return out;
}

std::string describe(const taut::DecodeError& e) {
    using T = taut::DecodeErrorTag;
    switch (e.tag) {
        case T::WrongType:
            return std::string("WrongType;expected=") + e.expected;
        case T::MissingKey:
            return "MissingKey;key=" + std::to_string(e.key);
        case T::DuplicateMapKey:
            return "DuplicateMapKey;key=" + (e.key_is_text ? std::string(e.key_text) : std::to_string(e.key));
        case T::TooDeep:
            return "TooDeep;limit=" + std::to_string(e.limit);
        case T::TooLarge:
            return "TooLarge;len=" + std::to_string(e.len) + ";limit=" + std::to_string(e.limit);
        default:
            return "tag#" + std::to_string(static_cast<int>(e.tag));
    }
}

// The typed decode from bytes, which applies M's bounds (TautCheckedDecode.md CD-B3).
template <class M>
taut::DecodeResult<M> decode(std::string_view hex) {
    return M::try_decode(bytes_of(hex));
}

template <class M>
std::string outcome_of(std::string_view hex) {
    auto r = decode<M>(hex);
    if (!r) {
        return "err " + describe(r.error);
    }
    return "ok";
}

// The checked decode, then the value's own encode.
template <class M>
std::string checked(std::string_view hex) {
    auto r = decode<M>(hex);
    if (!r) {
        return "err " + describe(r.error);
    }
    taut::Buf b;
    r.value.to_cbor(b);
    return "ok " + hexof(b);
}

}  // namespace
"""


def _observe(tmp_path: Path, s, main: str, *, forward_compat: bool = False) -> dict[str, str]:
    scaffold.emit(s, tmp_path, langs=["cpp"], services=[], runtime=True, forward_compat=forward_compat)
    run = _compile_and_run_cpp(tmp_path, _OBSERVE + main, "observe")
    return dict(line.split("\t", 1) for line in run.stdout.splitlines())


# Fields named like every name a message's C++ code uses: the runtime's types and helper, the
# schema's enum and messages (the struct itself among them, and a field named like its own
# message), the enum's `try_` function, the two namespaces, and the parameters and locals the
# generator once declared. None may clash with the generated code (`gen/cpp.py`, Names).
_FORMER_LOCALS = ("b", "c", "v", "x", "k", "e", "f", "kv")
S_HYGIENE = mk(Enum("Mode", ok=0, alt=1),
               Msg("Inner", F("Inner", 1, INT)),
               Msg("Holder",
                   F("Mode", 1, Ref("Mode")),
                   F("Inner", 2, Ref("Inner")),
                   F("Holder", 3, INT),
                   F("Cbor", 4, List(Ref("Inner"))),
                   F("Buf", 5, Map(STR, Ref("Mode"))),
                   F("DecodeResult", 6, Ref("Inner"), optional=True),
                   F("DecodeError", 7, Map(BOOL, INT)),
                   F("encode_value", 8, INT),
                   F("try_Mode_from_wire", 9, INT),
                   F("std", 10, List(List(INT))),
                   F("taut", 11, STR, optional=MISSING_OK),
                   *(F(name, tag, INT) for tag, name in enumerate(_FORMER_LOCALS, start=12))))

HYGIENE_VALUE = {"Mode": "alt", "Inner": {"Inner": 7}, "Holder": 3,
                 "Cbor": [{"Inner": 1}, {"Inner": -2}], "Buf": {"b": "ok", "a": "alt"},
                 "DecodeResult": {"Inner": 9}, "DecodeError": {True: 1, False: 0},
                 "encode_value": 8, "try_Mode_from_wire": 9, "std": [[1, 2], []], "taut": "t",
                 **{name: tag for tag, name in enumerate(_FORMER_LOCALS, start=12)}}


def test_cpp_compiles_fields_named_like_anything_its_code_uses(tmp_path):
    """Generated code names its own parameters and locals with `__` and qualifies every other
    name `::taut::`, so a field named like any of them compiles, plain and forward-compat, and
    round-trips. (Keywords, and the member functions' own names, stay out of reach.) Other
    targets cannot take some of these names, so validate refuses them for those, but none for
    cpp (test_reserved_names.py)."""
    assert [e for e in validate(S_HYGIENE) if re.search(r"\bcpp\b", e)] == []
    golden = codec.encode(S_HYGIENE, "Holder", HYGIENE_VALUE).hex()
    unknown = cbor.dumps({**cbor.loads(bytes.fromhex(golden)), 99: [1, "u"]}).hex()
    main = f"""
int main() {{
    auto built = {cpp_gen._render_struct(S_HYGIENE, "Holder", HYGIENE_VALUE)};
    taut::Buf out;
    built.to_cbor(out);
    std::cout << "built\\t" << hexof(out) << "\\n";
    std::cout << "checked\\t" << checked<taut::Holder>("{golden}") << "\\n";
    std::cout << "unknown-field\\t" << checked<taut::Holder>("{unknown}") << "\\n";
    return 0;
}}
"""
    for forward_compat in (False, True):
        observed = _observe(tmp_path / ("fc" if forward_compat else "plain"), S_HYGIENE, main,
                            forward_compat=forward_compat)
        kept = unknown if forward_compat else golden  # generated without forward-compat, it drops it
        assert observed == {"built": golden, "checked": f"ok {golden}", "unknown-field": f"ok {kept}"}


S_LITERAL = mk(Msg("Keyed", F("m", 1, Map(INT, INT))),
               Msg("Outer", F("inner", 1, Ref("Keyed"))),  # no map of its own
               Msg("Plain", F("n", 1, INT)))


def test_cpp_is_constexpr_only_where_the_struct_is_a_literal_type(tmp_path):
    """libc++'s std::map is not a literal type, so neither is a message that holds one, even
    through another message, and a constexpr function returning it does not compile."""
    hpp = cpp_gen._emit_types(S_LITERAL)
    assert "static constexpr ::taut::DecodeResult<::taut::Plain> try_from_cbor(" in hpp
    assert "static ::taut::DecodeResult<::taut::Keyed> try_from_cbor(" in hpp
    assert "static ::taut::DecodeResult<::taut::Outer> try_from_cbor(" in hpp
    golden = codec.encode(S_LITERAL, "Outer", {"inner": {"m": {2: 3}}}).hex()
    observed = _observe(tmp_path, S_LITERAL, f"""
int main() {{
    std::cout << "outer\\t" << checked<taut::Outer>("{golden}") << "\\n";
    return 0;
}}
""")
    assert observed == {"outer": f"ok {golden}"}


S_MISSING_OK = mk(Msg("Late", F("note", 1, STR, optional=MISSING_OK)),
                  Msg("Opt", F("note", 1, STR, optional=True)))


def test_cpp_missing_ok_reads_an_absent_key_as_null_and_still_refuses_wrong_types(tmp_path):
    observed = _observe(tmp_path, S_MISSING_OK, r"""
template <class M>
std::string note_of(std::string_view hex) {
    auto r = decode<M>(hex);
    if (!r) {
        return "err " + describe(r.error);
    }
    return r.value.note.has_value() ? "text " + std::string(*r.value.note) : "null";
}

// The checked decode runs at compile time too, and reads an absent MISSING_OK key as null.
constexpr auto late_absent = taut::Late::try_from_cbor(taut::try_decode(std::string_view("\xa0", 1)).value);
static_assert(late_absent.ok && !late_absent.value.note.has_value());
constexpr auto late_text = taut::Late::try_from_cbor(taut::try_decode(std::string_view("\xa1\x01\x61x", 4)).value);
static_assert(late_text.ok && *late_text.value.note == "x");
static_assert(!taut::Late::try_from_cbor(taut::try_decode(std::string_view("\xa1\x01\x01", 3)).value).ok);

int main() {
    std::cout << "late-absent\t" << note_of<taut::Late>("a0") << "\n";
    std::cout << "late-null\t" << note_of<taut::Late>("a101f6") << "\n";
    std::cout << "late-text\t" << note_of<taut::Late>("a1016178") << "\n";
    std::cout << "late-wrong-type\t" << note_of<taut::Late>("a10101") << "\n";
    std::cout << "late-not-a-map\t" << note_of<taut::Late>("00") << "\n";
    std::cout << "opt-absent\t" << note_of<taut::Opt>("a0") << "\n";
    std::cout << "opt-null\t" << note_of<taut::Opt>("a101f6") << "\n";
    taut::Buf unset;
    taut::Late{}.to_cbor(unset);
    std::cout << "late-unset-encodes\t" << hexof(unset) << "\n";
    return 0;
}
""")
    assert observed == {
        "late-absent": "null",
        "late-null": "null",
        "late-text": "text x",
        "late-wrong-type": "err WrongType;expected=text",
        "late-not-a-map": "err WrongType;expected=map",
        "opt-absent": "err MissingKey;key=1",
        "opt-null": "null",
        "late-unset-encodes": "a101f6",
    }


S_MAP_KEYS = mk(Msg("ByInt", F("m", 1, Map(INT, INT))),
                Msg("ByText", F("m", 1, Map(STR, INT))),
                Msg("ByBool", F("m", 1, Map(BOOL, INT))))


def test_cpp_map_field_refuses_a_repeated_entry_key_of_each_key_kind(tmp_path):
    observed = _observe(tmp_path, S_MAP_KEYS, r"""
int main() {
    std::cout << "int\t" << outcome_of<taut::ByInt>("a10182a201050201a201050202") << "\n";
    std::cout << "text\t" << outcome_of<taut::ByText>("a10182a201616b0201a201616b0202") << "\n";
    std::cout << "bool\t" << outcome_of<taut::ByBool>("a10182a201f50201a201f50202") << "\n";
    std::cout << "bool-false\t" << outcome_of<taut::ByBool>("a10182a201f40201a201f40202") << "\n";
    std::cout << "before-its-value\t" << outcome_of<taut::ByText>("a10182a201616b0201a201616b02f6") << "\n";
    std::cout << "distinct\t" << outcome_of<taut::ByText>("a10182a201616a0201a201616b0202") << "\n";
    return 0;
}
""")
    # The key as text (question 9): an int in decimal, a str as itself, a bool as true or false.
    assert observed == {
        "int": "err DuplicateMapKey;key=5",
        "text": "err DuplicateMapKey;key=k",
        "bool": "err DuplicateMapKey;key=true",
        "bool-false": "err DuplicateMapKey;key=false",
        "before-its-value": "err DuplicateMapKey;key=k",
        "distinct": "ok",
    }


# Legal shapes, nested (`ir/validate.py`): lists nest and may hold maps, a map's key is int,
# str or bool and its value a scalar, enum or message, and any field may be optional.
S_NESTED = mk(Enum("Mode", ok=0, alt=1),
              Msg("Box", F("mode", 1, Ref("Mode"))),
              Msg("Deep",  # no map, so its to_cbor and from_cbor are constexpr
                  F("cube", 1, List(List(List(INT)))),
                  F("rows", 2, List(List(Ref("Box")))),
                  F("maybe_grid", 3, List(List(STR)), optional=True),
                  F("maybe_modes", 4, List(Ref("Mode")), optional=MISSING_OK)),
              Msg("Keyed",
                  F("pages", 1, List(Map(STR, INT))),
                  F("shelves", 2, List(List(Map(BOOL, Ref("Box"))))),
                  F("maybe_index", 3, Map(INT, Ref("Mode")), optional=True),
                  F("maybe_pages", 4, List(Map(INT, BYTES)), optional=MISSING_OK)))

NESTED_VALUES = {
    "deep-filled": ("Deep", {"cube": [[[1, -2], []], [], [[300]]],
                             "rows": [[{"mode": "alt"}], [], [{"mode": "ok"}, {"mode": "alt"}]],
                             "maybe_grid": [["a", "\u2603"], []], "maybe_modes": ["alt", "ok"]}),
    "deep-null": ("Deep", {"cube": [], "rows": [], "maybe_grid": None, "maybe_modes": None}),
    "deep-engaged-empty": ("Deep", {"cube": [[]], "rows": [[]], "maybe_grid": [], "maybe_modes": []}),
    "keyed-filled": ("Keyed", {"pages": [{"b": 2, "a": 1}, {}],
                               "shelves": [[{True: {"mode": "alt"}, False: {"mode": "ok"}}], []],
                               "maybe_index": {3: "ok", -5: "alt"},
                               "maybe_pages": [{2: b"\x00", 1: b""}]}),
    "keyed-null": ("Keyed", {"pages": [], "shelves": [], "maybe_index": None, "maybe_pages": None}),
    "keyed-engaged-empty": ("Keyed", {"pages": [{}], "shelves": [[{}]], "maybe_index": {},
                                      "maybe_pages": []}),
}

_ABSENT = object()

# Inputs to the checked decode: name, message, wire fields over an empty value (_ABSENT drops one).
NESTED_INPUTS = [
    ("cube-leaf-not-an-int", "Deep", {1: [[["x"]]]}),
    ("row-box-not-a-map", "Deep", {2: [[5]]}),
    ("grid-row-null", "Deep", {3: [None]}),
    ("modes-absent", "Deep", {4: _ABSENT}),
    ("page-entry-not-a-map", "Keyed", {1: [[5]]}),
    ("page-entry-key-1-first", "Keyed", {1: [[{2: None}]]}),
    ("page-entry-without-value", "Keyed", {1: [[{1: "a"}]]}),
    ("page-repeated-key-before-its-value", "Keyed", {1: [[{1: "k", 2: 1}, {1: "k", 2: None}]]}),
    ("shelf-repeated-bool-key", "Keyed", {2: [[[{1: True, 2: {1: 0}}, {1: True, 2: {1: 1}}]]]}),
    ("index-value-null", "Keyed", {3: [{1: 3, 2: None}]}),
    ("pages-absent", "Keyed", {1: _ABSENT}),
]


def _nested_wire(fields: dict) -> bytes:
    wire = {1: [], 2: [], 3: None, 4: None}  # Deep and Keyed alike: two lists, two nulls
    wire.update(fields)
    return cbor.dumps({tag: v for tag, v in wire.items() if v is not _ABSENT})


def _reference_outcome(s, message: str, data: bytes) -> str:
    """What the reference (`wire/codec.py`) makes of `data`, as the C++ below reports it."""
    try:
        again = codec.encode(s, message, codec.decode(s, message, data))
    except cbor.DecodeError as exc:
        return f"err {exc.tag}" + "".join(f";{name}={v}" for name, v in exc.payload.items())
    return f"ok {again.hex()}"


@pytest.fixture(scope="module")
def nested_shapes(tmp_path_factory):
    """One C++ program over S_NESTED: (observed, expected), each expectation the reference's."""
    tmp_path = tmp_path_factory.mktemp("nested")
    deep = {name: ref for name, ref in NESTED_VALUES.items() if ref[0] == "Deep"}
    (tmp_path / "cpp").mkdir()
    (tmp_path / "cpp" / "types.hpp").write_text('#pragma once\n#include "api.hpp"\n')
    (tmp_path / "cpp" / "corpus.hpp").write_text(cpp_gen._emit_corpus(S_NESTED, deep))

    built, prints, expected = [], [], {}
    for name, (message, value) in NESTED_VALUES.items():
        golden = codec.encode(S_NESTED, message, value).hex()
        built.append(f"std::string built_{_ident(name)}() {{\n"
                     f"    auto v = {cpp_gen._render_struct(S_NESTED, message, value)};\n"
                     f"    taut::Buf b;\n    v.to_cbor(b);\n    return hexof(b);\n}}")
        prints.append(f'    std::cout << "{name} built\\t" << built_{_ident(name)}() << "\\n";')
        expected[f"{name} built"] = golden
        expected[f"{name} checked"] = f"ok {golden}"
        prints.append(f'    std::cout << "{name} checked\\t" << checked<taut::{message}>("{golden}") << "\\n";')
    for name, message, fields in NESTED_INPUTS:
        hexed = _nested_wire(fields).hex()
        expected[f"{name} checked"] = _reference_outcome(S_NESTED, message, bytes.fromhex(hexed))
        prints.append(f'    std::cout << "{name} checked\\t" << checked<taut::{message}>("{hexed}") << "\\n";')

    observed = _observe(tmp_path, S_NESTED, r"""
#include "corpus.hpp"

static_assert(taut::corpus::VECTOR_COUNT == 3);

""" + "\n\n".join(built) + "\n\nint main() {\n" + "\n".join(prints) + "\n    return 0;\n}\n")
    return observed, expected


# A repeated bool map key: question 9 rules its payload the key as text, `true`.
BOOL_KEY_CASE = "shelf-repeated-bool-key checked"


def test_cpp_generates_every_legal_shape_at_any_nesting(nested_shapes):
    """Each value is built natively and encodes to the reference's bytes, which decode back;
    each input decodes as the reference does. Deep has no map, so the constexpr corpus oracle
    proves its values at compile time too, through the checked decode."""
    assert validate(S_NESTED) == []
    assert "#include <map>" in cpp_gen._emit_types(mk(Msg("M", F("pages", 1, List(Map(STR, INT))))))
    observed, expected = nested_shapes
    # The inputs reach every tag `describe` above reports with its payload, and no other.
    assert {outcome.split(";")[0] for outcome in expected.values() if outcome.startswith("err ")} == {
        "err WrongType", "err MissingKey", "err DuplicateMapKey"}
    assert expected[BOOL_KEY_CASE] == "err DuplicateMapKey;key=true"
    assert observed == expected


def test_cpp_reports_a_repeated_bool_map_key_as_text(nested_shapes):
    observed, expected = nested_shapes
    assert observed[BOOL_KEY_CASE] == expected[BOOL_KEY_CASE]


def test_cpp_generated_scalar_list_float_static_asserts_cxx20(tmp_path):
    compiler = _cpp_compiler()

    runtime_src = Path(cpp_gen.__file__).resolve().parent / "runtime" / "cbor.hpp"
    include_dir = tmp_path / "taut"
    include_dir.mkdir()
    (include_dir / "cbor.hpp").write_text(runtime_src.read_text())

    refs = {
        "scalar-list-floats": (
            "M",
            {"x": -0.0, "xs": [0.0, -0.0, 0.1, 100000.0, float("inf")]},
        )
    }
    (tmp_path / "types.hpp").write_text(cpp_gen._emit_types(S_SCALAR_LIST))
    (tmp_path / "corpus.hpp").write_text(cpp_gen._emit_corpus(S_SCALAR_LIST, refs))
    source = tmp_path / "generated_scalar_list_float.cpp"
    source.write_text(textwrap.dedent("""\
        #include "corpus.hpp"

        int main() { return taut::corpus::VECTOR_COUNT == 1 ? 0 : 1; }
    """))

    exe = tmp_path / "generated_scalar_list_float"
    result = subprocess.run(
        [compiler, "-std=c++20", "-I", str(tmp_path), str(source), "-o", str(exe)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, textwrap.dedent(f"""\
        command: {compiler} -std=c++20 -I {tmp_path} {source} -o {exe}
        stdout:
        {result.stdout}
        stderr:
        {result.stderr}
    """)


def test_cpp_constexpr_corpus_proves_the_golden_corpus(tmp_path):
    """The constexpr oracle over the golden corpus, as `corpus/build.py` writes it: at compile
    time each vector's native value encodes to its golden bytes, and those bytes decode back
    through its message's typed decode from bytes, under its bounds, and re-encode to
    themselves."""
    compiler = _cpp_compiler()
    schema = load_schema(build.IR_PATH)
    refs = build.reference_values()
    golden = json.loads(build.GOLDEN_PATH.read_text())
    corpus = cpp_gen._emit_corpus(schema, refs)
    assert sorted(re.findall(r'eq_hex\(encode_\w+\(\), "([0-9a-f]+)"\)', corpus)) == \
        sorted(golden[name]["cbor"] for name in refs)
    assert sorted(re.findall(r"taut::(\w+)::try_decode\(", corpus)) == sorted(message for message, _ in refs.values())
    (tmp_path / "taut").mkdir()
    (tmp_path / "taut" / "cbor.hpp").write_text((RUNTIME / "cbor.hpp").read_text())
    (tmp_path / "types.hpp").write_text(cpp_gen._emit_types(schema))
    (tmp_path / "corpus.hpp").write_text(corpus)
    source = tmp_path / "golden_corpus.cpp"
    source.write_text('#include "corpus.hpp"\n\n'
                      f"int main() {{ return taut::corpus::VECTOR_COUNT == {len(refs)} ? 0 : 1; }}\n")
    exe = tmp_path / "golden_corpus"
    result = subprocess.run([compiler, "-std=c++20", "-I", str(tmp_path), str(source), "-o", str(exe)],
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert subprocess.run([str(exe)]).returncode == 0


def test_cpp_has_no_decode_entry_point_that_is_not_fail_closed():
    """Question 5 (ruled): every public decode entry point returns a value or a DecodeError
    through DecodeResult. The unchecked `parse` (it read past the end of its input and threw
    std::out_of_range), its helpers, the lenient accessors, the generated `from_cbor` and
    ext.hpp's throwing host decoder, which reserved memory from untrusted counts, are gone."""
    runtime = (RUNTIME / "cbor.hpp").read_text()
    extensions = (RUNTIME / "ext.hpp").read_text()
    unchecked = (r"\b(parse|decode_at|read_arg|byte_at|get|as_int|as_bool|as_float|as_text|as_bytes"
                 r"|as_array|checked_parse_map|ext_decode_at|ext_read_arg|ext_require)\(")
    assert re.findall(unchecked, runtime + extensions) == []
    assert "reserve(" not in extensions
    schema = parity.parity_schema()
    for forward_compat in (False, True):
        hpp = cpp_gen._emit_types(schema, forward_compat)
        assert re.findall(r"\bfrom_cbor\(", hpp) == []
        assert hpp.count("try_from_cbor(const ::taut::Cbor& __c)") == len(schema.messages)


def test_cpp_runtime_float_vectors_static_assert(tmp_path):
    compiler = _cpp_compiler()

    root = Path(__file__).resolve().parents[2]
    runtime_dir = Path(cpp_gen.__file__).resolve().parent / "runtime"
    rows = json.loads((root / "corpus" / "float_vectors.json").read_text())

    parts = [
        '#include "cbor.hpp"',
        "#include <string_view>",
        "",
        "namespace {",
        "",
    ]
    for row in rows:
        name = _ident(row["note"])
        bits = row["f64"]
        cbor = row["cbor"]
        lit = _cpp_bytes(bytes.fromhex(cbor))
        parts.append(f"consteval taut::Buf encode_{name}() {{")
        parts.append("    taut::Buf b;")
        parts.append(f"    b.float_(taut::f64_from_bits(0x{bits}ULL));")
        parts.append("    return b;")
        parts.append("}")
        parts.append(f'static_assert(taut::eq_hex(encode_{name}(), "{cbor}"), "{name} encode");')
        parts.append("")
        parts.append(f"consteval taut::Buf reemit_{name}() {{")
        parts.append(f"    auto c = taut::try_decode({lit});")
        parts.append("    taut::Buf b;")
        parts.append("    if (c) {")
        parts.append("        taut::encode_value(b, c.value);")
        parts.append("    }")
        parts.append("    return b;")
        parts.append("}")
        parts.append(f"static_assert(taut::eq(reemit_{name}(), {lit}), \"{name} reemit\");")
        if not row["note"].startswith("nan"):
            parts.append("")
            parts.append(f"consteval bool decode_bits_{name}() {{")
            parts.append(f"    auto c = taut::try_decode({lit});")
            parts.append("    auto f = c.value.try_float();")
            parts.append(f"    return c && f && taut::f64_bits(f.value) == 0x{bits}ULL;")
            parts.append("}")
            parts.append(f'static_assert(decode_bits_{name}(), "{name} decode bits");')
        parts.append("")
    parts.append("}")
    parts.append("")
    parts.append("int main() { return 0; }")
    source = tmp_path / "cpp_float_static_assert.cpp"
    source.write_text("\n".join(parts))

    exe = tmp_path / "cpp_float_static_assert"
    result = subprocess.run(
        [compiler, "-std=c++20", "-I", str(runtime_dir), str(source), "-o", str(exe)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, textwrap.dedent(f"""\
        command: {compiler} -std=c++20 -I {runtime_dir} {source} -o {exe}
        stdout:
        {result.stdout}
        stderr:
        {result.stderr}
    """)


# Host bytes the extension helpers refuse, and the deepest host they read, each with the tag the
# three are called with. The reference (`taut/ext.py`) decides each outcome: a tag below the band
# is the caller's error, raised before the host is read, and any fault in the host is a
# DecodeError.
_EXT_TAG = BAND_START + 1
EXT_NEGATIVES = [
    # note, host hex, tag
    ("below-band-before-host-decode", "ff", 7),
    ("scalar-host", "01", _EXT_TAG),
    ("array-host", "80", _EXT_TAG),
    ("empty-host", "", _EXT_TAG),
    ("truncated-host", "a101", _EXT_TAG),
    ("trailing-host", "a000", _EXT_TAG),
    ("text-map-key", "a1616b01", _EXT_TAG),
    # The strict runtime reads the host: the lax decoder took each of these four.
    ("negative-map-key", "a12001", _EXT_TAG),
    ("duplicate-map-key", "a201000101", _EXT_TAG),
    ("non-canonical-int", "a1011800", _EXT_TAG),
    ("invalid-utf8", "a10161ff", _EXT_TAG),
    ("unsupported-major", "c0a0", _EXT_TAG),
    ("unsupported-simple", "a101f7", _EXT_TAG),
    ("unsupported-additional-info", "a1011f", _EXT_TAG),
    # Counts no input could hold: nothing is reserved from them, and the first missing item is
    # Truncated (the lax decoder reserved them, and std::length_error escaped).
    ("map-count-u64-max", "bbffffffffffffffff", _EXT_TAG),
    ("array-count-u64-max", "a1019bffffffffffffffff", _EXT_TAG),
    # Not knowing the host's root, the helpers read it at the depth ceiling with no length bound
    # (TautOptions.md G3): a host 128 deep is read, one 129 deep is TooDeep{128}.
    ("host-at-the-depth-ceiling", "a101" + "81" * 126 + "80", _EXT_TAG),
    ("host-beyond-the-depth-ceiling", "a101" + "81" * 127 + "80", _EXT_TAG),
]
EXT_NEGATIVE_DECISION = {"backend": "b", "hops": 1}


def _ext_reference(s, op: str, host: bytes, tag: int) -> str:
    """What the reference makes of one call, as the C++ harness reports it."""
    try:
        if op == "set":
            ext.ext_set(s, host, "Decision", tag, EXT_NEGATIVE_DECISION)
        elif op == "get":
            ext.ext_get(s, host, "Decision", tag)
        else:
            ext.ext_clear(host, tag)
    except cbor.DecodeError as exc:
        return parity.format_error(exc.tag, exc.payload)
    except ValueError:  # after DecodeError, which is a ValueError too
        return "caller-error"
    return "ok"


def test_cpp_ext_negatives_are_the_references():
    """The table's outcomes, pinned: each host fault is the same DecodeError from all three."""
    s = _resext_schema()
    outcomes = {note: {_ext_reference(s, op, bytes.fromhex(host), tag) for op in ("set", "get", "clear")}
                for note, host, tag in EXT_NEGATIVES}
    assert outcomes == {
        "below-band-before-host-decode": {"caller-error"},
        "scalar-host": {"WrongType;expected=map"},
        "array-host": {"WrongType;expected=map"},
        "empty-host": {"Truncated"},
        "truncated-host": {"Truncated"},
        "trailing-host": {"TrailingBytes"},
        "text-map-key": {"NonIntegerMapKey"},
        "negative-map-key": {"NegativeMapKey;key=-1"},
        "duplicate-map-key": {"DuplicateMapKey;key=1"},
        "non-canonical-int": {"NonCanonicalInt;value=0"},
        "invalid-utf8": {"InvalidUtf8"},
        "unsupported-major": {"UnsupportedMajor;major=6"},
        "unsupported-simple": {"UnsupportedInfo;info=23"},
        "unsupported-additional-info": {"UnsupportedInfo;info=31"},
        "map-count-u64-max": {"Truncated"},
        "array-count-u64-max": {"Truncated"},
        "host-at-the-depth-ceiling": {"ok"},
        "host-beyond-the-depth-ceiling": {"TooDeep;limit=128"},
    }


def test_cpp_resext_runtime_corpus_negatives_and_fuzz(tmp_path):
    s, residual_rows, ext_rows = _resext_cpp_rows()
    assert cli.main([
        "gen", str(resext.IR_PATH), "-o", str(tmp_path), "--lang", "cpp",
        "--api-only", "--with-runtime", "--forward-compat",
    ]) == 0
    assert (tmp_path / "cpp/api.hpp").exists()
    assert (tmp_path / "cpp/taut/cbor.hpp").exists()
    assert (tmp_path / "cpp/taut/ext.hpp").exists()

    seed = 0xC0FFEE
    rng = random.Random(seed)
    fuzz_residual = []
    fuzz_ext = []
    tag = BAND_START + 1
    for i in range(1000):
        host_map = {
            1: rng.randint(0, 5000),
            2: f"n{i}",
            5: rng.randint(-20, 200),
            3: _fuzz_value(rng),                         # interleaves between 2 and 5
            BAND_START + 10 + rng.randrange(20): _fuzz_value(rng),
        }
        extra_tag = rng.choice([0, 4, 6, 7, 8, 64, BAND_START + 100 + rng.randrange(50)])
        if extra_tag not in {1, 2, 3, 5}:
            host_map[extra_tag] = _fuzz_value(rng)
        fuzz_residual.append({"note": f"residual-fuzz-{i}", "wire": cbor.dumps(host_map).hex()})

        ext_host_map = {1: rng.randint(0, 5000), 2: f"h{i}", 5: rng.randint(-20, 200)}
        ext_host = cbor.dumps(ext_host_map)
        if i % 5 == 0:
            ext_host = ext.ext_set(s, ext_host, "Decision", tag, {"backend": "old", "hops": -1})
        value = {"backend": f"b{i}", "hops": rng.randint(-10, 30)}
        value_wire = codec.encode(s, "Decision", value)
        set_expect = ext.ext_set(s, ext_host, "Decision", tag, value)
        clear_expect = ext.ext_clear(set_expect, tag)
        fuzz_ext.append({
            "note": f"ext-fuzz-{i}",
            "host": ext_host.hex(),
            "tag": tag,
            "value": value_wire.hex(),
            "set_expect": set_expect.hex(),
            "clear_expect": clear_expect.hex(),
        })

    large_host = cbor.dumps({1: 1, 2: "x" * 700, 5: 9})
    large_value = {"backend": "large", "hops": 1}
    large_value_wire = codec.encode(s, "Decision", large_value)
    large_set = ext.ext_set(s, large_host, "Decision", tag, large_value)
    assert len(large_set) > 512
    fuzz_ext.append({
        "note": "large-host-output-over-512",
        "host": large_host.hex(),
        "tag": tag,
        "value": large_value_wire.hex(),
        "set_expect": large_set.hex(),
        "clear_expect": ext.ext_clear(large_set, tag).hex(),
    })

    residual_init = _cpp_rows(residual_rows + fuzz_residual, ["note", "wire"])
    ext_init = ",\n".join(
        "{"
        + ", ".join([
            _cpp_string_literal(row["op"]),
            _cpp_string_literal(row["note"]),
            _cpp_string_literal(row["host"]),
            str(row["tag"]),
            _cpp_string_literal(row.get("value", "")),
            _cpp_string_literal(row["expect"]),
        ])
        + "}"
        for row in ext_rows
    )
    fuzz_ext_init = ",\n".join(
        "{"
        + ", ".join([
            _cpp_string_literal(row["note"]),
            _cpp_string_literal(row["host"]),
            str(row["tag"]),
            _cpp_string_literal(row["value"]),
            _cpp_string_literal(row["set_expect"]),
            _cpp_string_literal(row["clear_expect"]),
        ])
        + "}"
        for row in fuzz_ext
    )

    negative_value = codec.encode(s, "Decision", EXT_NEGATIVE_DECISION).hex()
    negatives_init = ",\n".join(
        "{" + ", ".join([_cpp_string_literal(note), _cpp_string_literal(host), str(tag),
                         *(_cpp_string_literal(_ext_reference(s, op, bytes.fromhex(host), tag))
                           for op in ("set", "get", "clear"))]) + "}"
        for note, host, tag in EXT_NEGATIVES
    )

    source = textwrap.dedent(f"""\
        #include "api.hpp"
        #include "taut/ext.hpp"

        #include <exception>
        #include <iostream>
        #include <optional>
        #include <stdexcept>
        #include <string>
        #include <string_view>
        #include <utility>
        #include <vector>

        struct ResidualRow {{ const char* note; const char* wire; }};
        struct ExtRow {{ const char* op; const char* note; const char* host; long long tag; const char* value; const char* expect; }};
        struct ExtFuzzRow {{ const char* note; const char* host; long long tag; const char* value; const char* set_expect; const char* clear_expect; }};
        struct ExtNegative {{ const char* note; const char* host; long long tag; const char* set; const char* get; const char* clear; }};

        static const ResidualRow residual_rows[] = {{
        {residual_init}
        }};

        static const ExtRow ext_rows[] = {{
        {ext_init}
        }};

        static const ExtFuzzRow ext_fuzz_rows[] = {{
        {fuzz_ext_init}
        }};

        static const ExtNegative ext_negatives[] = {{
        {negatives_init}
        }};

        int hex_nibble(char c) {{
            if (c >= '0' && c <= '9') {{
                return c - '0';
            }}
            if (c >= 'a' && c <= 'f') {{
                return c - 'a' + 10;
            }}
            if (c >= 'A' && c <= 'F') {{
                return c - 'A' + 10;
            }}
            throw std::invalid_argument("bad hex");
        }}

        std::string from_hex(std::string_view hex) {{
            if ((hex.size() % 2) != 0) {{
                throw std::invalid_argument("odd hex");
            }}
            std::string out;
            out.reserve(hex.size() / 2);
            for (std::size_t i = 0; i < hex.size(); i += 2) {{
                out.push_back(static_cast<char>((hex_nibble(hex[i]) << 4) | hex_nibble(hex[i + 1])));
            }}
            return out;
        }}

        std::string_view view(const std::string& s) {{
            return std::string_view(s.data(), s.size());
        }}

        std::string to_hex(std::string_view data) {{
            static constexpr char digits[] = "0123456789abcdef";
            std::string out;
            out.reserve(data.size() * 2);
            for (unsigned char byte : data) {{
                out.push_back(digits[byte >> 4]);
                out.push_back(digits[byte & 0x0f]);
            }}
            return out;
        }}

        std::string to_hex(const std::vector<unsigned char>& data) {{
            return to_hex(std::string_view(reinterpret_cast<const char*>(data.data()), data.size()));
        }}

        std::string buf_string(const taut::Buf& b) {{
            return std::string(reinterpret_cast<const char*>(b.d), b.n);
        }}

        std::string buf_hex(const taut::Buf& b) {{
            return to_hex(std::string_view(reinterpret_cast<const char*>(b.d), b.n));
        }}

        // A DecodeError as the reference's `Tag;field=value` (parity.format_error).
        std::string describe(const taut::DecodeError& e) {{
            using T = taut::DecodeErrorTag;
            switch (e.tag) {{
                case T::Truncated:
                    return "Truncated";
                case T::TrailingBytes:
                    return "TrailingBytes";
                case T::InvalidUtf8:
                    return "InvalidUtf8";
                case T::UnsupportedInfo:
                    return "UnsupportedInfo;info=" + std::to_string(e.info);
                case T::UnsupportedMajor:
                    return "UnsupportedMajor;major=" + std::to_string(e.major);
                case T::NonIntegerMapKey:
                    return "NonIntegerMapKey";
                case T::NegativeMapKey:
                    return "NegativeMapKey;key=" + std::to_string(e.key);
                case T::DuplicateMapKey:
                    return "DuplicateMapKey;key=" + (e.key_is_text ? std::string(e.key_text) : std::to_string(e.key));
                case T::NonCanonicalInt:
                    return "NonCanonicalInt;value=" + std::to_string(e.unsigned_value);
                case T::WrongType:
                    return std::string("WrongType;expected=") + e.expected;
                case T::TooDeep:
                    return "TooDeep;limit=" + std::to_string(e.limit);
                default:
                    return "tag#" + std::to_string(static_cast<int>(e.tag));
            }}
        }}

        // A decode that must succeed: its value, else std::runtime_error naming the error.
        template <class T>
        T must(taut::DecodeResult<T> r, std::string_view what) {{
            if (!r) {{
                throw std::runtime_error(std::string(what) + ": " + describe(r.error));
            }}
            return std::move(r.value);
        }}

        std::string typed_decision_wire(std::string_view value_hex) {{
            std::string value_bytes = from_hex(value_hex);
            taut::Decision d = must(taut::Decision::try_from_cbor(must(taut::try_decode(view(value_bytes)), "value")),
                                    "Decision");
            taut::Buf b;
            d.to_cbor(b);
            return buf_string(b);
        }}

        int mismatches = 0;

        void fail(std::string_view note, std::string_view got, std::string_view expect) {{
            ++mismatches;
            std::cerr << "mismatch " << note << "\\n  got    " << got << "\\n  expect " << expect << "\\n";
        }}

        void run_residuals() {{
            for (const auto& row : residual_rows) {{
                try {{
                    std::string wire = from_hex(row.wire);
                    taut::Host host = must(taut::Host::try_from_cbor(must(taut::try_decode(view(wire)), row.note)), row.note);
                    taut::Buf b;
                    host.to_cbor(b);
                    std::string got = buf_hex(b);
                    if (got != row.wire) {{
                        fail(row.note, got, row.wire);
                    }}
                }} catch (const std::exception& e) {{
                    fail(row.note, e.what(), "no exception");
                }}
            }}
        }}

        void run_ext_corpus() {{
            for (const auto& row : ext_rows) {{
                try {{
                    std::string host = from_hex(row.host);
                    std::string op(row.op);
                    if (op == "set") {{
                        std::string typed_wire = typed_decision_wire(row.value);
                        taut::Cbor value = must(taut::try_decode(view(typed_wire)), row.note);
                        std::string got = to_hex(must(taut::ext_set(view(host), row.tag, value), row.note));
                        if (got != row.expect) {{
                            fail(row.note, got, row.expect);
                        }}
                    }} else if (op == "get") {{
                        std::optional<taut::Cbor> got = must(taut::ext_get(view(host), row.tag), row.note);
                        if (std::string_view(row.expect) == "null") {{
                            if (got.has_value()) {{
                                fail(row.note, "present", "null");
                            }}
                        }} else if (!got.has_value()) {{
                            fail(row.note, "null", row.expect);
                        }} else {{
                            taut::Decision d = must(taut::Decision::try_from_cbor(*got), row.note);
                            taut::Buf b;
                            d.to_cbor(b);
                            std::string got_hex = buf_hex(b);
                            if (got_hex != row.expect) {{
                                fail(row.note, got_hex, row.expect);
                            }}
                        }}
                    }} else if (op == "clear") {{
                        std::string got = to_hex(must(taut::ext_clear(view(host), row.tag), row.note));
                        if (got != row.expect) {{
                            fail(row.note, got, row.expect);
                        }}
                    }} else {{
                        fail(row.note, op, "known op");
                    }}
                }} catch (const std::exception& e) {{
                    fail(row.note, e.what(), "no exception");
                }}
            }}
        }}

        void run_ext_fuzz() {{
            for (const auto& row : ext_fuzz_rows) {{
                try {{
                    std::string host = from_hex(row.host);
                    std::string typed_wire = typed_decision_wire(row.value);
                    taut::Cbor value = must(taut::try_decode(view(typed_wire)), row.note);
                    std::string set_got = to_hex(must(taut::ext_set(view(host), row.tag, value), row.note));
                    if (set_got != row.set_expect) {{
                        fail(row.note, set_got, row.set_expect);
                    }}

                    std::string strapped = from_hex(row.set_expect);
                    std::optional<taut::Cbor> got = must(taut::ext_get(view(strapped), row.tag), row.note);
                    if (!got.has_value()) {{
                        fail(row.note, "null", row.value);
                    }} else {{
                        taut::Decision d = must(taut::Decision::try_from_cbor(*got), row.note);
                        taut::Buf b;
                        d.to_cbor(b);
                        std::string got_hex = buf_hex(b);
                        if (got_hex != row.value) {{
                            fail(row.note, got_hex, row.value);
                        }}
                    }}

                    std::string clear_got = to_hex(must(taut::ext_clear(view(strapped), row.tag), row.note));
                    if (clear_got != row.clear_expect) {{
                        fail(row.note, clear_got, row.clear_expect);
                    }}
                }} catch (const std::exception& e) {{
                    fail(row.note, e.what(), "no exception");
                }}
            }}
        }}

        // One call's outcome as the reference reports it: `ok`, the DecodeError, or
        // `caller-error` for std::invalid_argument. Anything else escapes to the caller.
        template <class Call>
        std::string outcome_of(Call call) {{
            try {{
                auto r = call();
                if (!r) {{
                    return describe(r.error);
                }}
                return "ok";
            }} catch (const std::invalid_argument&) {{
                return "caller-error";
            }}
        }}

        void run_negatives() {{
            std::string typed_wire = typed_decision_wire("{negative_value}");
            taut::Cbor value = must(taut::try_decode(view(typed_wire)), "negative value");
            for (const auto& row : ext_negatives) {{
                std::string host = from_hex(row.host);
                const std::pair<const char*, std::string_view> calls[] = {{
                    {{"set", row.set}}, {{"get", row.get}}, {{"clear", row.clear}}}};
                for (const auto& [op, expect] : calls) {{
                    std::string note = std::string(row.note) + " " + op;
                    try {{
                        std::string got;
                        if (std::string_view(op) == "set") {{
                            got = outcome_of([&] {{ return taut::ext_set(view(host), row.tag, value); }});
                        }} else if (std::string_view(op) == "get") {{
                            got = outcome_of([&] {{ return taut::ext_get(view(host), row.tag); }});
                        }} else {{
                            got = outcome_of([&] {{ return taut::ext_clear(view(host), row.tag); }});
                        }}
                        if (got != expect) {{
                            fail(note, got, expect);
                        }}
                    }} catch (const std::exception& e) {{
                        fail(note, std::string("escaped: ") + e.what(), expect);
                    }}
                }}
            }}
        }}

        int main() {{
            run_residuals();
            run_ext_corpus();
            run_ext_fuzz();
            run_negatives();
            if (mismatches != 0) {{
                std::cerr << "ResExt C++ seed={seed} mismatches=" << mismatches << "\\n";
                return 1;
            }}
            std::cout << "ResExt C++ seed={seed} mismatches=0\\n";
            return 0;
        }}
    """)

    run = _compile_and_run_cpp(tmp_path, source, "cpp_resext_runtime")
    assert f"seed={seed} mismatches=0" in run.stdout
