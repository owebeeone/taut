"""The governed parity gate (TautCodecParityPlan.md §8 P1; TautCheckedDecode.md CD-C1-C4, §5.4).

Which targets and variants are gated and which allowlisted is data, in
corpus/parity/allowlist.json; no test here pins a status. The tests check that the
artifacts validate (bounds.vectors.json's segments, `len`, `limits`, `bounds` and header
among them), that the comparator and the report parser enforce the runner protocol
(an accept row and its re-encoding, the expectation for a codec that drops unknown fields,
payloads compared as strings, a row never reported, a runner exiting non-zero, a build that
fails, the `#constants` line and a from_cbor row's resolved bounds), that Python's harness
speaks it, that a target's runner is found by module and runs each of its variants, and,
end-to-end with whatever toolchains are present, that the gate's governance is clean.
"""

import copy
import dataclasses
import importlib
import importlib.util
import inspect
import json
import keyword
import os
import sys
import textwrap

import pytest

import taut.corpus
from taut.cli import main
from taut.corpus import parity, toolchains
from taut.gen import kotlin as kotlin_gen
from taut.gen import scaffold
from taut.gen import swift as swift_gen
from taut.ir import options
from taut.ir.dsl import STR, F, Msg, schema as mk
from taut.ir.model import MISSING_OK, EnumRef, ListOf, MapOf, MsgRef, Scalar
from taut.wire import cbor, codec

INT_ROWS = 11
MALFORMED_ROWS = 47
BOUNDS_ROWS = 30
ALL_ROWS = INT_ROWS + MALFORMED_ROWS + BOUNDS_ROWS
GENERATED = ("rust", "js", "cpp", "swift", "go", "kotlin", "java")
CONSTANTS_LINE = f"{parity.CONSTANTS}\tdefault_max_depth=32;max_depth_ceiling=128"


def _row(name):
    return next(r for r in parity.decode_rows() if r["name"] == name)


def _passing_lines(target="js"):
    """The report `target`'s runner prints when every row behaves as the corpus expects of it,
    in C3's protocol: its constants, and each from_cbor row's resolved bounds."""
    schema = parity.parity_schema()
    lines = [CONSTANTS_LINE, *(f"{row['name']}\t{parity.PASS}\t" for row in parity.int_rows())]
    for row in parity.decode_rows():
        expect = parity.row_expect(target, row)
        if expect.get("accept"):
            line = f"{row['name']}\t{parity.OK}\t{parity.expected_reencoding(row, expect)}"
        else:
            line = f"{row['name']}\t{parity.ERR}\t{parity.format_error(expect['tag'], expect)}"
        if row["stage"] == "from_cbor":
            line += "\t" + parity.format_bounds(parity.decoded_under(schema, row))
        lines.append(line)
    return lines


def _replace(lines, name, line=None):
    """`lines` with the line reporting row `name` replaced by `line`, or left out for None."""
    out = []
    for old in lines:
        if old.split("\t")[0] != name:
            out.append(old)
        elif line is not None:
            out.append(line)
    return out


# --- artifacts ------------------------------------------------------------------

def test_the_three_artifacts_validate():
    assert parity.validate_int_vectors() == INT_ROWS
    assert parity.validate_malformed_vectors() == MALFORMED_ROWS
    assert parity.validate_bounds_vectors() == BOUNDS_ROWS


def test_malformed_rows_expect_a_known_tag_or_accept(tmp_path):
    data = json.loads(parity.MALFORMED_VECTORS.read_text())
    accept = {r["name"] for r in data["vectors"] if "accept" in r["expect"]}
    assert {"map-key-2^53", "optional-present-null", "missing-ok-absent", "text-leading-bom",
            "shapes-filled", "shapes-sparse", "shapes-missing-ok-absent",
            "map-str-key-order", "unknown-field-round-trip", "unknown-field-beside-known",
            "names-round-trip"} <= accept                                           # M8, M15, M16
    path = tmp_path / "malformed.vectors.json"
    data["vectors"][0]["expect"] = {"accept": True, "reencode": "a0"}  # a re-encoding may be named
    path.write_text(json.dumps(data))
    assert parity.validate_malformed_vectors(path) == MALFORMED_ROWS
    for bad in ({"accept": False}, {"accept": True, "tag": "Truncated"},
                {"accept": True, "reencode": "zz"}, {"accept": True, "reencode": 160},
                {"tag": "Malformed"}, {"tag": "MissingKey", "field": 1},
                {"tag": "Truncated", "reencode": "a0"}):
        data["vectors"][0]["expect"] = bad
        path.write_text(json.dumps(data))
        with pytest.raises(parity.ParityValidationError):
            parity.validate_malformed_vectors(path)


def test_a_from_wire_row_never_accepts(tmp_path):
    data = json.loads(parity.MALFORMED_VECTORS.read_text())
    row = next(r for r in data["vectors"] if r["stage"] == "from_wire")
    row["expect"] = {"accept": True}
    path = tmp_path / "malformed.vectors.json"
    path.write_text(json.dumps(data))
    with pytest.raises(parity.ParityValidationError, match="never accepts"):
        parity.validate_malformed_vectors(path)


def test_expect_dropping_is_a_from_cbor_rows_second_expectation(tmp_path):
    """`expect_dropping` names what a codec that drops unknown fields must do (question 10):
    well-formed like `expect`, only on a from_cbor row, and never a copy of `expect`."""
    data = json.loads(parity.MALFORMED_VECTORS.read_text())
    path = tmp_path / "malformed.vectors.json"
    index = next(i for i, r in enumerate(data["vectors"]) if r["name"] == "unknown-field-round-trip")
    raw = next(i for i, r in enumerate(data["vectors"]) if r["stage"] == "raw_decode")
    assert data["vectors"][index]["expect_dropping"] == {"accept": True, "reencode": "a0"}
    for where, bad, match in ((index, {"accept": False}, "accept row"),
                              (index, {"tag": "Malformed"}, "unknown decode tag"),
                              (index, {"accept": True}, "equals expect"),
                              (raw, {"accept": True, "reencode": "a0"}, "from_cbor")):
        rows = json.loads(parity.MALFORMED_VECTORS.read_text())
        rows["vectors"][where]["expect_dropping"] = bad
        path.write_text(json.dumps(rows))
        with pytest.raises(parity.ParityValidationError, match=match):
            parity.validate_malformed_vectors(path)


def test_decode_rows_name_the_fixture_messages():
    schema = parity.parity_schema()
    for row in parity.decode_rows():
        if row["stage"] == "from_cbor":
            assert row["schema"] in schema.messages, row["name"]
        if row["stage"] == "from_wire":
            assert row["schema"] in schema.enums, row["name"]
    assert {"OptBox", "Empty", "Late", "Shapes", "Names", "Tree64", "Tree128", "Flat2", "Sized8",
            "Holds64", "HoldsSized8"} <= set(schema.messages)
    assert {row["schema"] for row in parity.bounds_rows() if row["stage"] == "from_cbor"} == {
        "IntBox", "Tree64", "Tree128", "Flat2", "Sized8", "Holds64", "HoldsSized8"}


# --- bounds.vectors.json (CD-C1, CD-C2) ------------------------------------------------

def _bounds_doc():
    return json.loads(parity.BOUNDS_VECTORS.read_text())


def _refused(tmp_path, doc, match):
    path = tmp_path / "bounds.vectors.json"
    path.write_text(json.dumps(doc))
    with pytest.raises(parity.ParityValidationError, match=match):
        parity.validate_bounds_vectors(path)


def _bounds_index(doc, name):
    return next(i for i, row in enumerate(doc["vectors"]) if row["name"] == name)


