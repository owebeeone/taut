"""IR version 2 (D27; TautOptions.md OPT-I1-I3, OPT-L5, OPT-F1, OPT-F4).

The export writes every level's declared `options`: the file's at the top level, each message's,
field's and enum's, and `{}` at the three reserved levels, each service, method and enum value (the
last through its enum's `member_options`). The file and each message also carry `effective`. The
loader reads versions 1 and 2 only. In version 2 it refuses an unknown option, any option at a
reserved level, a value its option cannot take, an `effective` other than what the options resolve
to, and an `effective` naming a wire option Python's runtime does not implement.
"""

import copy
import json
from pathlib import Path

import pytest

from taut.corpus import build, glade_build, resext_build
from taut.ir.dsl import BYTES, INT, Enum, F, List, Msg, Params, Ref, method, option, schema, service
from taut.ir.export import schema_json
from taut.ir.load import PYTHON_WIRE_OPTIONS, load_schema, schema_from_json
from taut.ir.options import OPTIONS, OptionDef, effective, effective_map

ROOT = Path(__file__).resolve().parents[2]
TASKS = ROOT / "docs" / "examples" / "tasks"
DEFAULTS = {"max_depth": 32, "max_encoded_len": None}
V2_KEYS = ("options", "effective", "member_options")

# What taut wrote before version 2 for `_job_schema()`, with `shapes` emptied (the loader never
# reads them): no options, no effective values.
V1_TEXT = (
    '{"version": 1, "shapes": {}, "enums": [{"name": "Mode", "members": {"fast": 0, "slow": 1}}], '
    '"messages": [{"name": "Job", "reserved_tags": [], "reserved_names": [], "next_id": null, '
    '"fields": [{"name": "id", "tag": 1, "type": {"k": "scalar", "scalar": "int"}, '
    '"optional": false, "transient": false, "merge": null}, {"name": "mode", "tag": 2, '
    '"type": {"k": "enum", "name": "Mode"}, "optional": true, "transient": false, "merge": null}]}], '
    '"services": [{"name": "Jobs", "methods": [{"name": "get", "role": "query", "shape": "unary", '
    '"params": [{"name": "id", "type": {"k": "scalar", "scalar": "int"}}], '
    '"out": [{"slot": "value", "type": {"k": "msg", "name": "Job"}}]}]}], "extensions": []}'
)


def _job_schema():
    """One of each level, nothing declared."""
    return schema(
        Enum("Mode", fast=0, slow=1),
        Msg("Job", F("id", 1, INT), F("mode", 2, Ref("Mode"), optional=True)),
        service("Jobs", method("get", role="query", params=Params(id=INT), out=Ref("Job"))),
    )


def _bounded():
    """Both bounds declared: `Tree` its own depth, `Leaf` inheriting the file's (OPT-D3)."""
    return schema(
        option.max_depth(1), option.max_encoded_len(4096),
        Msg("Tree", option.max_depth(64), F("children", 1, List(Ref("Tree")))),
        Msg("Leaf", F("x", 1, INT)),
    )


@pytest.fixture
def doc_option(monkeypatch):
    """A metadata option at field and enum level, as a later option would be (OPT-D1): no
    registered option takes those levels yet."""
    monkeypatch.setitem(OPTIONS, "doc", OptionDef("doc", str, frozenset({"field", "enum"}),
                                                  default="", klass="metadata", inherits=()))


def _declaring():
    """An option at each of the four levels that take one (the enum's and the field's `doc`),
    and both bounds resolved three ways: declared, inherited from the file, and the file's."""
    return schema(
        option.max_depth(16), option.max_encoded_len(4096),
        Enum("Mode", option.doc("how fast"), fast=0, slow=1),
        Msg("Tree", option.max_depth(64), F("children", 1, List(Ref("Tree")), option.doc("subtrees"))),
        Msg("Blob", option.max_encoded_len(2**20), F("data", 1, BYTES), F("mode", 2, Ref("Mode"))),
        Msg("Plain", F("x", 1, INT)),
        service("Jobs", method("get", role="query", params=Params(id=INT), out=Ref("Tree"))),
    )


