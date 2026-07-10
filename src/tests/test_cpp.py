import json
import random
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from taut import cli, ext
from taut.corpus import resext_build as resext
from taut.gen import cpp as cpp_gen
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk
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


def _cpp_int_literal(value: str) -> str:
    if value == "-9223372036854775808":
        return "std::numeric_limits<long long>::min()"
    if value == "9223372036854775807":
        return "std::numeric_limits<long long>::max()"
    return f"{value}LL"


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


def test_cpp_runtime_replays_shared_i64_parity_corpus(tmp_path):
    root = Path(__file__).resolve().parents[2]
    schema_path = root / "ir" / "parity_int.taut.py"
    # Baseline smoke test: pin the reviewed set; `lead` rows belong to the
    # governed `tautc parity` gate (corpus/parity/gen_vectors.py).
    int_vectors = [r for r in json.loads((root / "corpus" / "parity" / "int.vectors.json").read_text())["vectors"] if not r.get("lead")]
    malformed = [r for r in json.loads((root / "corpus" / "parity" / "malformed.vectors.json").read_text())["vectors"] if not r.get("lead")]

    assert cli.main([
        "gen", str(schema_path), "-o", str(tmp_path), "--lang", "cpp",
        "--api-only", "--with-runtime",
    ]) == 0

    round_rows = []
    encode_rows = []
    for row in int_vectors:
        value = row["value"]
        if row["kind"] == "round_trip":
            pairs = value["by_id"]
            by_id = "{}" if not pairs else "{" + ", ".join(
                "{" + _cpp_int_literal(k) + ", " + _cpp_int_literal(v) + "}" for k, v in pairs
            ) + "}"
            round_rows.append(
                "{"
                + ", ".join([
                    _cpp_string_literal(row["name"]),
                    _cpp_int_literal(value["n"]),
                    by_id,
                    _cpp_string_literal(row["cbor"]),
                ])
                + "}"
            )
        elif row["kind"] == "encode_fail":
            encode_rows.append(
                "{"
                + ", ".join([
                    _cpp_string_literal(row["name"]),
                    _cpp_string_literal(value["n"]),
                    _cpp_string_literal(row["expect"]["tag"]),
                ])
                + "}"
            )

    mal_rows = []
    for row in malformed:
        expect = row["expect"]
        mal_rows.append(
            "{"
            + ", ".join([
                _cpp_string_literal(row["name"]),
                _cpp_string_literal(row["stage"]),
                _cpp_string_literal(row.get("schema", "")),
                _cpp_string_literal(row["bytes"]),
                _cpp_string_literal(expect["tag"]),
                "true" if "key" in expect else "false",
                _cpp_int_literal(str(expect.get("key", "0"))),
                "true" if "info" in expect else "false",
                str(expect.get("info", 0)),
                "true" if "major" in expect else "false",
                str(expect.get("major", 0)),
                _cpp_string_literal(expect.get("expected", "")),
                _cpp_string_literal(expect.get("enum", "")),
                _cpp_string_literal(str(expect.get("value", ""))),
            ])
            + "}"
        )

    source = textwrap.dedent("""\
        #include "api.hpp"

        #include <cstdlib>
        #include <cstdint>
        #include <iostream>
        #include <limits>
        #include <map>
        #include <string>
        #include <string_view>

        struct RoundRow {
            const char* name;
            long long n;
            std::map<long long, long long> by_id;
            const char* cbor;
        };

        struct EncodeFailRow {
            const char* name;
            const char* n;
            const char* tag;
        };

        struct MalRow {
            const char* name;
            const char* stage;
            const char* schema;
            const char* bytes;
            const char* tag;
            bool has_key;
            long long key;
            bool has_info;
            unsigned info;
            bool has_major;
            unsigned major;
            const char* expected;
            const char* enum_name;
            const char* value;
        };

        static const RoundRow round_rows[] = {
        ROUND_ROWS
        };

        static const EncodeFailRow encode_fail_rows[] = {
        ENCODE_ROWS
        };

        static const MalRow malformed_rows[] = {
        MAL_ROWS
        };

        int hex_nibble(char c) {
            if (c >= '0' && c <= '9') return c - '0';
            if (c >= 'a' && c <= 'f') return c - 'a' + 10;
            if (c >= 'A' && c <= 'F') return c - 'A' + 10;
            std::abort();
        }

        std::string from_hex(std::string_view hex) {
            std::string out;
            out.reserve(hex.size() / 2);
            for (std::size_t i = 0; i < hex.size(); i += 2) {
                out.push_back(static_cast<char>((hex_nibble(hex[i]) << 4) | hex_nibble(hex[i + 1])));
            }
            return out;
        }

        std::string_view view(const std::string& s) {
            return std::string_view(s.data(), s.size());
        }

        std::string to_hex(std::string_view data) {
            static constexpr char digits[] = "0123456789abcdef";
            std::string out;
            out.reserve(data.size() * 2);
            for (unsigned char byte : data) {
                out.push_back(digits[byte >> 4]);
                out.push_back(digits[byte & 0x0f]);
            }
            return out;
        }

        std::string buf_hex(const taut::Buf& b) {
            return to_hex(std::string_view(reinterpret_cast<const char*>(b.d), b.n));
        }

        taut::DecodeErrorTag tag_from_name(std::string_view name) {
            using T = taut::DecodeErrorTag;
            if (name == "Truncated") return T::Truncated;
            if (name == "TrailingBytes") return T::TrailingBytes;
            if (name == "InvalidUtf8") return T::InvalidUtf8;
            if (name == "UnsupportedInfo") return T::UnsupportedInfo;
            if (name == "UnsupportedMajor") return T::UnsupportedMajor;
            if (name == "NonIntegerMapKey") return T::NonIntegerMapKey;
            if (name == "IntOverflow") return T::IntOverflow;
            if (name == "DuplicateMapKey") return T::DuplicateMapKey;
            if (name == "MissingKey") return T::MissingKey;
            if (name == "WrongType") return T::WrongType;
            if (name == "UnknownEnum") return T::UnknownEnum;
            std::abort();
        }

        const char* tag_name(taut::DecodeErrorTag tag) {
            using T = taut::DecodeErrorTag;
            switch (tag) {
                case T::Truncated: return "Truncated";
                case T::TrailingBytes: return "TrailingBytes";
                case T::InvalidUtf8: return "InvalidUtf8";
                case T::UnsupportedInfo: return "UnsupportedInfo";
                case T::UnsupportedMajor: return "UnsupportedMajor";
                case T::NonIntegerMapKey: return "NonIntegerMapKey";
                case T::IntOverflow: return "IntOverflow";
                case T::DuplicateMapKey: return "DuplicateMapKey";
                case T::MissingKey: return "MissingKey";
                case T::WrongType: return "WrongType";
                case T::UnknownEnum: return "UnknownEnum";
            }
            return "?";
        }

        bool overflow_payload_matches(const taut::DecodeError& error, std::string_view value) {
            if (value.empty()) return true;
            const std::uint64_t just_outside = 1ULL << 63;
            if (value == "9223372036854775808") {
                return !error.negative_overflow && error.unsigned_value == just_outside;
            }
            if (value == "-9223372036854775809") {
                return error.negative_overflow && error.unsigned_value == just_outside;
            }
            return false;
        }

        bool error_matches(const taut::DecodeError& error, const MalRow& row) {
            if (error.tag != tag_from_name(row.tag)) return false;
            using T = taut::DecodeErrorTag;
            switch (error.tag) {
                case T::UnsupportedInfo:
                    return !row.has_info || error.info == row.info;
                case T::UnsupportedMajor:
                    return !row.has_major || error.major == row.major;
                case T::DuplicateMapKey:
                case T::MissingKey:
                    return !row.has_key || error.key == row.key;
                case T::WrongType:
                    return std::string_view(row.expected).empty()
                        || std::string_view(error.expected ? error.expected : "") == row.expected;
                case T::UnknownEnum:
                    return (std::string_view(row.enum_name).empty()
                            || std::string_view(error.enum_name ? error.enum_name : "") == row.enum_name)
                        && (std::string_view(row.value).empty() || std::to_string(error.value) == row.value);
                case T::IntOverflow:
                    return overflow_payload_matches(error, row.value);
                default:
                    return true;
            }
        }

        bool outside_i64(std::string_view value) {
            return value == "9223372036854775808"
                || value == "-9223372036854775809"
                || value == "18446744073709551615";
        }

        int mismatches = 0;

        void fail(std::string_view note, std::string_view got, std::string_view expect) {
            ++mismatches;
            std::cerr << "mismatch " << note << "\\n  got    " << got << "\\n  expect " << expect << "\\n";
        }

        void expect_error(const MalRow& row, const taut::DecodeError& error) {
            if (!error_matches(error, row)) fail(row.name, tag_name(error.tag), row.tag);
        }

        void run_round_trip() {
            for (const auto& row : round_rows) {
                taut::IntBox box{row.n, row.by_id};
                taut::Buf b;
                box.to_cbor(b);
                std::string got = buf_hex(b);
                if (got != row.cbor) fail(row.name, got, row.cbor);

                std::string wire = from_hex(row.cbor);
                auto decoded = taut::try_decode(view(wire));
                if (!decoded) {
                    fail(row.name, tag_name(decoded.error.tag), "valid decode");
                    continue;
                }
                auto msg = taut::IntBox::try_from_cbor(decoded.value);
                if (!msg) {
                    fail(row.name, tag_name(msg.error.tag), "valid IntBox");
                    continue;
                }
                if (msg.value.n != row.n || msg.value.by_id != row.by_id) {
                    fail(row.name, "decoded value mismatch", "same native value");
                }
                taut::Buf round;
                msg.value.to_cbor(round);
                got = buf_hex(round);
                if (got != row.cbor) fail(row.name, got, row.cbor);
            }
        }

        void run_encode_fail() {
            for (const auto& row : encode_fail_rows) {
                if (std::string_view(row.tag) != "IntOutOfSubset") {
                    fail(row.name, row.tag, "IntOutOfSubset");
                }
                if (!outside_i64(row.n)) {
                    fail(row.name, row.n, "outside native long long");
                }
            }
        }

        void run_malformed() {
            for (const auto& row : malformed_rows) {
                std::string bytes = from_hex(row.bytes);
                if (std::string_view(row.stage) == "raw_decode") {
                    auto decoded = taut::try_decode(view(bytes));
                    if (decoded) fail(row.name, "decoded", row.tag);
                    else expect_error(row, decoded.error);
                } else if (std::string_view(row.stage) == "from_cbor") {
                    auto decoded = taut::try_decode(view(bytes));
                    if (!decoded) {
                        fail(row.name, tag_name(decoded.error.tag), "valid raw CBOR before from_cbor");
                    } else if (std::string_view(row.schema) == "IntBox") {
                        auto msg = taut::IntBox::try_from_cbor(decoded.value);
                        if (msg) fail(row.name, "decoded IntBox", row.tag);
                        else expect_error(row, msg.error);
                    } else {
                        fail(row.name, row.schema, "known from_cbor schema");
                    }
                } else if (std::string_view(row.stage) == "from_wire") {
                    auto decoded = taut::try_decode(view(bytes));
                    if (!decoded) {
                        fail(row.name, tag_name(decoded.error.tag), "valid enum wire int");
                        continue;
                    }
                    auto wire = decoded.value.try_int();
                    if (!wire) {
                        fail(row.name, tag_name(wire.error.tag), "valid enum wire int");
                        continue;
                    }
                    if (std::string_view(row.schema) == "Mode") {
                        auto mode = taut::try_Mode_from_wire(wire.value);
                        if (mode) fail(row.name, "decoded Mode", row.tag);
                        else expect_error(row, mode.error);
                    } else {
                        fail(row.name, row.schema, "known from_wire schema");
                    }
                } else {
                    fail(row.name, row.stage, "known stage");
                }
            }
        }

        int main() {
            run_round_trip();
            run_encode_fail();
            run_malformed();
            if (mismatches != 0) return 1;
            std::cout << "C++ parity corpus mismatches=0\\n";
            return 0;
        }
    """)
    source = source.replace("ROUND_ROWS", ",\n".join(round_rows))
    source = source.replace("ENCODE_ROWS", ",\n".join(encode_rows))
    source = source.replace("MAL_ROWS", ",\n".join(mal_rows))

    run = _compile_and_run_cpp(tmp_path, source, "cpp_i64_parity")
    assert "C++ parity corpus mismatches=0" in run.stdout


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
