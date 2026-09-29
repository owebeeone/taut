import dataclasses

import pytest

from taut.ir import options
from taut.ir.dsl import (
    BYTES, INT, MISSING_OK, STR, Enum, F, List, Msg, Params, Ref, method, option, schema, service,
)
from taut.ir.model import EnumDef, EnumRef, FieldDef, MessageDef, MethodDef, ServiceDef
from taut.ir.options import OptionValue
from taut.ir.validate import validate
from taut.ir.export import schema_json
from taut.ir.load import schema_from_json


def test_keyword_message_and_fields_match_legacy_shape():
    legacy = schema(
        Msg(
            "WorkspaceRef",
            F("root", 1, STR, optional=True),
            F("workspace_id", 2, STR, optional=True),
        )
    )

    preferred = schema(
        WorkspaceRef=Msg(
            root=F(1, STR, optional=True),
            workspace_id=F(2, STR, optional=True),
        )
    )

    assert preferred == legacy
    assert validate(preferred) == []


def test_missing_ok_is_a_third_value_of_optional():
    s = schema(Msg("M", F("new", 1, STR, optional=MISSING_OK)))
    field = s.messages["M"].fields[0]
    assert field.optional == MISSING_OK
    assert field.optional  # still truthy: the field may be null
    assert not hasattr(field, "missing_ok")
    assert validate(s) == []


def test_optional_refuses_any_other_value_and_the_retired_keyword():
    for bad in ("maybe", 1, 0, None):
        with pytest.raises(TypeError):
            F("x", 1, STR, optional=bad)
    with pytest.raises(TypeError):
        F("x", 1, STR, optional=True, missing_ok=True)


def test_validate_refuses_an_optional_value_built_outside_the_dsl():
    s = schema(Msg("M", F("x", 1, STR, optional=True)))
    m = s.messages["M"]
    broken = dataclasses.replace(m, fields=(dataclasses.replace(m.fields[0], optional="maybe"),))
    assert validate(dataclasses.replace(s, messages={"M": broken})) == [
        "M.x: optional must be False, True or MISSING_OK, not 'maybe'"
    ]


def test_missing_ok_exports_as_a_value_of_optional_and_round_trips():
    baseline = schema_json(schema(Msg("M", F("old", 1, STR, optional=True))))
    opted = schema_json(schema(Msg("M", F("new", 1, STR, optional=MISSING_OK))))
    assert baseline["messages"][0]["fields"][0]["optional"] is True
    field = opted["messages"][0]["fields"][0]
    assert field["optional"] == "missing_ok"
    assert "missing_ok" not in field
    assert schema_from_json(opted).messages["M"].fields[0].optional == MISSING_OK


def test_load_refuses_the_retired_missing_ok_key():
    ir = schema_json(schema(Msg("M", F("new", 1, STR, optional=True))))
    ir["messages"][0]["fields"][0]["missing_ok"] = True
    with pytest.raises(ValueError, match="M.new: the IR key 'missing_ok' is retired"):
        schema_from_json(ir)


def test_keyword_enum_matches_legacy_shape():
    legacy = schema(Enum("ActionKind", create_repo=0, materialize=1))
    preferred = schema(ActionKind=Enum(create_repo=0, materialize=1))

    assert preferred == legacy
    assert validate(preferred) == []


def test_legacy_enum_string_syntax_remains_escape_hatch():
    s = schema(Enum("wire-status", ok=0, failed=1))

    assert s.enums["wire-status"].name == "wire-status"


def test_legacy_string_syntax_remains_escape_hatch_for_keyword_names():
    s = schema(
        Msg("Head", F("origin", 1, STR)),
        Msg("Subscribe", F("from", 1, List(Ref("Head")), optional=True)),
    )

    assert validate(s) == []
    assert s.messages["Subscribe"].fields[0].name == "from"


def test_ref_attribute_matches_string_form():
    assert Ref.ResponseEnvelope == Ref("ResponseEnvelope")
    assert Ref.ResponseEnvelope.name == "ResponseEnvelope"


@pytest.mark.parametrize("bad_name", ["bad-name", "class"])
def test_ref_attribute_names_must_be_identifiers(bad_name):
    with pytest.raises(ValueError, match="identifier"):
        getattr(Ref, bad_name)


@pytest.mark.parametrize("escape_name", ["bad-name", "class"])
def test_ref_string_syntax_remains_escape_hatch(escape_name):
    assert Ref(escape_name).name == escape_name


def test_params_keyword_form_matches_legacy_tuple_shape():
    legacy = service(
        "S",
        method(
            "create_repo",
            role="in",
            params=(("request", Ref.CreateRepoRequest), ("session", Ref.RepoSession)),
            out=Ref.CreateRepoResponse,
        ),
    )
    preferred = service(
        "S",
        method(
            "create_repo",
            role="in",
            params=Params(request=Ref.CreateRepoRequest, session=Ref.RepoSession),
            out=Ref.CreateRepoResponse,
        ),
    )

    assert Params(request=Ref.CreateRepoRequest, session=Ref.RepoSession) == (
        ("request", Ref.CreateRepoRequest),
        ("session", Ref.RepoSession),
    )
    assert preferred == legacy