def test_bounds_rows_are_b1_to_b30_each_leading_with_a_why_and_its_bounds():
    rows = parity.bounds_rows()
    assert [row["why"].partition(":")[0] for row in rows] == [f"B{i}" for i in range(1, 31)]
    assert all(row["lead"] is True and "len" in row and "bounds" in row for row in rows)
    assert {row["stage"] for row in rows} == {"raw_decode", "from_cbor"}
    names = {row["name"] for row in rows}
    assert not names & {row["name"] for row in [*parity.int_rows(), *parity.malformed_rows()]}
    assert {"depth-100000-arrays", "depth-100000-maps"} <= names


def test_the_bounds_header_records_tauts_two_depth_numbers(tmp_path):
    doc = _bounds_doc()
    assert (doc["default_max_depth"], doc["max_depth_ceiling"]) == (
        options.DEFAULT_MAX_DEPTH, options.MAX_DEPTH_CEILING) == (
        cbor.DEFAULT_MAX_DEPTH, cbor.MAX_DEPTH_CEILING) == (32, 128)
    assert parity.expected_constants() == "default_max_depth=32;max_depth_ceiling=128"
    for name, bad in (("default_max_depth", 33), ("max_depth_ceiling", 127), ("default_max_depth", 32.0),
                      ("max_depth_ceiling", None)):
        _refused(tmp_path, {**doc, name: bad}, "but taut's default_max_depth is 32 and its max_depth_ceiling 128")
    _refused(tmp_path, {**doc, "schema_path": "ir/razel.taut.py"}, "is not the fixture int.vectors.json names")


def test_a_row_may_give_its_bytes_as_segments_whose_expansion_is_len(tmp_path):
    b9 = _row("depth-100000-arrays")
    assert b9["bytes"] == [{"repeat": "81", "count": 99999}, "80"] and b9["len"] == 100000
    assert parity.segments(b9) == [("81", 99999), ("80", 1)]
    assert parity.row_bytes(b9) == b"\x81" * 99999 + b"\x80"
    b30 = _row("len-root-decides")
    assert parity.segments(b30) == [("a101a1014a", 1), ("00010203040506070809", 1)]
    assert parity.segments(_row("size-at-limit")) == [("83010203", 1)]
    assert parity.row_bytes(_row("size-empty")) == b""
    with pytest.raises(parity.ParityValidationError, match="expand to 100000 bytes, len is 99999"):
        parity.row_bytes({**b9, "len": 99999})
    doc = _bounds_doc()
    at = _bounds_index(doc, "depth-100000-arrays")
    segment = "a segment is a hex string or"
    for bad, match in (([], "a hex string or a non-empty list of segments"), ({"repeat": "81"}, "a hex string or a"),
                       ("zz", "invalid hex"), (["8"], "invalid hex"),
                       ([{"repeat": "81", "count": 0}], segment), ([{"repeat": "81", "count": True}], segment),
                       ([{"repeat": "", "count": 2}], segment), ([{"repeat": "81"}], segment),
                       ([{"repeat": "81", "count": 2, "x": 1}], segment), ([7], segment)):
        broken = copy.deepcopy(doc)
        broken["vectors"][at]["bytes"] = bad
        _refused(tmp_path, broken, match)
    for bad in (99999, "100000", None):
        broken = copy.deepcopy(doc)
        broken["vectors"][at]["len"] = bad
        _refused(tmp_path, broken, "bytes expand to 100000 bytes, len is")
    broken = copy.deepcopy(doc)
    del broken["vectors"][at]["len"]
    _refused(tmp_path, broken, "missing len")


def test_a_raw_rows_limits_are_what_its_call_passes(tmp_path):
    assert _row("raw-depth-capped")["limits"] == {"max_depth": 1000}
    assert _row("size-empty")["limits"] == {"max_encoded_len": 0}
    assert "limits" not in _row("depth-32-arrays")
    doc = _bounds_doc()
    raw, typed = _bounds_index(doc, "size-over-limit"), _bounds_index(doc, "len-9-declared")
    for bad, match in (({}, "or no limits"), ({"depth": 3}, "or no limits"), ([3], "or no limits"),
                       ({"max_depth": 0}, "max_depth: an int of at least 1"),
                       ({"max_depth": True}, "max_depth: an int of at least 1"),
                       ({"max_encoded_len": -1}, "max_encoded_len: an int of at least 0")):
        broken = copy.deepcopy(doc)
        broken["vectors"][raw]["limits"] = bad
        _refused(tmp_path, broken, match)
    broken = copy.deepcopy(doc)
    broken["vectors"][typed]["limits"] = {"max_encoded_len": 9}
    _refused(tmp_path, broken, "only a raw_decode row has limits")


def test_a_rows_bounds_are_what_it_is_decoded_under(tmp_path):
    schema = parity.parity_schema()
    # A raw row: its limits, the depth capped at 128, else the defaults.
    assert _row("depth-32-arrays")["bounds"] == {"max_depth": 32}
    assert _row("size-over-limit")["bounds"] == {"max_depth": 32, "max_encoded_len": 3}
    assert _row("raw-depth-capped")["bounds"] == {"max_depth": 128}
    # A from_cbor row: its message's effective values, as Python resolves them.
    for name, bounds in (("depth-64-declared", {"max_depth": 64}), ("depth-root-decides", {"max_depth": 32}),
                         ("depth-2-declared", {"max_depth": 2}), ("depth-128-ceiling", {"max_depth": 128}),
                         ("len-8-declared", {"max_depth": 32, "max_encoded_len": 8}),
                         ("len-root-decides", {"max_depth": 32})):
        row = _row(name)
        assert row["bounds"] == bounds == parity.decoded_under(schema, row), name
        assert codec.bounds(schema, MsgRef(row["schema"])) == (bounds["max_depth"], bounds.get("max_encoded_len"))
    doc = _bounds_doc()
    for name, bad in (("depth-32-arrays", {"max_depth": 33}), ("raw-depth-capped", {"max_depth": 1000}),
                      ("size-over-limit", {"max_depth": 32}), ("depth-64-declared", {"max_depth": 32}),
                      ("len-8-declared", {"max_depth": 32}), ("len-root-decides", {"max_depth": 32, "max_encoded_len": 8})):
        broken = copy.deepcopy(doc)
        broken["vectors"][_bounds_index(doc, name)]["bounds"] = bad
        _refused(tmp_path, broken, "but it is decoded under")
    for bad in ({}, {"max_encoded_len": 8}, {"max_depth": "32"}, {"max_depth": 32, "max_encoded_len": None},
                {"max_depth": 32, "depth": 1}, [32]):
        broken = copy.deepcopy(doc)
        broken["vectors"][0]["bounds"] = bad
        _refused(tmp_path, broken, "bounds: max_depth, and max_encoded_len where a length bound applies")
    broken = copy.deepcopy(doc)
    del broken["vectors"][0]["bounds"]
    _refused(tmp_path, broken, "missing bounds")


def test_a_bounds_row_is_raw_or_typed_and_named_apart_from_every_other_row(tmp_path):
    doc = _bounds_doc()
    broken = copy.deepcopy(doc)
    broken["vectors"][0].update(stage="from_wire", schema="Mode")
    _refused(tmp_path, broken, "bad stage")
    broken = copy.deepcopy(doc)
    broken["vectors"][0]["name"] = parity.malformed_rows()[0]["name"]
    _refused(tmp_path, broken, "also name int or malformed rows")
    broken = copy.deepcopy(doc)
    broken["vectors"][1]["name"] = broken["vectors"][0]["name"]
    _refused(tmp_path, broken, "duplicate row name")
    broken = copy.deepcopy(doc)
    broken["vectors"][0]["expect"] = {"tag": "TooDeep", "limit": 32, "depth": 33}
    _refused(tmp_path, broken, "unknown payload field")


