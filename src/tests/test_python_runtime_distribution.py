"""Actual import/run conformance for source, package and supplied-runtime bindings."""
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from taut.cli import main
from taut.gen import scaffold
from taut.gen.python_runtime import BASE_FILES
from taut.ir.dsl import INT, F, Msg, Ref, method, schema, service
from taut.ir.load import load_schema

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src"
SHAPE_SOURCE = ROOT.parent / "taut-shape-py/src"
EXAMPLE = ROOT / "dev-docs/examples/python-oneof/content.taut.py"


@pytest.mark.parametrize('target', ['go', 'java'])
def test_parent_file_obstruction_on_pre313_pathlib(tmp_path, monkeypatch, target):
    """Older POSIX pathlib raises ENOTDIR for a child of a regular file."""
    import importlib
    import errno
    blocked = tmp_path / 'blocked'
    blocked.write_text('handwritten', encoding='utf-8')
    requested = blocked / 'owner'
    original = Path.lstat

    def lstat(path):
        if path == requested:
            raise NotADirectoryError(errno.ENOTDIR, 'Not a directory', str(path))
        return original(path)

    monkeypatch.setattr(Path, 'lstat', lstat)
    runtime = importlib.import_module('taut.gen.' + target + '_runtime')
    with pytest.raises(ValueError, match='obstructed'):
        runtime.canonical_path(requested)
    assert blocked.read_text(encoding='utf-8') == 'handwritten'
    assert sorted(path.name for path in tmp_path.iterdir()) == ['blocked']


def run(code, paths, *, success=True):
    prelude = "import sys\nsys.path[:0] = " + repr([str(p) for p in paths]) + "\n"
    env = dict(os.environ)
    env.pop("TAUT_SHAPE_SCHEMA", None)
    result = subprocess.run([sys.executable, "-I", "-S", "-c", prelude + code],
                            env=env, capture_output=True, text=True, encoding="utf-8")
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
    return result


BLOCK_COMPILER = '''
import importlib.abc
class NoCompiler(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("taut.ir", "taut.gen", "taut.cli", "taut.corpus", "setuptools", "taut.crdt")):
            raise AssertionError("application imported compiler/build module: " + fullname)
sys.meta_path.insert(0, NoCompiler())
'''

BEHAVIOR = '''
from a.python import api as a
from b.python import api as b
from taut.descriptors import MessageDescriptor
from taut.validation import ValidationReport, ValidationIssue, validate_record, is_record_valid
from taut.wire import cbor, codec, jsoncodec
import taut_shape.foundation as f
assert not any(n.endswith(".engine") for n in sys.modules)
assert f.MessageDescriptor is MessageDescriptor
assert f.ValidationReport is ValidationReport and f.ValidationIssue is ValidationIssue
assert f.codec.DecodeError is codec.DecodeError and f.cbor.DecodeError is cbor.DecodeError
assert type(a.Content.DESCRIPTOR) is type(b.Content.DESCRIPTOR) is MessageDescriptor
assert not hasattr(b.Content, "validate")
child = b.Content(b.ContentKind.text)
assert a.Envelope(child).validate().issues[0].path[-1].field_name == "text"
samples = [a.Content(a.ContentKind.text), a.Content(a.ContentKind.number, number=0),
           a.Content(a.ContentKind.flag, flag=False), a.Content(a.ContentKind.text, text=""),
           a.Content(a.ContentKind.items, items=[]), a.Content(a.ContentKind.empty),
           a.Content(a.ContentKind.number, text="extra"),
           a.VirtualEnvelope(content=child)]
observed = []
for v in samples:
    for recursive in (False, True):
        r = validate_record(v, v.DESCRIPTOR, v.__taut_binding__, recursive=recursive)
        assert is_record_valid(v, v.DESCRIPTOR, v.__taut_binding__, recursive=recursive) == (r.is_valid() and r.is_complete())
        observed.append([r.is_valid(), r.is_complete(), r.scope,
                         [[i.code, i.rule, [[p.kind, p.field_name, p.index, p.key_type, p.key_cbor_base64] for p in i.path]] for i in r.issues],
                         [[d.rule, d.reason_code, [p.field_name for p in d.path]] for d in r.deferred_checks]])
native = {"kind": "number", "text": "extra", "number": None, "flag": None, "items": None}
assert codec.decode(a.SCHEMA, "Content", codec.encode(a.SCHEMA, "Content", native)) == native
assert jsoncodec.to_json(a.SCHEMA, "Content", native) == '{"kind":"number","text":"extra"}'
from taut_shape.value import wire as vw
from taut_shape.value import _generated as vg
request = vg.ValueReadRequest("id", "stream")
tag, body = vw.encode_read(request)
assert codec.decode(vg.SCHEMA, "ValueReadRequest", body) == {"value_id": "id", "stream_id": "stream"}
assert type(vg.ValueReadRequest.DESCRIPTOR) is MessageDescriptor
assert f.validate_record(request, request.DESCRIPTOR, request.__taut_binding__).is_valid()
assert "taut.ir.load" not in sys.modules and "taut.gen.scaffold" not in sys.modules
import json
print(json.dumps(observed, sort_keys=True))
'''