@pytest.mark.parametrize("bad_name", ["bad-name", "class"])
def test_params_keyword_names_must_be_identifiers(bad_name):
    with pytest.raises(ValueError, match="identifier"):
        Params(**{bad_name: STR})


def test_legacy_tuple_params_remain_escape_hatch_for_keyword_names():
    m = method("subscribe", role="out", params=(("from", Ref.Head),), out=Ref.Head)

    assert m.params == (("from", Ref.Head),)


def test_anonymous_message_must_be_named_by_schema_keyword():
    with pytest.raises(TypeError, match="anonymous message"):
        schema(Msg(root=F(1, STR)))


def test_anonymous_enum_must_be_named_by_schema_keyword():
    with pytest.raises(TypeError, match="anonymous enum"):
        schema(Enum(open=0, done=1))


def test_anonymous_field_must_be_named_by_msg_keyword():
    with pytest.raises(TypeError, match="anonymous field"):
        Msg("A", F(1, STR))


def test_keyword_field_name_mismatch_is_rejected():
    with pytest.raises(TypeError, match="field name mismatch"):
        Msg("A", root=F("other", 1, STR))


def test_keyword_schema_name_mismatch_is_rejected():
    with pytest.raises(TypeError, match="declaration name mismatch"):
        schema(WorkspaceRef=Msg("Other", F("root", 1, STR)))


def test_keyword_enum_name_mismatch_is_rejected():
    with pytest.raises(TypeError, match="declaration name mismatch"):
        schema(ActionKind=Enum("Other", create_repo=0))


@pytest.mark.parametrize("bad_name", ["bad-name", "class"])
def test_keyword_declaration_names_must_be_identifiers(bad_name):
    with pytest.raises(ValueError, match="identifier"):
        schema(**{bad_name: Msg(root=F(1, STR))})


@pytest.mark.parametrize("bad_name", ["bad-name", "class"])
def test_keyword_field_names_must_be_identifiers(bad_name):
    with pytest.raises(ValueError, match="identifier"):
        Msg("A", **{bad_name: F(1, STR)})


# --- option values (TautOptions.md OPT-L2) ---------------------------------------------------

def test_option_is_re_exported_by_the_dsl():
    assert option is options.option


def test_option_values_at_file_message_field_and_enum_level():
    # A wrong level (max_depth on a field, max_encoded_len on an enum) is validate's to refuse.
    s = schema(
        option.max_depth(16),
        Enum("Kind", option.max_encoded_len(3), a=0),
        Msg("Tree", F("children", 1, List(Ref("Tree")), option.max_depth(5)), option.max_depth(64)),
        Msg("Plain", F("x", 1, INT)),
        option.max_encoded_len(1024),
    )
    assert s.options == {"max_depth": 16, "max_encoded_len": 1024}
    assert s.enums["Kind"].options == {"max_encoded_len": 3}
    assert s.enums["Kind"].members == {"a": 0}
    assert s.messages["Tree"].options == {"max_depth": 64}
    assert s.messages["Tree"].fields[0].options == {"max_depth": 5}
    assert s.messages["Plain"].options == {}
    assert s.messages["Plain"].fields[0].options == {}


def test_the_owner_syntax_example_builds():
    # TautOptions.md §0, less its later field option: a message's option may precede its fields.
    s = schema(
        option.max_depth(16),
        Enum("FrameType", data=0, ctl=1),
        Msg("Tree",
            option.max_depth(64),
            F("children", 1, List(Ref("Tree")))),
        Msg("Head",
            F("origin", 1, STR),
            F("hash", 3, BYTES)),
    )
    assert s.options == {"max_depth": 16}
    assert s.messages["Tree"].options == {"max_depth": 64}
    assert [f.name for f in s.messages["Tree"].fields] == ["children"]
    assert s.messages["Head"].options == {}


def test_option_values_survive_the_keyword_forms():
    s = schema(
        Kind=Enum(option.max_depth(3), a=0, b=1),
        Tree=Msg(option.max_depth(64), children=F(1, List(Ref.Tree), option.max_encoded_len(7))),
    )
    assert s.enums["Kind"].options == {"max_depth": 3}
    assert s.enums["Kind"].members == {"a": 0, "b": 1}
    assert s.messages["Tree"].options == {"max_depth": 64}
    assert s.messages["Tree"].fields[0].options == {"max_encoded_len": 7}


def test_enum_resolution_keeps_field_and_message_options():
    s = schema(
        Enum("Kind", a=0),
        Msg("M", option.max_depth(4), F("k", 1, Ref("Kind"), option.max_depth(2))),
    )
    field = s.messages["M"].fields[0]
    assert field.type == EnumRef("Kind")
    assert field.options == {"max_depth": 2}
    assert s.messages["M"].options == {"max_depth": 4}


def _sentinels(cls, **fixed):
    """An instance of `cls` whose every attribute not in `fixed` holds a distinct sentinel."""
    values = {f.name: fixed.get(f.name, object()) for f in dataclasses.fields(cls)}
    return cls(**values), values