def test_a_malformed_row_may_use_the_same_fields(tmp_path):
    """One row format for both files: a malformed row's segments, `len`, `limits` and
    `bounds` are checked as a bounds row's are, and none is required."""
    data = json.loads(parity.MALFORMED_VECTORS.read_text())
    path = tmp_path / "malformed.vectors.json"
    row = data["vectors"][0]                                   # truncated-u64-argument, 1b0000
    row.update(bytes=["1b", {"repeat": "00", "count": 2}], len=3, limits={"max_depth": 1},
               bounds={"max_depth": 1})
    path.write_text(json.dumps(data))
    assert parity.validate_malformed_vectors(path) == MALFORMED_ROWS
    for key, bad, match in (("len", 2, "expand to 3 bytes, len is 2"), ("bounds", {"max_depth": 32}, "decoded under"),
                            ("limits", {"max_depth": 0}, "max_depth: an int of at least 1")):
        broken = copy.deepcopy(data)
        broken["vectors"][0][key] = bad
        path.write_text(json.dumps(broken))
        with pytest.raises(parity.ParityValidationError, match=match):
            parity.validate_malformed_vectors(path)
    broken = copy.deepcopy(data)
    wire = next(r for r in broken["vectors"] if r["stage"] == "from_wire")
    wire["bounds"] = {"max_depth": 32}
    path.write_text(json.dumps(broken))
    with pytest.raises(parity.ParityValidationError, match="a from_wire row has no bounds"):
        parity.validate_malformed_vectors(path)


def test_every_artifact_names_contract_v1(tmp_path):
    assert parity.CONTRACT == "taut-codec-parity/i64/v1"
    for path in (parity.INT_VECTORS, parity.MALFORMED_VECTORS, parity.BOUNDS_VECTORS, parity.ALLOWLIST):
        assert json.loads(path.read_text())["contract"] == parity.CONTRACT, path.name
    checks = ((parity.INT_VECTORS, parity.validate_int_vectors),
              (parity.MALFORMED_VECTORS, parity.validate_malformed_vectors),
              (parity.BOUNDS_VECTORS, parity.validate_bounds_vectors),
              (parity.ALLOWLIST, parity.target_statuses))
    for source, check in checks:
        data = json.loads(source.read_text())
        for bad in ("taut-codec-parity/i64/v0", None):
            data["contract"] = bad
            path = tmp_path / source.name
            path.write_text(json.dumps(data))
            with pytest.raises(parity.ParityValidationError, match="expected 'taut-codec-parity/i64/v1'"):
                check(path)


def _shape(t):
    if isinstance(t, ListOf):
        return f"list<{_shape(t.elem)}>"
    if isinstance(t, MapOf):
        return f"map<{_shape(t.key)},{_shape(t.value)}>"
    return t.kind if isinstance(t, Scalar) else "enum" if isinstance(t, EnumRef) else "message"


def test_shapes_holds_every_legal_field_shape():
    """Each generator must generate and compile every shape `ir/validate.py` allows."""
    fields = parity.parity_schema().messages["Shapes"].fields
    assert [f.tag for f in fields] == list(range(1, len(fields) + 1))
    held = {(_shape(f.type), f.optional) for f in fields}
    required = [(kind, False) for kind in ("int", "float", "str", "bytes", "bool", "enum", "message")]
    optional = [(kind, True) for kind in ("int", "enum", "message", "list<int>", "map<str,int>")]
    collections = [(kind, False) for kind in ("list<int>", "list<message>", "list<list<int>>",
                                              "map<str,int>", "map<bool,enum>", "map<int,message>")]
    assert {*required, *optional, *collections, ("str", MISSING_OK)} <= held


# The locals, parameters and unqualified helpers the generators' message code declares or
# calls (`taut/gen/*.py`); each is a field of Names. `value` (a JS lambda parameter) is left
# out as a Kotlin modifier keyword, and `self`, `$0` and C++'s `__`-names cannot be fields.
NAMES = {"m", "b", "c", "v", "o", "f", "x", "e", "k", "i", "j", "a", "t", "it", "kv", "fv", "ok",
         "err", "arr", "ks", "kc", "vc", "ek", "ev", "key", "dup", "entries",
         "encode_value", "java", "decodeDictionary"}

# The nine languages' keywords, reserved and contextual words: Python's from `keyword`,
# Swift's and Kotlin's hard ones from their generators, and the others here.
_KEYWORDS = {
    *keyword.kwlist, *keyword.softkwlist, *swift_gen._SWIFT_KEYWORDS, *kotlin_gen._KT_KEYWORDS,
    *"""abstract as async await become box break const continue crate do dyn else enum extern
        false final fn for gen if impl in let loop macro match mod move mut override priv pub
        ref return self static struct super trait true try type typeof union unsafe unsized use
        virtual where while yield""".split(),                                              # rust
    *"""alignas alignof and and_eq asm auto bitand bitor bool case catch char char8_t char16_t
        char32_t class co_await co_return co_yield compl concept const_cast consteval constexpr
        constinit decltype default delete double dynamic_cast explicit export float friend goto
        inline int long mutable namespace new noexcept not not_eq nullptr operator or or_eq
        private protected public register reinterpret_cast requires short signed sizeof
        static_assert static_cast switch template this thread_local throw typedef typeid
        typename unsigned using void volatile wchar_t xor xor_eq""".split(),               # c++
    *"""assert boolean byte extends finally implements import instanceof interface native
        package permits record sealed strictfp synchronized throws transient var""".split(),  # java
    *"""arguments debugger declare eval function infer is keyof module null readonly
        undefined with""".split(),                                              # js, typescript
    *"chan defer fallthrough func go map range select".split(),                        # go
    *"""by constructor delegate dynamic field file get init out param property receiver set
        setparam value""".split(),                                     # kotlin soft keywords
}


def test_names_fields_are_named_like_what_the_generators_emit():
    """Names catches a field that clashes with a generated local, parameter or unqualified
    helper (a Java field `m`). It holds a scalar, a list and a map, and none of its names
    is a keyword in any of the nine languages: keywords are a separate concern."""
    fields = parity.parity_schema().messages["Names"].fields
    names = {f.name for f in fields}
    assert names == NAMES
    assert {"int", "str", "bool", "list<int>", "map<str,int>"} <= {_shape(f.type) for f in fields}
    assert not names & _KEYWORDS
    assert _row("names-round-trip")["expect"] == {"accept": True}


def test_committed_vectors_match_generator():
    """The committed .json is exactly `gen_vectors.py` output — reviewable AND
    regenerable, and no hand-edit has drifted from the generator."""
    spec = importlib.util.spec_from_file_location(
        "parity_gen_vectors", parity.PARITY_DIR / "gen_vectors.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    assert gen.render(gen.INT_VECTORS) == parity.INT_VECTORS.read_text()
    assert gen.render(gen.MALFORMED_VECTORS) == parity.MALFORMED_VECTORS.read_text()
    assert gen.render(gen.BOUNDS_VECTORS, gen.BOUNDS_HEADER) == parity.BOUNDS_VECTORS.read_text()


# --- allowlist governance ---------------------------------------------------------

def test_every_allowlisted_target_has_phase_owner_and_reason():
    entries = json.loads(parity.ALLOWLIST.read_text())["targets"]
    for entry in entries:
        assert entry["target"] in parity.variants()
        for key in ("phase", "owner", "reason"):
            assert isinstance(entry.get(key), str) and entry[key], (entry["target"], key)
    statuses = {s.target: s for s in parity.target_statuses()}
    assert {e["target"] for e in entries} == {t for t, s in statuses.items() if s.status == "allowlisted"}


def _allowlist(tmp_path, *entries):
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps({"version": 1, "contract": parity.CONTRACT, "targets": list(entries)}))
    return path


ENTRY = {"target": "java", "phase": "P2", "owner": "codec-parity", "reason": "fails M1"}


