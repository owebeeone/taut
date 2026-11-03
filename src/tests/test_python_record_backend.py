"""Opt-in YIDL records retain one Taut owner and the default projection."""

import copy
import dataclasses
import pickle
import sys
import types
from pathlib import Path
import pytest
from taut.cli import main
from taut.gen.scaffold import emit, python_api
from taut.ir.dsl import INT, F, Msg, schema
from taut.ir.load import load_schema
from taut.wire import codec, jsoncodec

EXAMPLE = (
    Path(__file__).resolve().parents[2]
    / "dev-docs/examples/python-oneof/content.taut.py"
)
requires_yidl = pytest.mark.skipif(
    sys.version_info < (3, 12), reason="YIDL records require CPython3.12 or newer"
)


def generated(validation=True):
    name = "_yidl_records_" + str(len(sys.modules))
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(
        python_api(load_schema(EXAMPLE), validation=validation, python_records="yidl"),
        module.__dict__,
    )
    return module


@pytest.mark.parametrize("validation", [False, True])
def test_default_still_uses_stdlib(validation):
    s = load_schema(EXAMPLE)
    assert python_api(s, validation=validation) == python_api(
        s, validation=validation, python_records="stdlib"
    )
    assert "taut.records" not in python_api(s, validation=validation)


@pytest.mark.parametrize("validation", [False, True])
@requires_yidl
def test_mutate_repair_then_deep_freeze(validation):
    from taut.records import FrozenDict

    m = generated(validation)
    child = m.Content(m.ContentKind.items, items=[1, 2])
    external_list = [child]
    external_map = {"a": child}
    value = m.Collection(external_list, external_map)
    value._taut_freeze()
    value._taut_freeze()
    external_list.append(m.Content(m.ContentKind.empty))
    external_map["b"] = m.Content(m.ContentKind.empty)
    assert len(value.entries) == len(value.by_key) == 1
    assert value.entries[0] is value.by_key["a"] is child
    assert type(value.entries) is tuple and type(value.by_key) is FrozenDict
    with pytest.raises(dataclasses.FrozenInstanceError):
        child.items = []
    with pytest.raises(TypeError):
        value.by_key["b"] = child
    assert hasattr(value, "validate") is validation
    if validation:
        assert value.is_valid()
    revised = dataclasses.replace(child, items=[3])
    revised.items.append(4)
    assert revised.items == [3, 4] and child.items == (1, 2)
    native = {
        "kind": "items",
        "text": None,
        "number": None,
        "flag": None,
        "items": child.items,
    }
    expected = dict(native, items=[1, 2])
    assert (
        codec.decode(m.SCHEMA, "Content", codec.encode(m.SCHEMA, "Content", native))
        == expected
    )
    assert (
        jsoncodec.from_json_value(
            m.SCHEMA, "Content", jsoncodec.to_json_value(m.SCHEMA, "Content", native)
        )
        == expected
    )


@requires_yidl
def test_freeze_field_name_does_not_collide():
    mod = types.ModuleType("_record_freeze_field")
    sys.modules[mod.__name__] = mod
    exec(
        python_api(schema(Record=Msg(freeze=F(1, INT))), python_records="yidl"),
        mod.__dict__,
    )
    value = mod.Record(1)
    value.freeze = 2
    value._taut_freeze()
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.freeze = 3


@requires_yidl
def test_invalid_draft_snapshot_and_frozen_validation():
    m = generated()
    value = m.Content(m.ContentKind.number, text="wrong")
    before = value.validate()
    assert len(before.issues) == 2
    value.text = None
    value.number = 0
    value._taut_freeze()
    assert value.is_valid() and len(before.issues) == 2
    assert type(value.DESCRIPTOR) is type(m.Collection.DESCRIPTOR)
    assert [f.name for f in dataclasses.fields(value)] == [
        "kind",
        "text",
        "number",
        "flag",
        "items",
    ]


@requires_yidl
def test_frozen_representations_do_not_weaken_mutable_validation():
    m = generated()
    value = m.Collection((), {})
    assert not value.is_valid()
    value.entries = []
    value._taut_freeze()
    assert value.is_valid()
    default = types.ModuleType("_record_std")
    sys.modules[default.__name__] = default
    exec(python_api(load_schema(EXAMPLE), validation=True), default.__dict__)
    assert not default.Collection((), {}).is_valid()


@requires_yidl
def test_recursive_records_and_shared_children():
    m = generated()
    child = m.Tree(None, [])
    root = m.Tree(None, [child, child])
    root._taut_freeze()
    assert root.children[0] is root.children[1] and root.is_valid()
    with pytest.raises(dataclasses.FrozenInstanceError):
        child.content = None


