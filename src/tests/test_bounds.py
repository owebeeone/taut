"""Checked decode's bounds through Python's API, the reference the other eight mirror (D26:
TautCheckedDecode.md §3, CD-E4, CD-E5; D27: TautOptions.md OPT-D4, OPT-L6, G1, G3).

`ROWS` are §4.4's B1-B30 as `bounds.vectors.json` holds them, written by
`corpus/parity/gen_vectors.py` (CD-C2), each with the bounds it is decoded under: raw rows
through `cbor.loads` with the limits their call passes, typed rows through `codec.decode` on
CD-C1's six messages in the parity fixture, `FIXTURE`. The gate replays the same rows in every
language; the raw decoder's own contract is in test_cbor.py.
"""

from __future__ import annotations

import ast
import inspect
import random
from pathlib import Path

import pytest

from taut import ext
from taut.corpus import parity
from taut.ir import options
from taut.ir.dsl import INT, STR, Enum, F, List, Msg, Ref, extension, option, schema
from taut.ir.model import EnumRef, ListOf, MsgRef, Scalar
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec, jsoncodec

# `ir/parity_int.taut.py`, which holds IntBox and CD-C1's six. The file declares no bound, so
# IntBox, Holds64 and HoldsSized8 resolve to the defaults: depth 32 and no length bound.
FIXTURE = parity.parity_schema()

RAW = "raw_decode"
ACCEPT = {"accept": True}
TRUNCATED = {"tag": "Truncated"}


def too_deep(limit: int) -> dict:
    return {"tag": "TooDeep", "limit": limit}


def too_large(length: int, limit: int) -> dict:
    return {"tag": "TooLarge", "len": length, "limit": limit}


ROWS = parity.bounds_rows()
TYPED = [row for row in ROWS if row["stage"] != RAW]


def _ids(rows: list[dict]) -> list[str]:
    return [f"{row['why'].partition(':')[0]}-{row['name']}" for row in rows]


def _applied(row: dict) -> tuple[int, int | None]:
    """A row's bounds as `(max_depth, max_encoded_len)`, None for no length bound."""
    return row["bounds"]["max_depth"], row["bounds"].get("max_encoded_len")


def _outcome(call) -> dict:
    """ACCEPT, or the DecodeError as `{"tag": ..., <payload>}`; anything else propagates."""
    try:
        call()
    except cbor.DecodeError as exc:
        assert type(exc) is cbor.DecodeError
        return {"tag": exc.tag, **exc.payload}
    return ACCEPT


def test_the_fixture_declares_cd_c1s_six():
    assert FIXTURE.options == {}
    assert {name: FIXTURE.messages[name].options for name in (
        "Tree64", "Tree128", "Flat2", "Sized8", "Holds64", "HoldsSized8")} == {
        "Tree64": {"max_depth": 64}, "Tree128": {"max_depth": 128}, "Flat2": {"max_depth": 2},
        "Sized8": {"max_encoded_len": 8}, "Holds64": {}, "HoldsSized8": {}}


def test_rows_are_b1_to_b30():
    assert [row["why"].partition(":")[0] for row in ROWS] == [f"B{i}" for i in range(1, 31)]
    assert len({row["name"] for row in ROWS}) == len(ROWS)
    assert all(row["lead"] is True for row in ROWS)


@pytest.mark.parametrize("row", ROWS, ids=_ids(ROWS))
def test_b_row(row):
    data, limits, expect = parity.row_bytes(row), row.get("limits", {}), row["expect"]
    if row["stage"] == RAW:
        # A raw row's bounds are what its call passes, the depth capped at 128, else the defaults.
        depth = min(limits.get("max_depth", cbor.DEFAULT_MAX_DEPTH), cbor.MAX_DEPTH_CEILING)
        assert (depth, limits.get("max_encoded_len")) == _applied(row)
        decoded = []
        assert _outcome(lambda: decoded.append(cbor.loads(data, **limits))) == expect
        if decoded:
            assert cbor.dumps(decoded[0]) == data                   # and re-encodes to its bytes
    else:
        # A typed row's are what the resolver gives its message (CD-C4), and no call passes any.
        message = row["schema"]
        assert not limits and codec.bounds(FIXTURE, MsgRef(message)) == _applied(row)
        decoded = []
        assert _outcome(lambda: decoded.append(codec.decode(FIXTURE, message, data))) == expect
        if decoded:
            assert codec.encode(FIXTURE, message, decoded[0]) == data