def generate_pair(tmp_path, modes, *, validation=True):
    full = load_schema(EXAMPLE)
    child_schema = dataclasses.replace(full, messages={"Content": full.messages["Content"]})
    owner = tmp_path / "foundation"
    bindings = {"python": {"source_root": str(owner)}} if "source" in modes else None
    if modes[0] != "source" and "source" in modes:
        # Explicit consumers require a materialized owner. This seed creates no child types.
        scaffold.emit(schema(), tmp_path / "support", langs=["python"], runtime_mode="source",
                      validation=True, runtime_bindings=bindings)
    scaffold.emit(child_schema, tmp_path / "b", langs=["python"], runtime_mode=modes[0],
                  validation=False, runtime_bindings=bindings)
    if modes == ("source", "package"):
        scaffold.emit(child_schema, tmp_path / "support", langs=["python"], runtime_mode="source",
                      validation=True, runtime_bindings=bindings)
    # Parent must not regenerate its child's classes or require its methods.
    scaffold.emit(full, tmp_path / "a", langs=["python"], runtime_mode=modes[1], validation=validation,
                  runtime_bindings=bindings,
                  python_external_types={"Content": "b.python.api.Content", "ContentKind": "b.python.api.ContentKind"})
    if "source" in modes:
        # Ensure a source owner assembled with validation even when the disabled child ran first.
        paths = [owner, tmp_path, SHAPE_SOURCE]
    else:
        paths = [SOURCE, tmp_path, SHAPE_SOURCE]
    return paths


@pytest.mark.parametrize("modes", [("source", "source"), ("package", "package"),
                                    ("package", "source"), ("source", "package"), (None, None)])
def test_shared_owner_independent_child_library_and_same_corpus(tmp_path, modes):
    paths = generate_pair(tmp_path, modes)
    result = run(BLOCK_COMPILER + BEHAVIOR, paths)
    observed = json.loads(result.stdout)
    assert len(observed) == 16
    assert observed[0][:3] == [False, True, "local"]
    assert observed[2][:2] == [True, True]
    assert observed[-1][:2] == [False, False]


@pytest.mark.parametrize("mode", ["source", "package", None])
def test_validation_off_needs_no_engine_or_compiler(tmp_path, mode):
    s = load_schema(EXAMPLE)
    scaffold.emit(s, tmp_path, langs=["python"], runtime_mode=mode)
    if mode == "source":
        runtime = tmp_path / "python/taut"
        assert not (runtime / "validation.py").exists()
        assert {p.relative_to(runtime).as_posix() for p in runtime.rglob("*.py")} == set(BASE_FILES)
        for rel in BASE_FILES:
            assert (runtime / rel).read_bytes() == (SOURCE / "taut" / rel).read_bytes()
    code = BLOCK_COMPILER + '''
class NoValidation(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "taut.validation": raise AssertionError("validation off imported engine")
sys.meta_path.insert(0, NoValidation())
import api
from taut.wire import codec, jsoncodec
import taut_shape.foundation as f
assert not hasattr(api.Content, "validate")
assert api.Content.DESCRIPTOR.fields[0].name == "kind"
assert f.MessageDescriptor is type(api.Content.DESCRIPTOR)
assert not any(n.endswith(".engine") for n in sys.modules)
native = {"kind":"number", "number":42}
assert jsoncodec.to_json(api.SCHEMA, "Content", native) == '{"kind":"number","number":"42"}'
assert codec.decode(api.SCHEMA, "Content", codec.encode(api.SCHEMA, "Content", native))["number"] == 42
'''
    paths = [tmp_path / "python", SHAPE_SOURCE] + ([] if mode == "source" else [SOURCE])
    run(code, paths)


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("mode", ["source", "package", None])
@pytest.mark.parametrize("validation", [False, True])
def test_generation_mode_goldens(tmp_path, mode, validation):
    s = load_schema(EXAMPLE)
    scaffold.emit(s, tmp_path, langs=["python"], runtime_mode=mode, validation=validation)
    expected = ROOT / "dev-docs/examples/python-oneof/goldens" / ("on.py" if validation else "off.py")
    assert (tmp_path / "python/api.py").read_text(encoding="utf-8") == expected.read_text(encoding="utf-8")
    manifest = json.loads((tmp_path / "python/.taut-python-outputs.json").read_text())
    assert manifest["mode"] == (mode or "supplied")
    assert manifest["validation"] is validation
    assert (tmp_path / "python/taut").exists() is (mode == "source")