@requires_yidl
def test_separately_generated_yidl_child_uses_shared_owner():
    s = load_schema(EXAMPLE)
    child_schema = dataclasses.replace(s, messages={"Content": s.messages["Content"]})
    child = types.ModuleType("_yidl_external_child")
    sys.modules[child.__name__] = child
    exec(
        python_api(child_schema, validation=True, python_records="yidl"), child.__dict__
    )
    parent = types.ModuleType("_yidl_external_parent")
    sys.modules[parent.__name__] = parent
    exec(
        python_api(
            s,
            validation=True,
            python_records="yidl",
            external_types={
                "Content": child.__name__ + ".Content",
                "ContentKind": child.__name__ + ".ContentKind",
            },
        ),
        parent.__dict__,
    )
    value = parent.Envelope(child.Content(child.ContentKind.items, items=[1]))
    value._taut_freeze()
    assert value.is_valid() and value.content.DESCRIPTOR is child.Content.DESCRIPTOR
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.content.items = []


@requires_yidl
def test_mixed_backend_child_requires_explicit_regeneration():
    s = load_schema(EXAMPLE)
    child_schema = dataclasses.replace(s, messages={"Content": s.messages["Content"]})
    child = types.ModuleType("_stdlib_external_child")
    sys.modules[child.__name__] = child
    exec(python_api(child_schema), child.__dict__)
    parent = types.ModuleType("_mixed_external_parent")
    sys.modules[parent.__name__] = parent
    exec(
        python_api(
            s,
            python_records="yidl",
            external_types={
                "Content": child.__name__ + ".Content",
                "ContentKind": child.__name__ + ".ContentKind",
            },
        ),
        parent.__dict__,
    )
    value = parent.Envelope(child.Content(child.ContentKind.empty))
    with pytest.raises(TypeError, match="regenerate the dependency"):
        value._taut_freeze()


def test_backend_does_not_change_other_language_output(tmp_path):
    s = schema(Record=Msg(value=F(1, INT)))
    emit(s, tmp_path / "a", langs=["python", "js"], runtime=True)
    emit(s, tmp_path / "b", langs=["python", "js"], runtime=True, python_records="yidl")
    # Ownership manifests legitimately contain their distinct absolute output roots.
    before = {
        p.relative_to(tmp_path / "a/js"): p.read_bytes()
        for p in (tmp_path / "a/js").rglob("*")
        if p.is_file() and not p.name.startswith(".taut-")
    }
    after = {
        p.relative_to(tmp_path / "b/js"): p.read_bytes()
        for p in (tmp_path / "b/js").rglob("*")
        if p.is_file() and not p.name.startswith(".taut-")
    }
    assert before == after


def test_frozen_map_copy_pickle_and_regular_mutators():
    from taut.records import FrozenDict

    value = FrozenDict({"a": 1})
    for change in (
        lambda: value.update(b=2),
        lambda: value.pop("a"),
        lambda: value.clear(),
        lambda: value.setdefault("b", 2),
        lambda: value.__ior__({"b": 2}),
        lambda: value.popitem(),
    ):
        with pytest.raises(TypeError):
            change()
    assert copy.deepcopy(value) == pickle.loads(pickle.dumps(value)) == {"a": 1}
    assert type(copy.deepcopy(value)) is FrozenDict
    value.__init__({"b": 2})
    assert value == {"a": 1}


@pytest.mark.parametrize("backend", ["stdlib", "yidl"])
def test_python_option_rejected_without_python_before_writes(tmp_path, backend):
    target = tmp_path / "out"
    with pytest.raises(ValueError, match="Python.*target"):
        emit(
            schema(Record=Msg(value=F(1, INT))),
            target,
            langs=["js"],
            python_records=backend,
        )
    assert not target.exists()
    with pytest.raises(ValueError, match="Python.*target"):
        main(
            [
                "gen",
                str(EXAMPLE),
                "-o",
                str(target),
                "--lang",
                "js",
                "--python-records",
                backend,
            ]
        )
    assert not target.exists()


def test_python_cli_yidl_source_delivery(tmp_path):
    target = tmp_path / "out"
    assert (
        main(
            [
                "gen",
                str(EXAMPLE),
                "-o",
                str(target),
                "--lang",
                "python",
                "--python-records",
                "yidl",
                "--runtime",
                "source",
                "--with-validation",
            ]
        )
        == 0
    )
    assert (target / "python/taut/records.py").exists()
    assert "taut_dataclass" in (target / "python/api.py").read_text()


@requires_yidl
def test_incompatible_yidl_runtime_reports_missing_feature(monkeypatch):
    import yidl_dataclass
    from taut.records import taut_dataclass

    monkeypatch.setattr(yidl_dataclass, "dataclass", lambda cls=None, **kwargs: cls)
    with pytest.raises(ImportError, match="lacks freeze_method support"):
        taut_dataclass(type("Record", (), {"__annotations__": {"value": int}}))


def test_old_taut_runtime_rejects_yidl_capability(monkeypatch):
    import taut.contracts

    monkeypatch.setattr(
        taut.contracts,
        "CAPABILITIES",
        frozenset({"descriptors.v1", "codec.v1", "oneof.v1"}),
    )
    with pytest.raises(taut.contracts.ConfigurationError, match="records.yidl.v1"):
        generated()