@pytest.mark.parametrize("key", ["phase", "owner", "reason"])
def test_target_statuses_rejects_an_entry_without_phase_owner_or_reason(tmp_path, key):
    assert parity.allowlisted_targets(_allowlist(tmp_path, ENTRY)) == {"java"}
    entry = {k: v for k, v in ENTRY.items() if k != key}
    with pytest.raises(parity.ParityValidationError, match=f"no allowlist {key}"):
        parity.target_statuses(_allowlist(tmp_path, entry))


def test_target_statuses_rejects_duplicate_allowlist_entry(tmp_path):
    with pytest.raises(parity.ParityValidationError, match="duplicate target"):
        parity.target_statuses(_allowlist(tmp_path, ENTRY, dict(ENTRY)))


def test_the_allowlist_takes_variant_names(tmp_path):
    """A `<target>/fc` variant is gated or allowlisted on its own, like a target."""
    fc = {**ENTRY, "target": "java/fc"}
    statuses = {s.target: s.status for s in parity.target_statuses(_allowlist(tmp_path, fc))}
    assert list(statuses) == list(parity.variants())
    assert statuses["java/fc"] == "allowlisted" and statuses["java"] == "gated"
    assert parity.allowlisted_targets(_allowlist(tmp_path, ENTRY, fc)) == {"java", "java/fc"}
    for bad in ("python/fc", "typescript/fc", "java/xx", "fc"):
        with pytest.raises(parity.ParityValidationError, match="unknown target"):
            parity.target_statuses(_allowlist(tmp_path, {**ENTRY, "target": bad}))


def test_governance_flags_a_green_but_allowlisted_target():
    # Inverse check that makes the gate LEAD: the day a target passes fully it
    # must be de-listed, or CI fails.
    green = parity.TargetReport("python", available=True, results=[
        parity.VectorResult("ok", "malformed", "Truncated", parity.PASS, "", False),
    ])
    assert parity.governance({"python": green}, {"python"})      # green + listed -> violation
    assert parity.governance({"python": green}, set()) == []     # green + gated -> fine


def test_governance_flags_a_gated_target_that_fails():
    red = parity.TargetReport("python", available=True, results=[
        parity.VectorResult("boom", "malformed", "NonCanonicalInt", parity.FAIL, "decoded ok", True),
    ])
    assert parity.governance({"python": red}, set())             # red + gated -> violation
    assert parity.governance({"python": red}, {"python"}) == []  # red + listed -> fine


def test_skipped_target_is_not_a_violation():
    skipped = parity.skipped("rust", "rustc absent")
    assert not skipped.available and skipped.skip_reason == "rustc absent"
    assert parity.governance({"rust": skipped}, set()) == []
    assert parity.governance({"rust": skipped}, {"rust"}) == []


def test_governed_variants_judges_a_target_and_its_fc_variant_as_the_gate_does(tmp_path):
    """The per-language tests' helper: each variant GREEN, or RED and allowlisted."""
    def run(forward_compat=False):
        name = parity.variant("go", forward_compat)
        if forward_compat:
            return parity.red(name, "build failed (exit 1)\nno such thing")
        return parity.parse_report(name, "\n".join(_passing_lines(name)))

    reports, violations = parity.governed_variants(run, _allowlist(tmp_path))
    assert [(r.target, r.green) for r in reports] == [("go", True), ("go/fc", False)]
    assert violations == ["go/fc: RED build failed (exit 1) and is not allowlisted\n"
                          "build failed (exit 1)\nno such thing"]
    fc = {**ENTRY, "target": "go/fc"}
    assert parity.governed_variants(run, _allowlist(tmp_path, fc))[1] == []
    assert parity.governed_variants(run, _allowlist(tmp_path, fc, {**ENTRY, "target": "go"}))[1] == \
        ["go: PASSES fully but is allowlisted — remove it from allowlist.json"]


def test_governance_judges_a_variant_like_a_target():
    red = parity.red("go/fc", "build failed (exit 1)")
    green = parity.parse_report("go/fc", "\n".join(_passing_lines("go/fc")))
    assert green.green and not red.green
    assert parity.governance({"go/fc": red}, set()) == ["go/fc: RED build failed (exit 1) and is not allowlisted"]
    assert parity.governance({"go/fc": red}, {"go/fc"}) == []
    assert parity.governance({"go/fc": red}, {"go"}) != []           # the target's entry is not the variant's
    assert parity.governance({"go/fc": green}, {"go/fc"}) != []      # a green variant must be de-listed


# --- the comparator -------------------------------------------------------------

def test_an_accept_row_passes_only_on_ok():
    row = _row("map-key-2^53")
    assert parity.judge("js", row, parity.OK, row["bytes"])[0] == parity.PASS
    assert parity.judge("js", row, parity.ERR, "NonIntegerMapKey")[0] == parity.FAIL
    assert parity.judge("js", row, parity.UNTYPED, "RangeError: x")[0] == parity.FAIL


def test_an_accept_row_passes_only_when_it_re_encodes_to_its_bytes():
    # D2's law: decode ok => encode(decode(bytes)) == bytes.
    row = _row("text-leading-bom")                           # 64efbbbf61, "\ufeffa"
    assert parity.judge("ts", row, parity.OK, "64efbbbf61") == (parity.PASS, "")
    assert parity.judge("ts", row, parity.OK, "6161") == \
        (parity.FAIL, "re-encoded 6161, expected 64efbbbf61")
    assert parity.judge("ts", row, parity.OK, "") == (parity.FAIL, "no re-encoding reported")


def test_an_accept_row_honours_its_named_re_encoding():
    row = _row("missing-ok-absent")                          # M16: a0, re-encoded as a101f6
    assert row["bytes"] == "a0" and parity.expected_reencoding(row) == "a101f6"
    assert parity.judge("go", row, parity.OK, "a101f6") == (parity.PASS, "")
    assert parity.judge("go", row, parity.OK, "a0") == (parity.FAIL, "re-encoded a0, expected a101f6")
    assert parity.judge("go", row, parity.OK, "")[0] == parity.FAIL
    sparse = _row("shapes-sparse")["bytes"]
    assert parity.expected_reencoding(_row("shapes-missing-ok-absent")) == sparse
    assert parity.expected_reencoding(_row("shapes-sparse")) == sparse


def test_a_tag_row_that_decodes_fails_whatever_it_re_encodes_to():
    row = _row("simple-one-byte-torn")                       # f8: UnsupportedInfo{24}
    assert parity.judge("js", row, parity.OK, "f8") == \
        (parity.FAIL, "decoded ok, expected UnsupportedInfo;info=24")


def test_a_tag_row_compares_the_tag_and_every_named_payload_field_as_a_string():
    row = _row("key-first-negative")                     # {"tag": "NegativeMapKey", "key": "-1"}
    assert parity.judge("js", row, parity.ERR, "NegativeMapKey;key=-1") == (parity.PASS, "")
    assert parity.judge("js", row, parity.ERR, "NegativeMapKey;key=1")[0] == parity.FAIL
    assert parity.judge("js", row, parity.ERR, "NegativeMapKey")[0] == parity.FAIL  # payload missing
    assert parity.judge("js", row, parity.ERR, "Truncated")[0] == parity.FAIL
    assert parity.judge("js", row, parity.OK, "")[0] == parity.FAIL
    assert parity.judge("js", row, parity.UNTYPED, "TypeError: x")[0] == parity.FAIL
    assert parity.judge("js", row, "pass", "")[0] == parity.FAIL                 # not an outcome
    status, detail = parity.judge("js", _row("wrong-type-text"), parity.ERR, "WrongType;expected=str")
    assert status == parity.FAIL and detail == "got WrongType;expected=str, expected WrongType;expected=text"
    # an int in the row and in the report compare equal; fields the row does not name are ignored
    assert parity.judge("js", _row("key-first-duplicate"), parity.ERR,
                        "DuplicateMapKey;key=1;value=0")[0] == parity.PASS