@pytest.mark.parametrize("row", TYPED, ids=_ids(TYPED))
def test_the_json_profile_applies_the_same_bounds(row):
    data = parity.row_bytes(row)
    assert _outcome(lambda: jsoncodec.cbor_to_json(FIXTURE, row["schema"], data)) == row["expect"]


def test_raw_decoder_constants_equal_the_options():
    assert cbor.DEFAULT_MAX_DEPTH == options.DEFAULT_MAX_DEPTH == 32
    assert cbor.MAX_DEPTH_CEILING == options.MAX_DEPTH_CEILING == 128
    assert options.OPTIONS["max_depth"].default == cbor.DEFAULT_MAX_DEPTH
    assert options.OPTIONS["max_encoded_len"].default is None


def test_raw_decoder_imports_nothing_from_taut():
    tree = ast.parse(Path(cbor.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0 and not (node.module or "").startswith("taut"), ast.dump(node)
        elif isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] != "taut" for alias in node.names), ast.dump(node)


def test_typed_decode_takes_no_bound():
    # CD-B3: no call can raise or lower its root's bounds.
    assert list(inspect.signature(codec.decode).parameters) == ["schema", "message", "data"]
    assert list(inspect.signature(codec.decode_ref).parameters) == ["schema", "tref", "data"]
    assert list(inspect.signature(jsoncodec.cbor_to_json).parameters) == [
        "schema", "message", "data", "indent"]


@pytest.mark.parametrize("message, opener, bound", [
    ("Tree64", "a10181", 64), ("Tree128", "a10181", 128), ("Holds64", "a10181", 32),
    ("IntBox", "81", 32),
])
def test_typed_decode_of_deep_input_is_too_deep_not_recursion_error(message, opener, bound):
    data = bytes.fromhex(opener * 100_000 + "80")
    assert _outcome(lambda: codec.decode(FIXTURE, message, data)) == too_deep(bound)


# --- the root rule (OPT-D4): one root per call, and a root that is not a message -------------

# A file that declares both bounds, a message that overrides one, and one that inherits both.
FILED = schema(
    option.max_depth(3), option.max_encoded_len(16),
    Enum("Mode", ok=0, alt=1),
    Msg("Tree", F("kids", 1, List(Ref("Tree"))), option.max_depth(64), next_id=2),
    Msg("Plain", F("v", 1, List(INT)), next_id=2),
)


def test_bounds_resolve_per_root():
    assert codec.bounds(FILED, MsgRef("Tree")) == (64, 16)       # its own depth, the file's length
    assert codec.bounds(FILED, MsgRef("Plain")) == (3, 16)       # the file's
    assert codec.bounds(FILED, ListOf(MsgRef("Tree"))) == (3, 16)    # not a message: the file's
    assert codec.bounds(FILED, EnumRef("Mode")) == (3, 16)
    assert codec.bounds(FILED, Scalar("bytes")) == (3, 16)
    assert codec.bounds(FIXTURE, ListOf(MsgRef("Tree64"))) == (32, None)   # else the defaults
    for name in FIXTURE.messages:
        assert codec.bounds(FIXTURE, MsgRef(name)) == (
            options.effective(FIXTURE, "max_depth", message=name),
            options.effective(FIXTURE, "max_encoded_len", message=name),
        )