def test_safe_transitions_shared_users_and_no_partial_writes(tmp_path):
    s = load_schema(EXAMPLE)
    owner = tmp_path / "owner"
    binding = {"python": {"source_root": str(owner)}}
    for name, enabled in (("a", True), ("b", False)):
        scaffold.emit(s, tmp_path / name, langs=["python"], runtime_mode="source", validation=enabled, runtime_bindings=binding)
    assert (owner / "taut/validation.py").exists()
    scaffold.emit(s, tmp_path / "a", langs=["python"], runtime_mode="source", validation=False, runtime_bindings=binding)
    assert not (owner / "taut/validation.py").exists()
    assert not "def validate(" in (tmp_path / "a/python/api.py").read_text()
    # Switching one user to package must preserve the other source user's foundation.
    scaffold.emit(s, tmp_path / "a", langs=["python"], runtime_mode="package")
    assert (owner / "taut/descriptors.py").exists()
    scaffold.emit(s, tmp_path / "b", langs=["python"], runtime_mode="package")
    assert not (owner / "taut/descriptors.py").exists()
    scaffold.emit(s, tmp_path / "a", langs=["python"], runtime_mode="source", validation=True)
    target = tmp_path / "a/python/taut/validation.py"
    target.write_text(target.read_text() + "\n# application modification\n")
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="modified"):
        scaffold.emit(s, tmp_path / "a", langs=["python"], runtime_mode="package")
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("conflict", ["handwritten", "unknown_copy", "modified", "contract", "new_unknown"])
def test_runtime_preflight_protects_outputs(tmp_path, conflict):
    s = load_schema(EXAMPLE)
    runtime = tmp_path / "python/taut"
    if conflict in ("handwritten", "unknown_copy"):
        runtime.mkdir(parents=True)
        (runtime / "codec.py").write_text("# generated-looking header\n" if conflict == "unknown_copy" else "handwritten")
    else:
        scaffold.emit(s, tmp_path, langs=["python"], runtime_mode="source", validation=True)
        if conflict == "modified":
            (runtime / "wire/cbor.py").write_text("modified")
        elif conflict == "new_unknown":
            (runtime / "mystery.py").write_text("unknown")
        else:
            path = tmp_path / "python/.taut-runtime.json"
            data = json.loads(path.read_text()); data["codec"] = 9
            path.write_text(json.dumps(data))
    before = snapshot(tmp_path)
    with pytest.raises(ValueError):
        scaffold.emit(s, tmp_path, langs=["python"], runtime_mode="source")
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("options", [dict(runtime=True, runtime_mode="package"), dict(runtime_mode="wrong"),
     dict(runtime=1), dict(validation=1), dict(runtime_bindings={"python":{"descriptor_contract": 99}}),
     dict(runtime_bindings={"python":{"module": "private.taut"}})])
def test_programmatic_selection_conflicts_before_writes(tmp_path, options):
    with pytest.raises((ValueError, TypeError)):
        scaffold.emit(load_schema(EXAMPLE), tmp_path, langs=["python"], **options)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("flags", [["--runtime", "source"], ["--with-runtime"],
    ["--with-runtime", "--runtime", "source"], ["--runtime", "source", "--runtime", "source"],
    ["--runtime", "package"], []])