def test_payload_exemptions_are_per_target():
    row = _row("positive-int-overflow")                  # {"tag": "IntOverflow", "value": "9223372036854775808"}
    assert parity.PAYLOAD_EXEMPT == {"rust": frozenset({("IntOverflow", "value")})}
    assert parity.judge("rust", row, parity.ERR, "IntOverflow")[0] == parity.PASS
    assert parity.judge("rust/fc", row, parity.ERR, "IntOverflow")[0] == parity.PASS   # the target's runtime
    assert parity.judge("python", row, parity.ERR, "IntOverflow")[0] == parity.FAIL
    assert parity.judge("python", row, parity.ERR, "IntOverflow;value=9223372036854775808")[0] == parity.PASS


# --- unknown fields and the forward-compat variants (TautCheckedDecode.md §8 question 10) ---

def test_python_typescript_and_every_fc_variant_keep_unknown_fields():
    keepers = {"python", "typescript", *(f"{target}/fc" for target in GENERATED)}
    assert {name for name in parity.variants() if parity.keeps_unknown_fields(name)} == keepers


def test_a_codec_that_drops_unknown_fields_is_judged_by_expect_dropping():
    row = _row("unknown-field-round-trip")                   # Empty holding field 1 = 0
    assert (row["schema"], row["bytes"]) == ("Empty", "a10100")
    for keeper in ("python", "typescript", "rust/fc", "kotlin/fc"):
        assert parity.row_expect(keeper, row) == {"accept": True}
        assert parity.judge(keeper, row, parity.OK, "a10100") == (parity.PASS, "")
        assert parity.judge(keeper, row, parity.OK, "a0") == (parity.FAIL, "re-encoded a0, expected a10100")
    for dropper in GENERATED:
        assert parity.row_expect(dropper, row) == {"accept": True, "reencode": "a0"}
        assert parity.judge(dropper, row, parity.OK, "a0") == (parity.PASS, "")
        assert parity.judge(dropper, row, parity.OK, "a10100") == \
            (parity.FAIL, "re-encoded a10100, expected a0")
    plain = _row("shapes-sparse")                            # no expect_dropping: expect for every codec
    assert parity.row_expect("rust", plain) is plain["expect"]
    assert parity.judge("rust", plain, parity.OK, plain["bytes"]) == (parity.PASS, "")


def test_an_unknown_field_beside_known_ones_is_kept_or_dropped_whole():
    schema = parity.parity_schema()
    row = _row("unknown-field-beside-known")
    decoded = codec.decode(schema, "IntBox", bytes.fromhex(row["bytes"]))
    unknown = decoded.pop("__unknown__")
    assert list(unknown) == [3] and decoded["by_id"]
    assert parity.expected_reencoding(row) == row["bytes"]
    assert parity.expected_reencoding(row, row["expect_dropping"]) == codec.encode(schema, "IntBox", decoded).hex()


def test_a_repeated_map_key_is_reported_as_text():
    """Question 9: the key as text, an int in decimal, a str as itself and a bool as `true`."""
    assert _row("map-field-duplicate")["expect"] == {"tag": "DuplicateMapKey", "key": 5}
    assert _row("map-str-key-duplicate")["expect"] == {"tag": "DuplicateMapKey", "key": "a"}
    assert _row("map-bool-key-duplicate")["expect"] == {"tag": "DuplicateMapKey", "key": "true"}
    schema = parity.parity_schema()
    assert parity._observe_python(schema, _row("map-bool-key-duplicate")) == \
        (parity.ERR, "DuplicateMapKey;key=true")
    assert parity._observe_python(schema, _row("map-str-key-duplicate")) == (parity.ERR, "DuplicateMapKey;key=a")


# --- report parsing and hardening -----------------------------------------------------

def test_a_complete_passing_report_is_green():
    report = parity.parse_report("js", "\n".join(_passing_lines()) + "\n")
    assert report.green
    assert len(report.results) == ALL_ROWS
    assert [r.kind for r in report.results].count("bounds") == BOUNDS_ROWS
    # a keeper's report is a dropper's failure on the unknown-field rows, and the reverse
    kept = parity.parse_report("js", "\n".join(_passing_lines("js/fc")))
    assert sorted(r.name for r in kept.failures) == [
        "depth-32-unknown-field", "unknown-field-beside-known", "unknown-field-round-trip"]
    assert parity.parse_report("js/fc", "\n".join(_passing_lines("js/fc"))).green


def test_a_row_never_reported_fails():
    lines = [line for line in _passing_lines() if not line.startswith("optional-absent\t")]
    report = parity.parse_report("js", "\n".join(lines))
    assert not report.green
    assert [(r.name, r.detail) for r in report.failures] == [("optional-absent", parity.NO_REPORT)]


def test_a_runner_exiting_non_zero_fails_its_target_even_if_every_row_passed():
    report = parity.parse_report("js", "\n".join(_passing_lines()), returncode=101, stderr="boom")
    assert report.failures == []
    assert not report.green
    assert report.fault.startswith("runner exited 101")
    assert parity.governance({"js": report}, set())


def test_a_row_reported_twice_or_unknown_or_with_a_bad_outcome_fails():
    lines = _passing_lines()
    report = parity.parse_report("js", "\n".join([*lines, lines[-1]]))
    assert [r.detail for r in report.failures] == ["reported more than once"]
    report = parity.parse_report("js", "\n".join([*lines, "no-such-row\tok\t"]))
    assert report.failures == [] and "no-such-row" in report.fault and not report.green
    name = parity.int_rows()[0]["name"]
    report = parity.parse_report("js", "\n".join([f"{name}\tok\t", *lines[1:]]))
    assert [(r.name, r.status) for r in report.failures] == [(name, parity.FAIL)]


# --- C3's protocol: the constants line, a from_cbor row's resolved bounds, the two tags ---

def test_a_runner_prints_its_constants_once_as_the_bounds_header_says():
    lines = _passing_lines()
    assert lines[0] == CONSTANTS_LINE and parity.parse_report("js", "\n".join(lines)).green
    missing = parity.parse_report("js", "\n".join(lines[1:]))
    assert missing.failures == [] and not missing.green
    assert missing.fault.splitlines()[0] == parity.NO_CONSTANTS
    assert parity._verdict(missing) == "RED no #constants line"
    assert parity.governance({"js": missing}, set()) and parity.governance({"js": missing}, {"js"}) == []
    twice = parity.parse_report("js", "\n".join([*lines, CONSTANTS_LINE]))
    assert twice.fault == "#constants printed 2 times, expected once"
    for other in ("default_max_depth=64;max_depth_ceiling=128", "default_max_depth=32;max_depth_ceiling=100",
                  "max_depth_ceiling=128;default_max_depth=32", "default_max_depth=32", ""):
        report = parity.parse_report("js", "\n".join([f"{parity.CONSTANTS}\t{other}", *lines[1:]]))
        assert report.fault == f"#constants {other}, expected default_max_depth=32;max_depth_ceiling=128"
    exited = parity.parse_report("js", "\n".join(lines[1:]), returncode=3)
    assert exited.fault.splitlines()[0] == "runner exited 3" and parity.NO_CONSTANTS in exited.fault.splitlines()
    assert parity.red("js", "build failed (exit 1)").fault == "build failed (exit 1)"