def _level(ir: dict, where: str) -> dict:
    """The IR object of the first element at level `where`."""
    if where == "file":
        return ir
    if where == "message":
        return ir["messages"][0]
    if where == "field":
        return ir["messages"][0]["fields"][0]
    if where == "enum":
        return ir["enums"][0]
    if where == "service":
        return ir["services"][0]
    if where == "method":
        return ir["services"][0]["methods"][0]
    raise AssertionError(where)


def _options_at(ir: dict, where: str) -> dict:
    """The `options` map of the first element at level `where`, an enum value included."""
    if where == "enum_value":
        return ir["enums"][0]["member_options"]["fast"]
    return _level(ir, where)["options"]


def _as_version_1(ir: dict) -> dict:
    """`ir` as taut wrote it before version 2: version 1, no options, no effective values."""
    old = copy.deepcopy(ir)
    old["version"] = 1
    levels = [old, *old["enums"], *old["messages"], *old["services"]]
    levels += [f for m in old["messages"] for f in m["fields"]]
    levels += [mt for s in old["services"] for mt in s["methods"]]
    for level in levels:
        for key in V2_KEYS:
            level.pop(key, None)
    return old


# --- the export (OPT-I1, OPT-I2) --------------------------------------------------------------

def test_export_writes_version_2_with_options_at_all_seven_levels(doc_option):
    ir = schema_json(_declaring())
    assert ir["version"] == 2
    assert ir["options"] == {"max_depth": 16, "max_encoded_len": 4096}
    mode = ir["enums"][0]
    assert mode["options"] == {"doc": "how fast"}
    assert mode["member_options"] == {"fast": {}, "slow": {}}   # enum values: reserved
    tree, blob, plain = ir["messages"]
    assert tree["options"] == {"max_depth": 64}
    assert blob["options"] == {"max_encoded_len": 2**20}
    assert plain["options"] == {}
    assert tree["fields"][0]["options"] == {"doc": "subtrees"}
    assert [f["options"] for f in blob["fields"]] == [{}, {}]
    jobs = ir["services"][0]
    assert jobs["options"] == {}                                # services: reserved
    assert jobs["methods"][0]["options"] == {}                  # methods: reserved


def test_export_writes_effective_at_the_file_and_each_message_only(doc_option):
    s = _declaring()
    ir = schema_json(s)
    assert ir["effective"] == {"max_depth": 16, "max_encoded_len": 4096} == effective_map(s)
    assert {m["name"]: m["effective"] for m in ir["messages"]} == {
        "Tree": {"max_depth": 64, "max_encoded_len": 4096},     # its own depth, the file's length
        "Blob": {"max_depth": 16, "max_encoded_len": 2**20},    # the file's depth, its own length
        "Plain": {"max_depth": 16, "max_encoded_len": 4096},    # the file's
    }
    for m in ir["messages"]:
        assert m["effective"] == effective_map(s, message=m["name"])
        assert all("effective" not in f for f in m["fields"])
    assert "effective" not in ir["enums"][0]
    assert "effective" not in ir["services"][0]
    assert "effective" not in ir["services"][0]["methods"][0]


def test_nothing_declared_exports_empty_options_and_the_defaults():
    ir = schema_json(_job_schema())
    assert ir["options"] == {}
    assert ir["effective"] == DEFAULTS
    assert ir["messages"][0]["options"] == {}
    assert ir["messages"][0]["effective"] == DEFAULTS
    assert json.dumps(ir["effective"]) == '{"max_depth": 32, "max_encoded_len": null}'


def test_export_places_the_new_keys_after_each_level_s_name(doc_option):
    ir = schema_json(_declaring())
    assert list(ir) == ["version", "options", "effective", "shapes", "enums", "messages",
                        "services", "extensions"]
    assert list(ir["enums"][0]) == ["name", "options", "members", "member_options"]
    assert list(ir["messages"][0]) == ["name", "options", "effective", "reserved_tags",
                                       "reserved_names", "next_id", "fields"]
    assert list(ir["messages"][0]["fields"][0]) == ["name", "tag", "options", "type", "optional",
                                                    "transient", "merge"]
    assert list(ir["services"][0]) == ["name", "options", "methods"]
    assert list(ir["services"][0]["methods"][0]) == ["name", "options", "role", "shape", "params",
                                                     "out"]


