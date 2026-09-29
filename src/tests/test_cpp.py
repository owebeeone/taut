import json
import random
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from taut import cli, ext
from taut.corpus import parity, parity_cpp
from taut.corpus import resext_build as resext
from taut.gen import cpp as cpp_gen
from taut.gen import scaffold
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.ir.dsl import BOOL, FLOAT, INT, MISSING_OK, STR, F, List, Map, Msg, schema as mk
from taut.wire import cbor, codec


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
    assert "b.float_(x);" in hpp
    assert "for (const auto& x : xs) { b.float_(x); }" in hpp
    assert ".as_float()" in hpp
    assert cpp_gen._render(S_SCALAR_LIST, FLOAT, -0.0) == "taut::f64_from_bits(0x8000000000000000ULL)"


def test_cpp_codegen_threads_float_map_string_shape_only():
    # Generated constexpr std::map iteration is not portable under C++20 libc++;
    # scalar/list float generated code is the compiled C++20 coverage below.
    hpp = cpp_gen._emit_types(S_MAP_SHAPE)
    assert "std::map<long long, double> by_id;" in hpp
    assert "for (const auto& [k, v] : by_id)" in hpp
    assert "b.float_(v);" in hpp
    assert "v.by_id[e.get(1).as_int()] = e.get(2).as_float();" in hpp


def test_cpp_codegen_emits_fallible_decode_path_for_i64_and_enums():
    root = Path(__file__).resolve().parents[2]
    schema = load_schema(root / "ir" / "parity_int.taut.py")
    hpp = cpp_gen._emit_types(schema)
    assert "inline constexpr DecodeResult<Mode> try_Mode_from_wire(long long v)" in hpp
    assert 'DecodeError::unknown_enum("Mode", v)' in hpp
    assert "static DecodeResult<IntBox> try_from_cbor(const Cbor& c)" in hpp
    assert "auto __decoded_1 = (*__field_1.value).try_int();" in hpp
    assert "auto __decoded_2_arr = (*__field_2.value).try_array();" in hpp
    assert "auto __decoded_2_k = (*__decoded_2_key_cbor.value).try_int();" in hpp
    assert "auto __decoded_2_v = (*__decoded_2_val_cbor.value).try_int();" in hpp