def test_a_bounds_rows_fourth_column_must_be_the_bounds_it_is_decoded_under():
    lines = _passing_lines()
    name = "depth-65-declared"                                   # Tree64, declaring max_depth 64
    assert f"{name}\t{parity.ERR}\tTooDeep;limit=64\tmax_depth=64;max_encoded_len=" in lines
    assert "len-9-declared\terr\tTooLarge;len=9;limit=8\tmax_depth=32;max_encoded_len=8" in lines
    for line, why in (
            (f"{name}\terr\tTooDeep;limit=64", "no resolved bounds reported, expected max_depth=64;max_encoded_len="),
            (f"{name}\terr\tTooDeep;limit=64\tmax_depth=32;max_encoded_len=",
             "resolved max_depth=32;max_encoded_len=, expected max_depth=64;max_encoded_len="),
            (f"{name}\terr\tTooDeep;limit=64\tmax_depth=64;max_encoded_len=8",
             "resolved max_depth=64;max_encoded_len=8, expected max_depth=64;max_encoded_len="),
            (f"{name}\terr\tTooDeep;limit=64\tmax_depth=64",
             "resolved bounds 'max_depth=64', not max_depth=<n>;max_encoded_len=<n or empty>"),
            # a wrong resolution is reported as such, whatever the outcome (OPT-P1)
            (f"{name}\terr\tTooDeep;limit=32\tmax_depth=32;max_encoded_len=",
             "resolved max_depth=32;max_encoded_len=, expected max_depth=64;max_encoded_len=")):
        report = parity.parse_report("js", "\n".join(_replace(lines, name, line)))
        assert [(r.name, r.detail) for r in report.failures] == [(name, why)]


def test_a_malformed_from_cbor_rows_fourth_column_is_checked_for_its_form_only():
    lines = _passing_lines()
    name = "missing-required-field"                              # IntBox: MissingKey{2}
    for line in (f"{name}\terr\tMissingKey;key=2", f"{name}\terr\tMissingKey;key=2\tmax_depth=7;max_encoded_len=9"):
        assert parity.parse_report("js", "\n".join(_replace(lines, name, line))).green
    bad = parity.parse_report("js", "\n".join(_replace(lines, name, f"{name}\terr\tMissingKey;key=2\tdepth=32")))
    assert [(r.name, r.detail) for r in bad.failures] == [
        (name, "resolved bounds 'depth=32', not max_depth=<n>;max_encoded_len=<n or empty>")]


def test_only_a_from_cbor_row_has_a_fourth_column():
    lines = _passing_lines()
    for name, line in (("size-over-limit", "size-over-limit\terr\tTooLarge;len=4;limit=3\tmax_depth=32;max_encoded_len=3"),
                       ("unknown-enum", "unknown-enum\terr\tUnknownEnum;enum=Mode;value=99\tmax_depth=32;max_encoded_len="),
                       ("zero", "zero\tpass\t\tmax_depth=32;max_encoded_len=")):
        report = parity.parse_report("js", "\n".join(_replace(lines, name, line)))
        assert [r.name for r in report.failures] == [name]
        assert "has no fourth column" in report.failures[0].detail


def test_too_deep_and_too_large_are_judged_on_tag_and_payload():
    assert {"TooDeep", "TooLarge"} <= parity.DECODE_TAGS
    assert parity.PAYLOAD_FIELDS[-2:] == ("len", "limit")
    assert parity.format_error("TooLarge", {"limit": 3, "len": 4}) == "TooLarge;len=4;limit=3"
    large, deep = _row("size-over-limit"), _row("depth-33-arrays")
    assert parity.judge("js", large, parity.ERR, "TooLarge;len=4;limit=3") == (parity.PASS, "")
    assert parity.judge("js", large, parity.ERR, "TooLarge;limit=3;len=4") == (parity.PASS, "")
    for detail in ("TooLarge;len=4;limit=4", "TooLarge;limit=3", "Truncated", "TooDeep;limit=3"):
        assert parity.judge("js", large, parity.ERR, detail)[0] == parity.FAIL, detail
    assert parity.judge("js", deep, parity.ERR, "TooDeep;limit=32") == (parity.PASS, "")
    assert parity.judge("js", deep, parity.ERR, "TooDeep;limit=128")[0] == parity.FAIL
    assert parity.judge("js", deep, parity.OK, "81" * 32 + "80")[0] == parity.FAIL
    assert parity.judge("js", deep, parity.UNTYPED, "RangeError: Maximum call stack size exceeded")[0] == parity.FAIL
    b1 = _row("depth-32-arrays")                                # an accept row given as segments
    assert parity.expected_reencoding(b1) == "81" * 31 + "80"
    assert parity.judge("js", b1, parity.OK, "81" * 31 + "80") == (parity.PASS, "")
    assert parity.judge("js", b1, parity.OK, str(b1["bytes"]))[0] == parity.FAIL


def test_a_json_reading_runner_gets_all_three_files(tmp_path):
    parity.write_json_rows(tmp_path)
    for path in (parity.INT_VECTORS, parity.MALFORMED_VECTORS, parity.BOUNDS_VECTORS):
        assert (tmp_path / path.name).read_text() == path.read_text()
    assert {"Tree64", "HoldsSized8"} <= set(json.loads((tmp_path / "dispatch.json").read_text())["messages"])


def test_a_build_failure_is_red_not_a_skip(tmp_path):
    ok = parity.build("go", [sys.executable, "-c", "pass"], cwd=tmp_path)
    assert ok is None
    red = parity.build("go", [sys.executable, "-c", "import sys; sys.stderr.write('bad'); sys.exit(2)"],
                       cwd=tmp_path)
    assert red.available and not red.green
    assert red.fault.startswith("build failed (exit 2)") and "bad" in red.fault
    assert {r.detail for r in red.results} == {parity.NO_REPORT}
    assert parity.governance({"go": red}, set())


def test_a_generator_refusal_is_red(tmp_path):
    red = parity.generate("no-such-language", tmp_path)
    assert red is not None and red.available and not red.green
    assert red.fault.startswith("generation failed")
    red = parity.generate("no-such-language/fc", tmp_path)
    assert red.target == "no-such-language/fc" and red.fault.startswith("generation failed")


def test_an_fc_variant_is_generated_with_forward_compat(tmp_path):
    assert parity.generate("go/fc", tmp_path / "fc") is None
    assert "WireResidual" in (tmp_path / "fc" / "go" / "api.go").read_text()
    assert parity.generate("go", tmp_path / "plain") is None
    assert "WireResidual" not in (tmp_path / "plain" / "go" / "api.go").read_text()


def test_every_target_generates_missing_ok(tmp_path):
    """`scaffold.emit` no longer refuses `optional=MISSING_OK` for any target; an
    unknown target is refused as unknown."""
    late = mk(Msg("Late", F("note", 1, STR, optional=MISSING_OK)))
    written = scaffold.emit(late, tmp_path, langs=list(parity.TARGETS), services=[])
    assert {path.relative_to(tmp_path).parts[0] for path in written} == set(parity.TARGETS)
    with pytest.raises(ValueError, match=r"unknown lang\(s\) \['no-such-language'\]"):
        scaffold.emit(late, tmp_path, langs=["no-such-language"], services=[])


def test_run_runner_judges_the_report_and_the_exit_status(tmp_path):
    (tmp_path / "report.txt").write_text("\n".join(_passing_lines()) + "\n")
    emit = "import sys; sys.stdout.write(open('report.txt').read()); sys.exit({})"
    assert parity.run_runner("js", [sys.executable, "-c", emit.format(0)], cwd=tmp_path).green
    red = parity.run_runner("js", [sys.executable, "-c", emit.format(1)], cwd=tmp_path)
    assert red.failures == [] and red.fault.startswith("runner exited 1")
    missing = parity.run_runner("js", [str(tmp_path / "no-such-runner")], cwd=tmp_path)
    assert missing.available and missing.fault.startswith("runner did not start")


# --- the Python harness -----------------------------------------------------------

def test_python_harness_reports_every_row_and_its_governance_is_clean():
    report = parity.run_python()
    assert report.available
    assert len(report.results) == ALL_ROWS
    assert report.green, [report.fault, *(f"{r.name}: {r.detail}" for r in report.failures)]
    assert parity.governance({"python": report}, parity.allowlisted_targets()) == []