def _assert_carried(rebuilt, values, *, rebuilt_attrs):
    for name, value in values.items():
        if name not in rebuilt_attrs:
            assert getattr(rebuilt, name) is value, f"{type(rebuilt).__name__}.{name} was dropped"


def test_every_rebuild_carries_every_attribute():
    # _field_named, through Msg(x=F(...))
    field, fvalues = _sentinels(FieldDef, name="")
    _assert_carried(Msg("M", x=field).fields[0], fvalues, rebuilt_attrs={"name"})
    # schema()'s own field and message rebuilds
    field, fvalues = _sentinels(FieldDef, name="x")
    message, mvalues = _sentinels(MessageDef, name="M", fields=(field,))
    s = schema(message)
    _assert_carried(s.messages["M"], mvalues, rebuilt_attrs={"fields"})
    _assert_carried(s.messages["M"].fields[0], fvalues, rebuilt_attrs=set())
    # _message_named, through schema(M=Msg(...))
    message, mvalues = _sentinels(MessageDef, name="", fields=())
    _assert_carried(schema(M=message).messages["M"], mvalues, rebuilt_attrs={"name", "fields"})
    # _enum_named, through schema(E=Enum(...)); members is copied
    enum, evalues = _sentinels(EnumDef, name="", members={"a": 0})
    rebuilt = schema(E=enum).enums["E"]
    _assert_carried(rebuilt, evalues, rebuilt_attrs={"name", "members"})
    assert rebuilt.members == {"a": 0}
    # schema()'s service rebuild and _resolve_method
    m, method_values = _sentinels(MethodDef, out=(), params=())
    svc, svc_values = _sentinels(ServiceDef, name="S", methods=(m,))
    s = schema(svc)
    _assert_carried(s.services["S"], svc_values, rebuilt_attrs={"methods"})
    _assert_carried(s.services["S"].methods[0], method_values, rebuilt_attrs={"out", "params"})


@pytest.mark.parametrize(
    "build",
    [
        lambda: schema(option.max_depth(1), Msg("M", F("x", 1, INT)), option.max_depth(2)),
        lambda: Msg("M", option.max_depth(1), F("x", 1, INT), option.max_depth(2)),
        lambda: F("x", 1, INT, option.max_depth(1), option.max_depth(1)),
        lambda: Enum("E", option.max_depth(1), option.max_depth(2), a=0),
    ],
    ids=["file", "message", "field", "enum"],
)
def test_the_same_option_twice_at_one_level_raises(build):
    with pytest.raises(TypeError, match="max_depth.*twice"):
        build()


def test_distinct_options_or_one_option_at_several_levels_are_fine():
    s = schema(
        option.max_depth(16), option.max_encoded_len(1024),
        Msg("M", option.max_depth(8), F("x", 1, INT, option.max_depth(8))),
    )
    assert s.options == {"max_depth": 16, "max_encoded_len": 1024}
    assert s.messages["M"].options == {"max_depth": 8}


@pytest.mark.parametrize(
    "stray",
    [42, "M", None, F("x", 1, INT), (Msg("A", F("x", 1, INT)),)],
    ids=["int", "str", "None", "field", "tuple"],
)
def test_schema_refuses_a_positional_that_is_neither_a_declaration_nor_an_option(stray):
    with pytest.raises(TypeError, match="schema"):
        schema(Msg("M", F("x", 1, INT)), stray)


@pytest.mark.parametrize(
    "build",
    [
        lambda: F("x", option.max_depth(1), 1, INT),
        lambda: F(option.max_depth(1), 1, INT),
        lambda: F("x", 1, option.max_depth(1)),
        lambda: F("x", 1, INT, option.max_depth(1), "junk"),
        lambda: Msg("M", F("x", 1, INT), 42),
        lambda: Msg(option.max_depth(1), "M", F("x", 1, INT)),
        lambda: Enum("E", "junk", a=0),
        lambda: Enum(option.max_depth(1), "E", a=0),
    ],
    ids=["F-before-tag", "F-first", "F-as-type", "F-junk-after", "Msg-junk", "Msg-before-name",
         "Enum-junk", "Enum-before-name"],
)
def test_option_values_follow_the_fixed_positionals(build):
    with pytest.raises(TypeError):
        build()


def test_an_option_value_is_not_a_keyword():
    # a keyword names a field or a declaration (TautOptions.md §0), so it cannot carry an option
    with pytest.raises(TypeError, match="must be declared with F"):
        Msg("M", max_depth=option.max_depth(3))
    with pytest.raises(TypeError, match="must be declared with"):
        schema(max_depth=option.max_depth(3))


def test_the_dsl_refuses_a_hand_built_value_its_constructor_would_refuse():
    with pytest.raises(KeyError, match="nope"):
        schema(OptionValue("nope", 1))
    with pytest.raises(TypeError, match="max_depth"):
        Msg("M", OptionValue("max_depth", True))
    with pytest.raises(ValueError, match="max_depth"):
        F("x", 1, INT, OptionValue("max_depth", 0))