def test_cli_mode_matrix_and_validation(tmp_path, flags):
    assert main(["gen", str(EXAMPLE), "-o", str(tmp_path), "-l", "python", "--api-only", "--with-validation", *flags]) == 0
    assert "def validate(" in (tmp_path / "python/api.py").read_text()
    assert (tmp_path / "python/taut/validation.py").exists() is ("source" in flags or "--with-runtime" in flags)


@pytest.mark.parametrize("flags", [["--runtime", "source", "--runtime", "package"],
    ["--with-runtime", "--runtime", "package"], ["--runtime", "missing"], ["--runtime"]])
def test_cli_conflict_unknown_missing_before_writes(tmp_path, flags):
    with pytest.raises((ValueError, SystemExit)):
        main(["gen", str(EXAMPLE), "-o", str(tmp_path), "-l", "python", *flags])
    assert not list(tmp_path.iterdir())


def test_emit_all_forwards_keyword_modes(tmp_path):
    s = schema(Record=Msg(data=F(1, INT)))
    s = dataclasses.replace(s, services={"Svc": service("Svc", method("get", role="query", out=Ref.Record))})
    scaffold.emit_all(s, "Svc", tmp_path, langs=["python"], runtime=True, runtime_mode="source", validation=True)
    assert (tmp_path / "python/taut/validation.py").exists()
    assert "def validate(" in (tmp_path / "python/api.py").read_text()


def test_old_child_wrong_contract_and_split_owner_rejected(tmp_path):
    s = load_schema(EXAMPLE)
    s = dataclasses.replace(s, messages={"Content": s.messages["Content"]})
    scaffold.emit(s, tmp_path / "child", langs=["python"], validation=False)
    full = load_schema(EXAMPLE)
    scaffold.emit(full, tmp_path / "parent", langs=["python"], validation=True,
                  python_external_types={"Content":"child.python.api.Content", "ContentKind":"child.python.api.ContentKind"})
    prelude = "from child.python import api as c\n"
    for mutation, expected in [("del c.Content.DESCRIPTOR; del c.Content.__taut_binding__", "regenerate/rebind child"),
                               ("c.Content.__taut_binding__ = object()", "split runtime owner")]:
        result = run(prelude + mutation + "\nimport parent.python.api\n", [SOURCE, tmp_path], success=False)
        assert expected in result.stderr
    # Explicitly incompatible contract, before any instance validation call.
    code = (tmp_path / "parent/python/api.py").read_text()
    (tmp_path / "parent/python/api.py").write_text(code.replace("descriptor=1, codec=1", "descriptor=99, codec=1"))
    result = run("import parent.python.api", [SOURCE, tmp_path], success=False)
    assert "required owner=" in result.stderr and "descriptor=99" in result.stderr


def test_same_behavior_exactly_across_distributions(tmp_path):
    results = []
    for index, modes in enumerate((("source", "source"), ("package", "package"), ("source", "package"))):
        root = tmp_path / str(index)
        paths = generate_pair(root, modes)
        results.append(json.loads(run(BLOCK_COMPILER + BEHAVIOR, paths).stdout))
    assert results[0] == results[1] == results[2]


def test_missing_package_exports_and_actual_second_owner_are_clear_errors(tmp_path):
    scaffold.emit(load_schema(EXAMPLE), tmp_path / "app", langs=["python"], runtime_mode="package", validation=True)
    result = run("import api", [tmp_path / "app/python"], success=False)
    assert "compatible taut foundation required" in result.stderr and "regenerate/rebind" in result.stderr
    # Load the real owner code at an alias to exercise nominal split prevention.
    code = '''
import importlib.util
spec = importlib.util.spec_from_file_location("private_contracts", CONTRACTS)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
'''.replace("CONTRACTS", repr(str(SOURCE / "taut/contracts.py")))
    result = run(code, [SOURCE], success=False)
    assert "split runtime owner" in result.stderr