def test_python_harness_uses_the_gate_comparator(monkeypatch):
    judged = []
    real = parity.judge

    def spy(target, row, outcome, detail, **resolved):
        judged.append((target, row["name"], resolved))
        return real(target, row, outcome, detail, **resolved)

    monkeypatch.setattr(parity, "judge", spy)
    assert parity.run_python().green
    schema = parity.parity_schema()
    assert judged == [
        ("python", row["name"],
         {"resolved": parity.format_bounds(parity.decoded_under(schema, row)) if row["stage"] == "from_cbor"
          else None})
        for row in parity.decode_rows()]


def test_python_speaks_the_protocol_through_the_parser():
    """Python's report is the lines a runner prints: its runtime's constants once, then each
    row, a from_cbor row's with a fourth column, the bounds its typed entry point resolved."""
    lines = parity.python_report()
    assert lines[0] == CONSTANTS_LINE
    assert (cbor.DEFAULT_MAX_DEPTH, cbor.MAX_DEPTH_CEILING) == (32, 128)
    by_name = {line.split("\t")[0]: line.split("\t") for line in lines[1:]}
    assert len(by_name) == len(lines) - 1 == ALL_ROWS
    assert by_name["size-over-limit"] == ["size-over-limit", parity.ERR, "TooLarge;len=4;limit=3"]
    assert by_name["depth-65-declared"] == ["depth-65-declared", parity.ERR, "TooDeep;limit=64",
                                             "max_depth=64;max_encoded_len="]
    assert by_name["len-8-declared"] == ["len-8-declared", parity.OK, "a101450102030405",
                                          "max_depth=32;max_encoded_len=8"]
    assert by_name["missing-required-field"][3] == "max_depth=32;max_encoded_len="   # both files
    assert len(by_name["unknown-enum"]) == len(by_name["zero"]) == 3                # no fourth column
    assert parity.run_python().green


def test_python_decodes_every_from_cbor_row_through_the_typed_entry_point(monkeypatch):
    """Item 3: from bytes, through `codec.decode`, which applies the message's bounds; a raw
    decode at the defaults and then `decode_struct` would accept B18 and refuse B17."""
    typed, real = [], codec.decode

    def spy(schema, message, data):
        typed.append(message)
        return real(schema, message, data)

    monkeypatch.setattr(codec, "decode", spy)
    monkeypatch.setattr(codec, "decode_struct", lambda *a, **k: pytest.fail("decode_struct used"))
    parity.python_report()
    round_trips = [row["message"] for row in parity.int_rows() if row["kind"] == "round_trip"]
    assert typed == [*round_trips, *(row["schema"] for row in parity.decode_rows() if row["stage"] == "from_cbor")]
    schema = parity.parity_schema()
    deep = parity.row_bytes(_row("depth-64-declared"))
    assert codec.decode(schema, "Tree64", deep)                                     # 64 deep: B17
    with pytest.raises(cbor.DecodeError) as raw:
        cbor.loads(deep)                                                            # the raw default
    assert (raw.value.tag, raw.value.limit) == ("TooDeep", 32)


def test_a_raw_row_passes_its_limits_to_pythons_raw_decode():
    schema = parity.parity_schema()
    assert parity._observe_python(schema, _row("raw-depth-capped")) == (parity.ERR, "TooDeep;limit=128")
    assert parity._observe_python(schema, _row("size-at-limit")) == (parity.OK, "83010203")
    no_limits = {k: v for k, v in _row("size-over-limit").items() if k not in ("limits", "bounds")}
    assert parity._observe_python(schema, no_limits) == (parity.OK, "83010203")       # the defaults
    mis_expanded = {**_row("depth-33-arrays"), "len": 34}                           # item 5
    outcome, detail = parity._observe_python(schema, mis_expanded)
    assert outcome == parity.UNTYPED and "expand to 33 bytes, len is 34" in detail


# --- the registry and the default run ---------------------------------------------------

def test_the_seven_generated_targets_also_run_as_fc_variants():
    """TARGETS stays the nine languages; each generated one also runs as `<target>/fc`,
    listed after it."""
    assert parity.TARGETS == ("rust", "python", "typescript", "js", "cpp", "swift", "go", "kotlin", "java")
    assert parity.FC_TARGETS == GENERATED
    assert parity.variants() == ("rust", "rust/fc", "python", "typescript", "js", "js/fc", "cpp", "cpp/fc",
                                 "swift", "swift/fc", "go", "go/fc", "kotlin", "kotlin/fc", "java", "java/fc")
    assert parity.split_variant("kotlin/fc") == ("kotlin", True)
    assert parity.split_variant("kotlin") == ("kotlin", False)
    assert (parity.variant("go", True), parity.variant("go", False)) == ("go/fc", "go")


def test_a_target_has_a_runner_exactly_when_its_module_exists():
    for name in parity.variants():
        target, _ = parity.split_variant(name)
        module = importlib.util.find_spec(f"taut.corpus.parity_{target}")
        assert (name in parity._RUNNERS) == (target == "python" or module is not None), name
    assert "python" in parity._RUNNERS and "no-such-target" not in parity._RUNNERS
    assert "python/fc" not in parity._RUNNERS and "typescript/fc" not in parity._RUNNERS
    assert list(parity._RUNNERS) == [name for name in parity.variants() if name in parity._RUNNERS]


def test_every_runner_takes_forward_compat_off_by_default():
    for target in parity.TARGETS:
        if target != "python":
            run = importlib.import_module(f"taut.corpus.parity_{target}").run
            assert inspect.signature(run).parameters["forward_compat"].default is False, target
    from taut.corpus import parity_typescript

    with pytest.raises(ValueError, match="no forward-compat variant"):
        parity_typescript.run(forward_compat=True)


def test_the_cpp_runner_describes_an_error_while_its_input_lives(monkeypatch):
    """A C++ DuplicateMapKey's text key is a view of the row's input, so the runner describes
    the error before that input goes; it reported `key=\\x00` when it described it later.
    Built without Names and Sized8, whose fields `b` C++ does not compile yet, and HoldsSized8,
    which holds a Sized8."""
    from taut.corpus import parity_cpp

    if toolchains.find_cxx() is None:
        pytest.skip("no C++ compiler")
    fixture = parity.parity_schema()
    without_names = dataclasses.replace(fixture, messages={
        name: m for name, m in fixture.messages.items() if name not in ("Names", "Sized8", "HoldsSized8")})
    row = _row("map-str-key-duplicate")
    monkeypatch.setattr(parity, "parity_schema", lambda: without_names)
    monkeypatch.setattr(parity, "int_rows", lambda: [])
    monkeypatch.setattr(parity, "malformed_rows", lambda: [row])
    monkeypatch.setattr(parity, "bounds_rows", lambda: [])
    report = parity_cpp.run()
    assert [(r.name, r.status, r.detail) for r in report.results] == [(row["name"], parity.PASS, "")], report.fault


def test_an_fc_variant_runs_its_targets_runner_with_forward_compat(monkeypatch):
    from taut.corpus import parity_go

    calls = []

    def run(forward_compat=False):
        calls.append(forward_compat)
        return parity.skipped(parity.variant("go", forward_compat), "fake toolchain")

    monkeypatch.setattr(parity_go, "run", run)
    assert parity._RUNNERS["go"]().target == "go"
    assert parity._RUNNERS["go/fc"]().target == "go/fc"
    assert calls == [False, True]


