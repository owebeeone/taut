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
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.ir.dsl import BOOL, BYTES, FLOAT, INT, MISSING_OK, STR, Enum, F, List, Map, Msg, Ref, schema as mk
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
# CD-E5's order of checks and D2's strictness where the corpus has a single row.
BEYOND_THE_CORPUS = [
    # name, stage, schema, hex, expected
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
]


def test_cpp_decode_matches_python_beyond_the_corpus(monkeypatch):
    """The gate's C++ runner, with the rows above appended to the corpus, stays green."""
    schema = parity.parity_schema()
    extra = []
    for name, stage, message, hexed, expected in BEYOND_THE_CORPUS:
        row = {"name": f"beyond-{name}", "stage": stage, "schema": message, "bytes": hexed,
               "why": "C++ decodes as Python does"}
        tag, payload = parity.parse_error(expected)
        if tag == "accept":
            row["expect"] = {"accept": True, **payload}  # `;reencode=` where it is not the input
        else:
            row["expect"] = {"tag": tag, **payload}
        extra.append(row)
    # The table is the reference's behaviour, not a guess.
    observed = [(row["name"], parity._observe_python(schema, row)) for row in extra]
    assert [(name, outcome) for name, (outcome, _) in observed if outcome == parity.UNTYPED] == []
    assert [parity.judge("python", row, *seen) for row, (_, seen) in zip(extra, observed)] == \
        [(parity.PASS, "")] * len(extra)

    listed = {s.target: s for s in parity.target_statuses() if s.status == "allowlisted"}
    if "cpp" in listed:  # the whole fixture must build and pass before the rows beyond it can
        pytest.skip(f"cpp is allowlisted in corpus/parity/allowlist.json (phase {listed['cpp'].phase}): "
                    f"{listed['cpp'].reason}")
    corpus = parity.malformed_rows()
    monkeypatch.setattr(parity, "malformed_rows", lambda: [*corpus, *extra])
    report = parity_cpp.run()
    if not report.available:
        pytest.skip(report.skip_reason)
    assert len(report.results) == len(parity.int_rows()) + len(corpus) + len(extra)
    failures = [f"{r.name}: {r.detail}" for r in report.failures]
    assert report.green, "\n".join([report.fault, *failures])


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
        default:
            return "tag#" + std::to_string(static_cast<int>(e.tag));
    }
}

template <class M>
taut::DecodeResult<M> decode(std::string_view hex) {
    auto raw = taut::try_decode(bytes_of(hex));
    if (!raw) {
        return taut::DecodeResult<M>::fail(raw.error);
    }
    return M::try_from_cbor(raw.value);
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
    round-trips. (Keywords, and the member functions' own names, stay out of reach.)"""
    assert validate(S_HYGIENE) == []
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
    through the fail-closed decode and re-encode to themselves."""
    compiler = _cpp_compiler()
    schema = load_schema(build.IR_PATH)
    refs = build.reference_values()
    golden = json.loads(build.GOLDEN_PATH.read_text())
    corpus = cpp_gen._emit_corpus(schema, refs)
    assert sorted(re.findall(r'eq_hex\(encode_\w+\(\), "([0-9a-f]+)"\)', corpus)) == \
        sorted(golden[name]["cbor"] for name in refs)
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


# Host bytes the extension helpers refuse, each with the tag the three are called with. The
# reference (`taut/ext.py`) decides each outcome: a tag below the band is the caller's error,
# raised before the host is read, and any fault in the host is a DecodeError.
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