def test_a_message_root_applies_its_own_bounds():
    trees = bytes.fromhex("a10181" + "a10180")                   # Tree{[Tree{[]}]}: depth 4
    assert codec.decode(FILED, "Tree", trees) == {"kids": [{"kids": []}]}
    deep = bytes.fromhex("a10181818100")                          # depth 4, before WrongType{int}
    assert _outcome(lambda: codec.decode(FILED, "Plain", deep)) == too_deep(3)
    at_len = bytes.fromhex("a1018d" + "00" * 13)                  # 16 bytes
    assert codec.decode(FILED, "Plain", at_len) == {"v": [0] * 13}
    over_len = bytes.fromhex("a1018e" + "00" * 14)                # 17 bytes
    assert _outcome(lambda: codec.decode(FILED, "Plain", over_len)) == too_large(17, 16)
    assert _outcome(lambda: codec.decode(FILED, "Tree", over_len)) == too_large(17, 16)


def test_a_root_that_is_not_a_message_uses_the_files_bounds():
    one = bytes.fromhex("81" + "a10180")                          # [Tree{[]}]: depth 3
    assert codec.decode_ref(FILED, ListOf(MsgRef("Tree")), one) == [{"kids": []}]
    two = bytes.fromhex("81" + "a10181" + "a10180")               # depth 5, though Tree says 64
    assert _outcome(lambda: codec.decode_ref(FILED, ListOf(MsgRef("Tree")), two)) == too_deep(3)
    assert codec.decode_ref(FILED, MsgRef("Tree"), bytes.fromhex("a10181a10180")) == {
        "kids": [{"kids": []}]}
    assert codec.decode_ref(FILED, Scalar("bytes"), bytes.fromhex("4f" + "00" * 15)) == bytes(15)
    over = bytes.fromhex("50" + "00" * 16)
    assert _outcome(lambda: codec.decode_ref(FILED, Scalar("bytes"), over)) == too_large(17, 16)
    assert codec.decode_ref(FILED, EnumRef("Mode"), b"\x01") == "alt"
    assert _outcome(lambda: codec.decode_ref(FILED, EnumRef("Mode"), b"\x02")) == {
        "tag": "UnknownEnum", "enum": "Mode", "value": 2}


def test_decode_struct_is_the_unchanged_two_step_reader():
    # G1: the caller decodes the bytes, then the tree; decode_struct applies no bound of its own.
    data = bytes.fromhex("a10181" * 40 + "a10180")                # a Tree64 82 containers deep
    assert _outcome(lambda: codec.decode(FIXTURE, "Tree64", data)) == too_deep(64)
    assert _outcome(lambda: cbor.loads(data)) == too_deep(32)     # the raw defaults
    native = codec.decode_struct(FIXTURE, "Tree64", cbor.loads(data, max_depth=128), strict=True)
    assert codec.encode(FIXTURE, "Tree64", native) == data
    assert codec.decode_struct(FIXTURE, "IntBox", {1: 5}) == {"n": 5, "by_id": None}   # lenient


# --- the extension helpers (CD-E4; TautOptions.md G3) ----------------------------------------

EXT_TAG = BAND_START + 1
# The file's own bounds are tight; a helper cannot name the host's root, so it applies neither.
EXT = schema(
    option.max_depth(2), option.max_encoded_len(8),
    Msg("Host", F("id", 1, INT), next_id=2),
    Msg("Decision", F("backend", 1, STR), F("hops", 2, INT), next_id=3),
    extension("Decision", tag=EXT_TAG),
)
DECISION = {"backend": "b7", "hops": 1}
HOST = codec.encode(EXT, "Host", {"id": 1})
STRAPPED = cbor.dumps({1: 1, EXT_TAG: {1: "b7", 2: 1}})


def _helpers(host: bytes) -> dict:
    return {
        "ext_get": lambda: ext.ext_get(EXT, host, "Decision", EXT_TAG),
        "ext_set": lambda: ext.ext_set(EXT, host, "Decision", EXT_TAG, DECISION),
        "ext_clear": lambda: ext.ext_clear(host, EXT_TAG),
    }


def test_extension_helpers_still_work():
    assert ext.ext_set(EXT, HOST, "Decision", EXT_TAG, DECISION) == STRAPPED
    assert ext.ext_get(EXT, STRAPPED, "Decision", EXT_TAG) == DECISION
    assert ext.ext_get(EXT, HOST, "Decision", EXT_TAG) is None
    assert ext.ext_clear(STRAPPED, EXT_TAG) == HOST
    assert ext.ext_clear(HOST, EXT_TAG) == HOST


