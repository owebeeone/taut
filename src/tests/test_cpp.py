import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from taut.gen import cpp as cpp_gen
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk


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