def test_adding_a_runner_module_adds_a_target_to_the_gate(tmp_path, monkeypatch):
    # Every real target has a runner module, so a stand-in target joins TARGETS.
    target = "standin"
    monkeypatch.setattr(parity, "TARGETS", (*parity.TARGETS, target))
    assert target not in parity._RUNNERS                          # no module yet, no runner
    module = f"taut.corpus.parity_{target}"
    (tmp_path / f"parity_{target}.py").write_text(textwrap.dedent(f"""
        from taut.corpus import parity

        STDOUT = ""

        def run():
            return parity.parse_report({target!r}, STDOUT)
    """))
    monkeypatch.setattr(taut.corpus, "__path__", [*taut.corpus.__path__, str(tmp_path)])
    importlib.invalidate_caches()
    try:
        assert target in parity._RUNNERS
        assert target not in parity.allowlisted_targets()             # a new target is gated
        runner = importlib.import_module(module)
        runner.STDOUT = "\n".join(_passing_lines())                  # green
        outcome = parity.run_gate(target=target)
        assert outcome.reports[target].green and outcome.violations == []
        assert any(line.startswith(target) and line.endswith("GREEN") for line in outcome.lines)
        runner.STDOUT = ""                                           # red: no row reported
        outcome = parity.run_gate(target=target)
        assert not outcome.reports[target].green
        assert len(outcome.violations) == 1 and outcome.violations[0].startswith(f"{target}: RED")
    finally:
        sys.modules.pop(module, None)


def test_the_gate_runs_every_target_with_a_runner_by_default(monkeypatch):
    def fake(target):
        return lambda: parity.skipped(target, "fake toolchain")

    monkeypatch.setattr(parity, "_RUNNERS", {name: fake(name) for name in ("python", "go", "go/fc")})
    assert set(parity.run_gate().reports) == {"python", "go", "go/fc"}
    assert set(parity.run_gate(run_compiled=False).reports) == {"python"}
    assert set(parity.run_gate(target="go").reports) == {"go", "go/fc"}   # a target: each variant
    assert set(parity.run_gate(target="go/fc").reports) == {"go/fc"}      # a variant: itself
    assert parity.run_gate(target="java").reports == {}           # no runner: not run
    for unknown in ("python/fc", "go/xx"):
        with pytest.raises(parity.ParityValidationError, match="unknown target"):
            parity.run_gate(target=unknown)


def test_the_summary_gives_each_variant_its_own_line(monkeypatch):
    def fake(name):
        return lambda: parity.parse_report(name, "\n".join(_passing_lines(name)))

    monkeypatch.setattr(parity, "_RUNNERS", {name: fake(name) for name in ("python", "go", "go/fc")})
    lines = parity.run_gate().lines
    table = {name: [line for line in lines if line.startswith(f"{name:<11} ")] for name in parity.variants()}
    assert all(len(found) == 1 for found in table.values()), table
    assert table["go"][0].endswith("GREEN") and table["go/fc"][0].endswith("GREEN")
    assert "not run" in table["rust/fc"][0]


def test_a_runner_that_raises_is_red_and_the_others_still_run(monkeypatch):
    def broken():
        raise RuntimeError("runner bug")

    monkeypatch.setattr(parity, "_RUNNERS", {"python": parity.run_python, "go": broken})
    outcome = parity.run_gate()
    assert outcome.reports["python"].available and outcome.reports["python"].results
    assert outcome.reports["go"].available and not outcome.reports["go"].green
    assert outcome.reports["go"].fault == "runner raised\nRuntimeError: runner bug"
    assert "  ! RuntimeError: runner bug" in outcome.lines
    assert f"  - no row reported ({ALL_ROWS} rows)" in outcome.lines


def test_the_cli_takes_a_target_or_an_fc_variant(monkeypatch, capsys):
    def fake(name):
        return lambda: parity.skipped(name, "fake toolchain")

    monkeypatch.setattr(parity, "_RUNNERS", {name: fake(name) for name in ("python", "go", "go/fc")})
    assert main(["parity", "-t", "go/fc"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "skipped" in next(line for line in lines if line.startswith(f"{'go/fc':<11} "))
    assert "not run" in next(line for line in lines if line.startswith(f"{'go':<11} "))
    with pytest.raises(SystemExit) as refused:
        main(["parity", "-t", "python/fc"])
    assert refused.value.code == 2


def test_parity_cli_python_only_reports_clean(capsys):
    assert main(["parity", "--no-compile"]) == 0
    out = capsys.readouterr().out
    assert f"int vectors: {INT_ROWS}" in out
    assert f"malformed vectors: {MALFORMED_ROWS}" in out
    assert f"bounds vectors: {BOUNDS_ROWS}" in out
    assert "governance: clean" in out


def test_full_gate_governance_clean():
    """End-to-end: every target that has a runner, through `tautc parity`. A missing
    toolchain skips with its reason (not a violation), so this holds whichever
    toolchains are present; a target that ran is green exactly when it is not
    allowlisted, and an allowlisted target's reason names every row it fails or, when
    its code did not generate or build, that fault. A runner that does not speak C3's
    protocol yet (D1) prints no #constants line and reports no bounds row: its reason
    starts with that fault and names every other row it fails."""
    outcome = parity.run_gate(run_compiled=True)
    assert outcome.violations == [], "\n".join(outcome.violations)
    assert set(outcome.reports) == set(parity._RUNNERS)
    assert outcome.reports["python"].available
    reasons = {s.target: s.reason for s in parity.target_statuses() if s.status == "allowlisted"}
    for target, report in outcome.reports.items():
        if not report.available or target not in reasons:
            continue
        label = report.fault.splitlines()[0] if report.fault else ""
        if label:
            assert label.startswith(("generation failed", "build failed", parity.NO_CONSTANTS)), (target, report.fault)
            assert reasons[target].startswith(label), (target, label)
        if label.startswith(("generation failed", "build failed")):
            continue
        unnamed = [r.name for r in report.failures
                   if r.name not in reasons[target] and not (label and r.kind == "bounds")]
        assert unnamed == [], (target, unnamed)


# --- toolchain finders ------------------------------------------------------------------

def _tool(path, code=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\nexit {code}\n")
    path.chmod(0o755)
    return path


@pytest.mark.skipif(os.name == "nt", reason="fake tools are shell scripts")
def test_java_tools_come_from_java_home_first(tmp_path, monkeypatch):
    home = tmp_path / "jdk"
    javac, java = _tool(home / "bin" / "javac"), _tool(home / "bin" / "java")
    monkeypatch.setenv("JAVA_HOME", str(home))
    assert toolchains.find_java_tools() == (str(javac), str(java))
    _tool(home / "bin" / "javac", code=1)                          # a broken JDK is passed over
    assert toolchains.find_java_tools() != (str(javac), str(java))


@pytest.mark.skipif(os.name == "nt", reason="fake tools are shell scripts")
def test_kotlinc_comes_from_the_kotlinc_variable_with_the_java_it_runs_with(tmp_path, monkeypatch):
    kotlinc = _tool(tmp_path / "kotlinc" / "bin" / "kotlinc")
    java = _tool(tmp_path / "jdk" / "bin" / "java")
    monkeypatch.setenv("KOTLINC", str(tmp_path / "kotlinc"))      # a directory names its bin/kotlinc
    monkeypatch.setenv("JAVA_HOME", str(tmp_path / "jdk"))
    assert toolchains.find_kotlin_tools() == (str(kotlinc), str(java))
    assert toolchains.java_env(str(java))["JAVA_HOME"] == str((tmp_path / "jdk").resolve())


@pytest.mark.skipif(os.name == "nt", reason="PATH isolation uses POSIX paths")
def test_a_missing_toolchain_is_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.delenv("KOTLINC", raising=False)
    monkeypatch.setattr(toolchains, "ANDROID_STUDIO_JBR", tmp_path / "no-jbr")
    monkeypatch.setattr(toolchains, "ANDROID_STUDIO_KOTLINC", tmp_path / "no-kotlinc")
    for finder in (toolchains.find_rustc, toolchains.find_node, toolchains.find_node_for_typescript,
                   toolchains.find_go, toolchains.find_swiftc, toolchains.find_cxx,
                   toolchains.find_java_tools, toolchains.find_kotlinc, toolchains.find_kotlin_tools):
        assert finder() is None, finder.__name__