@pytest.mark.parametrize("host", ["00", "20", "40", "6161", "80", "820102", "f4", "f6", "f93c00"])
def test_extension_helpers_refuse_a_host_that_is_not_a_map(host):
    for name, call in _helpers(bytes.fromhex(host)).items():
        assert _outcome(call) == {"tag": "WrongType", "expected": "map"}, name


@pytest.mark.parametrize("host, expect", [
    ("", TRUNCATED), ("a1", TRUNCATED), ("a101", TRUNCATED),
    ("c0", {"tag": "UnsupportedMajor", "major": 6}), ("a0a0", {"tag": "TrailingBytes"}),
    ("a1a00000", {"tag": "NonIntegerMapKey"}), ("a2010101", {"tag": "DuplicateMapKey", "key": 1}),
])
def test_extension_helpers_refuse_a_malformed_host_with_its_decode_error(host, expect):
    for name, call in _helpers(bytes.fromhex(host)).items():
        assert _outcome(call) == expect, name


def _host(arrays: int) -> bytes:
    """A host map whose unknown field 7 holds `arrays` nested arrays: 1 + `arrays` deep."""
    return bytes.fromhex("a107" + "81" * (arrays - 1) + "80")


def test_a_host_is_read_at_the_depth_ceiling():
    at_ceiling = _host(127)                                       # 128 deep, the file declares 2
    assert ext.ext_get(EXT, at_ceiling, "Decision", EXT_TAG) is None
    assert ext.ext_clear(at_ceiling, EXT_TAG) == at_ceiling
    strapped = ext.ext_set(EXT, at_ceiling, "Decision", EXT_TAG, DECISION)
    assert ext.ext_get(EXT, strapped, "Decision", EXT_TAG) == DECISION
    for host in (_host(128), _host(100_000)):                     # 129 deep, and far beyond
        for name, call in _helpers(host).items():
            assert _outcome(call) == too_deep(128), name


def test_a_host_is_read_with_no_length_bound():
    big = cbor.dumps({1: 1, 7: b"x" * 100_000})                   # the file declares 8 bytes
    strapped = ext.ext_set(EXT, big, "Decision", EXT_TAG, DECISION)
    assert ext.ext_get(EXT, strapped, "Decision", EXT_TAG) == DECISION
    assert ext.ext_clear(strapped, EXT_TAG) == big


@pytest.mark.parametrize("value, expect", [
    ({1: "b7"}, {"tag": "MissingKey", "key": 2}),                 # lenient decode read hops as None
    ({2: 1}, {"tag": "MissingKey", "key": 1}),
    ({1: 7, 2: 1}, {"tag": "WrongType", "expected": "text"}),
    ({1: "b7", 2: None}, {"tag": "WrongType", "expected": "int"}),
    (5, {"tag": "WrongType", "expected": "map"}),
])
def test_the_extension_is_read_strictly(value, expect):
    host = cbor.dumps({1: 1, EXT_TAG: value})
    assert _outcome(lambda: ext.ext_get(EXT, host, "Decision", EXT_TAG)) == expect


_PROBES = bytes.fromhex("00011718191a1b1c1f20384041585b5f6061787b7f8081989b9fa0a1b8bbbfc0"
                        "dcf4f5f6f7f8f9fafbfcff")


def test_extension_helpers_let_nothing_but_decode_error_escape():
    rng = random.Random(0xC1)
    hosts = [STRAPPED[:i] for i in range(len(STRAPPED))]         # every proper prefix
    hosts += [STRAPPED[:i] + bytes([b]) + STRAPPED[i + 1:]
              for i in range(len(STRAPPED)) for b in _PROBES]   # every byte, probed
    hosts += [bytes(rng.randrange(256) for _ in range(rng.randrange(1, 16))) for _ in range(2000)]
    for host in hosts:
        for name, call in _helpers(host).items():
            try:
                call()
            except cbor.DecodeError:
                pass
            except Exception as exc:  # noqa: BLE001 — the property under test
                pytest.fail(f"{name}({host.hex()}) raised {type(exc).__name__}: {exc}")