def test_cpp_passes_the_parity_gate():
    """Every row of the shared corpus through the gate's C++ runner (`tautc parity -t cpp`)."""
    report = parity_cpp.run()
    if not report.available:
        pytest.skip(report.skip_reason)
    failures = [f"{r.name}: {r.detail}" for r in report.failures]
    assert report.green, "\n".join([report.fault, *failures])
    # Only an encode-fail row may be satisfied by the type system; every other row ran.
    satisfied = {r.name for r in report.results if r.status == parity.TYPE_SATISFIED}
    assert satisfied == {r["name"] for r in parity.int_rows() if r["kind"] == "encode_fail"}


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
    ("float-width-is-not-checked", "raw_decode", "", "fb0000000000000000", "accept"),
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
    ("empty-message-ignores-unknown-fields", "from_cbor", "Empty", "a10100", "accept"),
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
        if expected == "accept":
            row["expect"] = {"accept": True}
        else:
            tag, payload = parity.parse_error(expected)
            row["expect"] = {"tag": tag, **payload}
        extra.append(row)
    # The table is the reference's behaviour, not a guess.
    observed = [(row["name"], parity._observe_python(schema, row)) for row in extra]
    assert [(name, outcome) for name, (outcome, _) in observed if outcome == parity.UNTYPED] == []
    assert [parity.judge("python", row, *seen) for row, (_, seen) in zip(extra, observed)] == \
        [(parity.PASS, "")] * len(extra)

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

}  // namespace
"""


def _observe(tmp_path: Path, s, main: str) -> dict[str, str]:
    scaffold.emit(s, tmp_path, langs=["cpp"], services=[], runtime=True)
    run = _compile_and_run_cpp(tmp_path, _OBSERVE + main, "observe")
    return dict(line.split("\t", 1) for line in run.stdout.splitlines())


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

// The unchecked constexpr path reads an absent MISSING_OK key as null too.
static_assert(!taut::Late::from_cbor(taut::parse(std::string_view("\xa0", 1))).note.has_value());
static_assert(*taut::Late::from_cbor(taut::parse(std::string_view("\xa1\x01\x61x", 4))).note == "x");

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
    std::cout << "before-its-value\t" << outcome_of<taut::ByText>("a10182a201616b0201a201616b02f6") << "\n";
    std::cout << "distinct\t" << outcome_of<taut::ByText>("a10182a201616a0201a201616b0202") << "\n";
    return 0;
}
""")
    assert observed == {
        "int": "err DuplicateMapKey;key=5",
        "text": "err DuplicateMapKey;key=k",
        "bool": "err DuplicateMapKey;key=1",
        "before-its-value": "err DuplicateMapKey;key=k",
        "distinct": "ok",
    }


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
        parts.append(f"    auto c = taut::parse({lit});")
        parts.append("    taut::Buf b;")
        parts.append("    taut::encode_value(b, c);")
        parts.append("    return b;")
        parts.append("}")
        parts.append(f"static_assert(taut::eq(reemit_{name}(), {lit}), \"{name} reemit\");")
        if not row["note"].startswith("nan"):
            parts.append("")
            parts.append(f"consteval bool decode_bits_{name}() {{")
            parts.append(f"    auto c = taut::parse({lit});")
            parts.append(f"    return c.k == taut::Cbor::K::Float && taut::f64_bits(c.as_float()) == 0x{bits}ULL;")
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

    source = textwrap.dedent(f"""\
        #include "api.hpp"
        #include "taut/ext.hpp"

        #include <exception>
        #include <functional>
        #include <iostream>
        #include <stdexcept>
        #include <string>
        #include <string_view>
        #include <vector>

        struct ResidualRow {{ const char* note; const char* wire; }};
        struct ExtRow {{ const char* op; const char* note; const char* host; long long tag; const char* value; const char* expect; }};
        struct ExtFuzzRow {{ const char* note; const char* host; long long tag; const char* value; const char* set_expect; const char* clear_expect; }};

        static const ResidualRow residual_rows[] = {{
        {residual_init}
        }};

        static const ExtRow ext_rows[] = {{
        {ext_init}
        }};

        static const ExtFuzzRow ext_fuzz_rows[] = {{
        {fuzz_ext_init}
        }};

        int hex_nibble(char c) {{
            if (c >= '0' && c <= '9') return c - '0';
            if (c >= 'a' && c <= 'f') return c - 'a' + 10;
            if (c >= 'A' && c <= 'F') return c - 'A' + 10;
            throw std::invalid_argument("bad hex");
        }}

        std::string from_hex(std::string_view hex) {{
            if ((hex.size() % 2) != 0) throw std::invalid_argument("odd hex");
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

        std::string typed_decision_wire(std::string_view value_hex) {{
            std::string value_bytes = from_hex(value_hex);
            taut::Decision d = taut::Decision::from_cbor(taut::checked_parse_map(view(value_bytes)));
            taut::Buf b;
            d.to_cbor(b);
            return buf_string(b);
        }}

        int mismatches = 0;

        void fail(std::string_view note, std::string_view got, std::string_view expect) {{
            ++mismatches;
            std::cerr << "mismatch " << note << "\\n  got    " << got << "\\n  expect " << expect << "\\n";
        }}

        void expect_invalid(std::string_view note, const std::function<void()>& fn, std::string_view contains = "") {{
            try {{
                fn();
                fail(note, "no throw", "std::invalid_argument");
            }} catch (const std::invalid_argument& e) {{
                if (!contains.empty() && std::string_view(e.what()).find(contains) == std::string_view::npos) {{
                    fail(note, e.what(), contains);
                }}
            }} catch (const std::exception& e) {{
                fail(note, e.what(), "std::invalid_argument");
            }}
        }}

        void run_residuals() {{
            for (const auto& row : residual_rows) {{
                try {{
                    std::string wire = from_hex(row.wire);
                    taut::Host host = taut::Host::from_cbor(taut::checked_parse_map(view(wire)));
                    taut::Buf b;
                    host.to_cbor(b);
                    std::string got = buf_hex(b);
                    if (got != row.wire) fail(row.note, got, row.wire);
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
                        taut::Cbor value = taut::checked_parse_map(view(typed_wire));
                        std::string got = to_hex(taut::ext_set(view(host), row.tag, value));
                        if (got != row.expect) fail(row.note, got, row.expect);
                    }} else if (op == "get") {{
                        auto got = taut::ext_get(view(host), row.tag);
                        if (std::string_view(row.expect) == "null") {{
                            if (got.has_value()) fail(row.note, "present", "null");
                        }} else {{
                            if (!got.has_value()) {{
                                fail(row.note, "null", row.expect);
                            }} else {{
                                taut::Decision d = taut::Decision::from_cbor(*got);
                                taut::Buf b;
                                d.to_cbor(b);
                                std::string got_hex = buf_hex(b);
                                if (got_hex != row.expect) fail(row.note, got_hex, row.expect);
                            }}
                        }}
                    }} else if (op == "clear") {{
                        std::string got = to_hex(taut::ext_clear(view(host), row.tag));
                        if (got != row.expect) fail(row.note, got, row.expect);
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
                    taut::Cbor value = taut::checked_parse_map(view(typed_wire));
                    std::string set_got = to_hex(taut::ext_set(view(host), row.tag, value));
                    if (set_got != row.set_expect) fail(row.note, set_got, row.set_expect);

                    std::string strapped = from_hex(row.set_expect);
                    auto got = taut::ext_get(view(strapped), row.tag);
                    if (!got.has_value()) {{
                        fail(row.note, "null", row.value);
                    }} else {{
                        taut::Decision d = taut::Decision::from_cbor(*got);
                        taut::Buf b;
                        d.to_cbor(b);
                        std::string got_hex = buf_hex(b);
                        if (got_hex != row.value) fail(row.note, got_hex, row.value);
                    }}

                    std::string clear_got = to_hex(taut::ext_clear(view(strapped), row.tag));
                    if (clear_got != row.clear_expect) fail(row.note, clear_got, row.clear_expect);
                }} catch (const std::exception& e) {{
                    fail(row.note, e.what(), "no exception");
                }}
            }}
        }}

        void run_negatives() {{
            expect_invalid("below-band-before-host-decode", [] {{
                (void)taut::ext_get(std::string_view("\\xff", 1), 7);
            }}, "below");
            expect_invalid("scalar-host", [] {{
                std::string host = from_hex("01");
                (void)taut::ext_get(view(host), {tag});
            }});
            expect_invalid("trailing-host", [] {{
                std::string host = from_hex("a000");
                (void)taut::ext_get(view(host), {tag});
            }});
            expect_invalid("invalid-map-key", [] {{
                std::string host = from_hex("a1616b01");
                (void)taut::ext_get(view(host), {tag});
            }});
            expect_invalid("unsupported-major", [] {{
                std::string host = from_hex("c0a0");
                (void)taut::ext_get(view(host), {tag});
            }});
            expect_invalid("unsupported-simple", [] {{
                std::string host = from_hex("a101f7");
                (void)taut::ext_get(view(host), {tag});
            }});
            expect_invalid("unsupported-additional-info", [] {{
                std::string host = from_hex("a1011f");
                (void)taut::ext_get(view(host), {tag});
            }});
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