def test_without_the_new_keys_the_export_is_version_1_key_for_key():
    ir = schema_json(_job_schema())
    ir["shapes"] = {}
    assert json.dumps(_as_version_1(ir)) == V1_TEXT   # every other key, in its order


def test_the_export_does_not_share_the_model_s_option_maps(doc_option):
    s = _declaring()
    ir = schema_json(s)
    ir["options"]["max_depth"] = 1
    ir["messages"][0]["options"].clear()
    ir["messages"][0]["fields"][0]["options"].clear()
    ir["enums"][0]["options"].clear()
    assert s.options == {"max_depth": 16, "max_encoded_len": 4096}
    assert s.messages["Tree"].options == {"max_depth": 64}
    assert s.messages["Tree"].fields[0].options == {"doc": "subtrees"}
    assert s.enums["Mode"].options == {"doc": "how fast"}


# --- the round trip ---------------------------------------------------------------------------

def test_dsl_export_load_round_trips_options_at_every_level(doc_option):
    s = _declaring()
    back = schema_from_json(json.loads(json.dumps(schema_json(s))))
    assert back == s
    assert back.options == {"max_depth": 16, "max_encoded_len": 4096}
    assert back.enums["Mode"].options == {"doc": "how fast"}
    assert back.messages["Tree"].options == {"max_depth": 64}
    assert back.messages["Tree"].fields[0].options == {"doc": "subtrees"}
    assert back.messages["Plain"].options == {}
    assert effective(back, "max_depth", message="Blob") == 16
    assert schema_json(back) == schema_json(s)


def test_a_known_option_at_a_wrong_level_loads_as_the_dsl_builds_it():
    # A wrong level is validate's to refuse (OPT-L4), for IR as for the DSL: the loader keeps it.
    s = schema(Enum("Mode", option.max_depth(3), fast=0),
               Msg("M", F("x", 1, INT, option.max_encoded_len(9))))
    back = schema_from_json(schema_json(s))
    assert back == s
    assert back.enums["Mode"].options == {"max_depth": 3}
    assert back.messages["M"].fields[0].options == {"max_encoded_len": 9}


# --- version 1 --------------------------------------------------------------------------------

def test_version_1_still_loads_and_resolves_to_the_defaults():
    back = schema_from_json(json.loads(V1_TEXT))
    assert back == _job_schema()
    assert back.options == {}
    assert back.messages["Job"].options == {}
    assert back.enums["Mode"].options == {}
    assert effective_map(back) == DEFAULTS
    assert effective_map(back, message="Job") == DEFAULTS


@pytest.mark.parametrize("where, key", [
    ("file", "options"), ("file", "effective"), ("message", "options"), ("message", "effective"),
    ("field", "options"), ("enum", "options"), ("enum", "member_options"), ("service", "options"),
    ("method", "options"),
])
def test_version_1_refuses_a_key_version_2_added(where, key):
    ir = json.loads(V1_TEXT)
    _level(ir, where)[key] = {}
    with pytest.raises(ValueError, match=f"version 1 .*'{key}'"):
        schema_from_json(ir)


# --- the version (OPT-I1) ---------------------------------------------------------------------

@pytest.mark.parametrize("version", [0, 3, -1, None, "2", 2.0, True])
def test_load_refuses_any_version_but_1_and_2(version):
    ir = schema_json(_job_schema())
    ir["version"] = version
    with pytest.raises(ValueError, match=r"unsupported IR version .*: this taut reads versions 1 and 2"):
        schema_from_json(ir)


def test_load_refuses_an_ir_without_a_version():
    ir = schema_json(_job_schema())
    del ir["version"]
    with pytest.raises(ValueError, match="unsupported IR version"):
        schema_from_json(ir)


def test_load_refuses_an_ir_that_is_not_an_object():
    with pytest.raises(ValueError, match="a taut IR is a JSON object"):
        schema_from_json([])


# --- options (OPT-I2, OPT-F1) -----------------------------------------------------------------

