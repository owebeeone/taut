import pytest

from taut.ir.dsl import INT, STR, Enum, F, List, Msg, Params, Ref, method, schema, service
from taut.ir.validate import validate


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