def test_repeated_runtime_same_owner_reuses_and_shared_engine_survives(tmp_path):
    s = load_schema(EXAMPLE)
    root = tmp_path / "foundation"
    binding = {"python": {"source_root": str(root)}}
    for name in ("a", "b"):
        scaffold.emit(s, tmp_path / name, langs=["python"], runtime=True, validation=True, runtime_bindings=binding)
    before = snapshot(root)
    scaffold.emit(s, tmp_path / "a", langs=["python"], runtime=True, validation=False, runtime_bindings=binding)
    assert (root / "taut/validation.py").exists()  # b still needs it
    assert before["taut/validation.py"] == (root / "taut/validation.py").read_bytes()
    with pytest.raises(ValueError, match="generation lock"):
        from taut.gen.python_runtime import output_locks
        with output_locks([root]):
            scaffold.emit(s, tmp_path / "a", langs=["python"], runtime=True, runtime_bindings=binding)


@pytest.mark.parametrize("mode", ["package", None])
def test_explicit_consumer_requires_owner_then_keeps_engine_after_producer_detaches(tmp_path, mode):
    s = schema(Record=Msg(data=F(1, INT)))
    owner = tmp_path / "foundation"
    binding = {"python": {"source_root": str(owner)}}
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="source owner is unavailable"):
        scaffold.emit(s, tmp_path / "consumer", langs=["python"], runtime_mode=mode,
                      validation=True, runtime_bindings=binding)
    assert snapshot(tmp_path) == before
    assert not (tmp_path / "consumer").exists() and not owner.exists()
    scaffold.emit(s, tmp_path / "producer", langs=["python"], runtime_mode="source",
                  validation=True, runtime_bindings=binding)
    scaffold.emit(s, tmp_path / "consumer", langs=["python"], runtime_mode=mode,
                  validation=True, runtime_bindings=binding)
    for producer_mode in ("source", "package"):
        scaffold.emit(s, tmp_path / "producer", langs=["python"], runtime_mode=producer_mode,
                      validation=False, runtime_bindings=binding if producer_mode == "source" else None)
        assert (owner / "taut/validation.py").is_file()
        run(BLOCK_COMPILER + "\nimport api\nassert api.Record(1).is_valid()\n",
            [owner, tmp_path / "consumer/python"])


@pytest.mark.parametrize("external", [False, True])
def test_obstructed_runtime_directory_fails_before_any_output_write(tmp_path, external):
    owner = tmp_path / "foundation" if external else tmp_path / "app/python"
    owner.mkdir(parents=True)
    (owner / "taut").write_text("HANDWRITTEN RUNTIME PATH")
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="obstructed output directory"):
        scaffold.emit(schema(Record=Msg(data=F(1, INT))), tmp_path / "app", langs=["python"],
                      runtime_mode="source", runtime_bindings={"python":{"source_root":str(owner)}} if external else None)
    assert snapshot(tmp_path) == before


def test_linked_runtime_directory_cannot_redirect_writes(tmp_path):
    owner = tmp_path / "app/python"
    target = tmp_path / "handwritten-target"
    owner.mkdir(parents=True); target.mkdir()
    link = owner / "taut"
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        link.symlink_to(target, target_is_directory=True)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="unsafe/obstructed output directory"):
        scaffold.emit(schema(Record=Msg(data=F(1, INT))), tmp_path / "app", langs=["python"], runtime=True)
    assert snapshot(tmp_path) == before and not list(target.iterdir())


def test_owned_cleanup_cannot_follow_junction_into_unowned_identical_files(tmp_path):
    import shutil
    output = tmp_path / "app"
    scaffold.emit(schema(Record=Msg(data=F(1, INT))), output, langs=["python"], runtime=True)
    wire = output / "python/taut/wire"
    target = output / "python/handwritten-wire"
    shutil.copytree(wire, target)
    assert wire.resolve().is_relative_to(tmp_path.resolve())
    assert wire.is_dir() and not wire.is_symlink()
    shutil.rmtree(wire)  # only this test's verified generator-created directory
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(wire), str(target)], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        wire.symlink_to(target, target_is_directory=True)
    before = snapshot(tmp_path)
    assert len(list(target.iterdir())) == 4
    with pytest.raises(ValueError, match="unsafe/obstructed output directory alias"):
        scaffold.emit(schema(Record=Msg(data=F(1, INT))), output, langs=["python"], runtime_mode="package")
    assert snapshot(tmp_path) == before
    assert len(list(target.iterdir())) == 4