@pytest.mark.parametrize("where", ["file", "message", "field", "enum"])
def test_load_refuses_an_unknown_option(where):
    ir = schema_json(_job_schema())
    _options_at(ir, where)["max_dept"] = 16
    with pytest.raises(ValueError, match="unknown option 'max_dept'; known options: max_depth"):
        schema_from_json(ir)


@pytest.mark.parametrize("where", ["service", "method", "enum_value"])
@pytest.mark.parametrize("name, value", [("max_depth", 16), ("idempotent", True)])
def test_load_refuses_any_option_at_a_reserved_level(where, name, value):
    ir = schema_json(_job_schema())
    _options_at(ir, where)[name] = value
    with pytest.raises(ValueError, match=f"'{name}' at a reserved level"):
        schema_from_json(ir)


@pytest.mark.parametrize("where", ["file", "message", "field", "enum"])
@pytest.mark.parametrize("name, value", [
    ("max_depth", 0), ("max_depth", 129), ("max_depth", "16"), ("max_depth", 16.0),
    ("max_depth", True), ("max_depth", None),
    ("max_encoded_len", 0), ("max_encoded_len", 2**31), ("max_encoded_len", "1k"),
    ("max_encoded_len", None),   # no bound is the absence of a declaration, never a value
])
def test_load_checks_each_value(where, name, value):
    ir = schema_json(_job_schema())
    _options_at(ir, where)[name] = value
    with pytest.raises(ValueError, match=f"option {name} takes"):
        schema_from_json(ir)


@pytest.mark.parametrize("where", ["file", "message", "field", "enum", "enum_value", "service",
                                   "method"])
def test_load_refuses_options_that_are_not_an_object(where):
    ir = schema_json(_job_schema())
    if where == "enum_value":
        ir["enums"][0]["member_options"]["fast"] = []
    else:
        _level(ir, where)["options"] = []
    with pytest.raises(ValueError, match="options must be an object"):
        schema_from_json(ir)


def test_load_refuses_member_options_that_are_not_an_object_or_name_no_member():
    ir = schema_json(_job_schema())
    ir["enums"][0]["member_options"] = []
    with pytest.raises(ValueError, match="member_options must be an object"):
        schema_from_json(ir)
    ir = schema_json(_job_schema())
    ir["enums"][0]["member_options"]["gone"] = {}
    with pytest.raises(ValueError, match="enum Mode: member_options names 'gone', not a member"):
        schema_from_json(ir)


# --- effective (OPT-I3, OPT-F1, OPT-F4) -------------------------------------------------------

@pytest.mark.parametrize("where, name", [("file", "the file"), ("message", "message Tree")])
def test_load_refuses_a_version_2_ir_without_effective(where, name):
    ir = schema_json(_bounded())
    del _level(ir, where)["effective"]
    with pytest.raises(ValueError, match=f"{name}: a version 2 IR carries effective values"):
        schema_from_json(ir)


@pytest.mark.parametrize("where", ["file", "message"])
def test_load_refuses_an_effective_that_is_not_an_object(where):
    ir = schema_json(_bounded())
    _level(ir, where)["effective"] = [64]
    with pytest.raises(ValueError, match="effective must be an object"):
        schema_from_json(ir)


@pytest.mark.parametrize("where, name", [("file", "the file"), ("message", "message Tree")])
def test_load_refuses_a_hand_edited_effective(where, name):
    ir = schema_json(_bounded())
    _level(ir, where)["effective"]["max_depth"] = 100
    with pytest.raises(ValueError, match=f"{name}: effective .* stale or hand-edited"):
        schema_from_json(ir)


def test_load_refuses_an_effective_left_stale_by_a_changed_declaration():
    ir = schema_json(_bounded())
    ir["messages"][0]["options"]["max_depth"] = 8           # Tree's own
    with pytest.raises(ValueError, match="message Tree: effective .* stale or hand-edited"):
        schema_from_json(ir)
    ir = schema_json(_bounded())
    ir["options"]["max_depth"] = 2                          # the file's, which Leaf inherits
    ir["effective"]["max_depth"] = 2
    with pytest.raises(ValueError, match="message Leaf: effective .* stale or hand-edited"):
        schema_from_json(ir)


@pytest.mark.parametrize("value", [True, 1.0])
def test_load_compares_effective_values_exactly(value):
    ir = schema_json(_bounded())
    assert ir["effective"]["max_depth"] == 1 == value         # equal in Python, not in the IR
    ir["effective"]["max_depth"] = value
    with pytest.raises(ValueError, match="the file: effective .* stale or hand-edited"):
        schema_from_json(ir)


def test_load_refuses_an_effective_that_lacks_an_option():
    ir = schema_json(_bounded())
    del ir["messages"][1]["effective"]["max_encoded_len"]
    with pytest.raises(ValueError, match="message Leaf: effective .* stale or hand-edited"):
        schema_from_json(ir)


@pytest.mark.parametrize("where, name", [("file", "the file"), ("message", "message Tree")])
def test_load_refuses_an_effective_naming_an_unknown_option(where, name):
    ir = schema_json(_bounded())
    _level(ir, where)["effective"]["max_frames"] = 8
    with pytest.raises(ValueError, match=f"{name}: effective names unknown option 'max_frames'"):
        schema_from_json(ir)


def _register(monkeypatch, name: str, klass: str) -> None:
    monkeypatch.setitem(OPTIONS, name, OptionDef(name, int, frozenset({"file", "message"}),
                                                 default=None, klass=klass,
                                                 inherits=("message", "file")))


def test_load_refuses_an_effective_naming_a_wire_option_python_does_not_implement(monkeypatch):
    _register(monkeypatch, "max_frames", "wire")
    ir = schema_json(schema(Msg("M", F("x", 1, INT))))
    assert ir["effective"] == {**DEFAULTS, "max_frames": None}
    with pytest.raises(ValueError, match="the file: effective names wire option 'max_frames', "
                                         "which this taut's Python runtime does not implement"):
        schema_from_json(ir)


def test_load_reads_an_effective_codegen_option_the_runtime_need_not_implement(monkeypatch):
    _register(monkeypatch, "gen_hint", "codegen")
    s = schema(Msg("M", F("x", 1, INT)))
    ir = schema_json(s)
    assert ir["messages"][0]["effective"] == {**DEFAULTS, "gen_hint": None}
    assert schema_from_json(ir) == s


def test_python_implements_every_registered_wire_option():
    assert PYTHON_WIRE_OPTIONS == {name for name, d in OPTIONS.items() if d.klass == "wire"}


@pytest.mark.parametrize("version", [1, 2])
def test_load_still_refuses_the_retired_missing_ok_key(version):
    ir = json.loads(V1_TEXT) if version == 1 else schema_json(_job_schema())
    ir["messages"][0]["fields"][0]["missing_ok"] = True
    with pytest.raises(ValueError, match="Job.id: the IR key 'missing_ok' is retired"):
        schema_from_json(ir)


# --- the committed IR files -------------------------------------------------------------------

_COMMITTED = [
    pytest.param(build.IR_PATH, build.IR_JSON_PATH, id="griplab"),
    pytest.param(glade_build.IR_PATH, glade_build.IR_JSON_PATH, id="glade"),
    pytest.param(resext_build.IR_PATH, resext_build.IR_JSON_PATH, id="resext"),
    pytest.param(TASKS / "tasks.taut.py", TASKS / "tasks.ir.json", id="tasks"),
]


@pytest.mark.parametrize("source, committed", _COMMITTED)
def test_each_committed_ir_is_a_current_version_2_export(source, committed):
    s = load_schema(source)
    text = committed.read_text()
    assert text == json.dumps(schema_json(s), indent=2) + "\n", f"{committed.name} is stale"
    assert json.loads(text)["version"] == 2
    assert schema_from_json(json.loads(text)) == s


@pytest.mark.parametrize("source, committed", _COMMITTED)
def test_each_committed_ir_still_loads_as_version_1(source, committed):
    back = schema_from_json(_as_version_1(json.loads(committed.read_text())))
    assert back == load_schema(source)   # none declares an option
    assert effective_map(back) == DEFAULTS
