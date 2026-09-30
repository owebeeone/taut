"""Go runner for the parity gate (see `parity_rust.py` for the shape).

The generated code is `package taut`. The runner is a `package main` that imports
it from a GOPATH laid out in the temporary directory (`gopath/src/parity/go`), and
it is built with modules off and with GOPATH, the build cache and Go's temporary
files all inside that directory, so the build never touches the user's Go cache
or GOPATH.

The runner reports what the generated Go codec did with each row, a decoded
malformed or bounds row with the hex of its re-encoding (`Encode` of the tree for a raw
row, of the typed value's `ToCbor()` for a from_cbor row); the gate judges it
(`parity.judge`). It speaks the bounds protocol (`parity`'s docstring, items 1-5): it
prints the runtime's `DefaultMaxDepth` and `MaxDepthCeiling` once as its `#constants`
line; a raw row with `limits` calls `TryDecodeWith` with them, and one without calls
`TryDecode`; every from_cbor row decodes from bytes through its message's
`TryXFromBytes`, and its line adds the bounds that entry point applies, the generated
`XMaxDepth` and `XMaxEncodedLen`; and it expands a row's segments itself, reporting an
expansion whose length is not the row's `len` as untyped.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from . import parity, toolchains

TARGET = "go"
_PACKAGE = "parity"  # the GOPATH directory that holds the generated `go` package and the runner

_MAIN = r'''// The Go runner for `tautc parity` (taut/src/taut/corpus/parity_go.py). Generated.
package main

import (
	"bytes"
	"encoding/hex"
	"errors"
	"fmt"
	"strconv"
	"strings"

	taut "@PACKAGE@/go"
)

type intRow struct {
	name string
	cbor string
	n    string
	byID [][2]string
}

type encodeFailRow struct {
	name   string
	values []string
}

// segment is count copies of hex, a part of a row's bytes.
type segment struct {
	hex   string
	count int
}

// decodeRow is a malformed or bounds row. length is its len, -1 where it states none; a
// raw row with limits passes maxDepth and maxEncodedLen (-1: no length bound).
type decodeRow struct {
	name          string
	stage         string
	schema        string
	segments      []segment
	length        int
	limits        bool
	maxDepth      int
	maxEncodedLen int
}

var roundTrips = []intRow{
@ROUND_TRIP@
}

var encodeFails = []encodeFailRow{
@ENCODE_FAIL@
}

var decodeRows = []decodeRow{
@DECODE_ROWS@
}

var detailSpaces = strings.NewReplacer("\t", " ", "\n", " ", "\r", " ")

// emit prints a report line, its columns separated by tabs.
func emit(columns ...string) {
	for i, column := range columns {
		columns[i] = detailSpaces.Replace(column)
	}
	fmt.Println(strings.Join(columns, "\t"))
}

func sameMap(a, b map[int64]int64) bool {
	if len(a) != len(b) {
		return false
	}
	for k, v := range a {
		if w, ok := b[k]; !ok || w != v {
			return false
		}
	}
	return true
}

// roundTrip encodes the row's IntBox, compares the hex, decodes it, compares the
// values and re-encodes.
func roundTrip(row intRow) (outcome, detail string) {
	defer func() {
		if r := recover(); r != nil {
			outcome, detail = "fail", fmt.Sprintf("panic: %v", r)
		}
	}()
	n, err := strconv.ParseInt(row.n, 10, 64)
	if err != nil {
		return "fail", "n: " + err.Error()
	}
	byID := map[int64]int64{}
	for _, pair := range row.byID {
		k, err := strconv.ParseInt(pair[0], 10, 64)
		if err != nil {
			return "fail", "by_id key: " + err.Error()
		}
		v, err := strconv.ParseInt(pair[1], 10, 64)
		if err != nil {
			return "fail", "by_id value: " + err.Error()
		}
		byID[k] = v
	}
	built := taut.IntBox{N: n, ById: byID}
	if enc := hex.EncodeToString(taut.Encode(built.ToCbor())); enc != row.cbor {
		return "fail", fmt.Sprintf("encode %s != %s", enc, row.cbor)
	}
	data, err := hex.DecodeString(row.cbor)
	if err != nil {
		return "fail", "row hex: " + err.Error()
	}
	decoded, err := taut.TryIntBoxFromBytes(data)
	if err != nil {
		return "fail", "decode: " + err.Error()
	}
	if decoded.N != n || !sameMap(decoded.ById, byID) {
		return "fail", fmt.Sprintf("decoded %+v", decoded)
	}
	if re := hex.EncodeToString(taut.Encode(decoded.ToCbor())); re != row.cbor {
		return "fail", fmt.Sprintf("reencode %s != %s", re, row.cbor)
	}
	return "pass", ""
}

// encodeFail: int64 is the encode-side subset guard, so a value outside it cannot
// be built at all. The row is type-satisfied when one of its integers does not fit.
func encodeFail(row encodeFailRow) (string, string) {
	for _, text := range row.values {
		_, err := strconv.ParseInt(text, 10, 64)
		if errors.Is(err, strconv.ErrRange) {
			return "type-satisfied", "unrepresentable in int64"
		}
		if err != nil {
			return "fail", err.Error()
		}
	}
	return "fail", "every value fits int64, expected one outside it"
}

// fromCbor is a from_cbor row's typed entry point, by message name (from the fixture
// schema): the message's decode from bytes, under its bounds, and the decoded value's
// own encoding.
func fromCbor(message string, data []byte) ([]byte, error) {
	switch message {
@FROM_CBOR@
	}
	return nil, fmt.Errorf("no from_cbor entry point for %s", message)
}

// resolved is a from_cbor row's fourth column: the bounds its message's typed entry
// point applies, from the generated constants, the length empty where none applies.
func resolved(message string) string {
	switch message {
@RESOLVED@
	}
	return "no typed entry point for " + message
}

func bounds(maxDepth, maxEncodedLen int) string {
	length := ""
	if maxEncodedLen >= 0 {
		length = strconv.Itoa(maxEncodedLen)
	}
	return fmt.Sprintf("max_depth=%d;max_encoded_len=%s", maxDepth, length)
}

// fromWire is a from_wire row's typed entry point, by enum name (from the fixture schema).
func fromWire(enum string, c taut.Cbor) error {
	switch enum {
@FROM_WIRE@
	}
	return fmt.Errorf("no from_wire entry point for %s", enum)
}

// expand is a row's bytes, its segments expanded, or an error when they do not expand
// to its length.
func expand(row decodeRow) ([]byte, error) {
	data := []byte{}
	for _, seg := range row.segments {
		piece, err := hex.DecodeString(seg.hex)
		if err != nil {
			return nil, fmt.Errorf("row hex: %w", err)
		}
		data = append(data, bytes.Repeat(piece, seg.count)...)
	}
	if row.length >= 0 && len(data) != row.length {
		return nil, fmt.Errorf("bytes expand to %d bytes, len is %d", len(data), row.length)
	}
	return data, nil
}

// rawDecode is a raw_decode row's call: TryDecodeWith with the limits it passes, else
// TryDecode.
func rawDecode(row decodeRow, data []byte) (taut.Cbor, error) {
	if row.limits {
		return taut.TryDecodeWith(data, row.maxDepth, row.maxEncodedLen)
	}
	return taut.TryDecode(data)
}

// decoded returns a decoded row's re-encoding: the tree for raw_decode, the typed value
// for from_cbor, and nothing for from_wire (an enum row never accepts).
func decoded(row decodeRow, data []byte) ([]byte, error) {
	switch row.stage {
	case "raw_decode":
		c, err := rawDecode(row, data)
		if err != nil {
			return nil, err
		}
		return taut.Encode(c), nil
	case "from_cbor":
		return fromCbor(row.schema, data)
	case "from_wire":
		c, err := taut.TryDecode(data)
		if err != nil {
			return nil, err
		}
		return nil, fromWire(row.schema, c)
	}
	return nil, fmt.Errorf("unknown stage %s", row.stage)
}

// describe is an err detail: the tag, then ;field=value for each payload field the
// tag carries (TautCheckedDecode.md CD-E1). A tag it does not know is reported as
// untyped, so a new tag fails the gate until it is described here.
func describe(e *taut.DecodeError) (string, bool) {
	switch e.Tag {
	case "Truncated", "TrailingBytes", "InvalidUtf8", "NonIntegerMapKey":
		return e.Tag, true
	case "UnsupportedInfo":
		return fmt.Sprintf("%s;info=%d", e.Tag, e.Info), true
	case "UnsupportedMajor":
		return fmt.Sprintf("%s;major=%d", e.Tag, e.Major), true
	case "NegativeMapKey", "DuplicateMapKey", "MissingKey":
		return fmt.Sprintf("%s;key=%s", e.Tag, e.Key), true
	case "WrongType":
		return fmt.Sprintf("%s;expected=%s", e.Tag, e.Expected), true
	case "UnknownEnum":
		return fmt.Sprintf("%s;enum=%s;value=%s", e.Tag, e.Enum, e.Value), true
	case "NonCanonicalInt", "IntOverflow":
		return fmt.Sprintf("%s;value=%s", e.Tag, e.Value), true
	case "TooDeep":
		return fmt.Sprintf("%s;limit=%d", e.Tag, e.Limit), true
	case "TooLarge":
		return fmt.Sprintf("%s;len=%d;limit=%d", e.Tag, e.Len, e.Limit), true
	}
	return "", false
}

// observe decodes one malformed or bounds row and reports what happened: ok, err with
// the tag and payload, or untyped for a row whose bytes do not expand to its length,
// any other error or a panic.
func observe(row decodeRow) (outcome, detail string) {
	defer func() {
		if r := recover(); r != nil {
			outcome, detail = "untyped", fmt.Sprintf("panic: %v", r)
		}
	}()
	data, err := expand(row)
	if err != nil {
		return "untyped", err.Error()
	}
	again, err := decoded(row, data)
	if err == nil {
		return "ok", hex.EncodeToString(again)
	}
	decodeErr, ok := err.(*taut.DecodeError)
	if !ok {
		return "untyped", fmt.Sprintf("%T: %v", err, err)
	}
	if text, known := describe(decodeErr); known {
		return "err", text
	}
	return "untyped", "DecodeError with an unknown tag: " + decodeErr.Error()
}

func main() {
	emit("#constants", fmt.Sprintf("default_max_depth=%d;max_depth_ceiling=%d",
		taut.DefaultMaxDepth, taut.MaxDepthCeiling))
	for _, row := range roundTrips {
		outcome, detail := roundTrip(row)
		emit(row.name, outcome, detail)
	}
	for _, row := range encodeFails {
		outcome, detail := encodeFail(row)
		emit(row.name, outcome, detail)
	}
	for _, row := range decodeRows {
		outcome, detail := observe(row)
		if row.stage == "from_cbor" {
			emit(row.name, outcome, detail, resolved(row.schema))
		} else {
			emit(row.name, outcome, detail)
		}
	}
}
'''


def _go(value: str) -> str:
    """A Go string literal (row names, integers and hex are ASCII)."""
    return json.dumps(value)


def _decode_row(row: dict) -> str:
    """A malformed or bounds row as a `decodeRow` literal: its bytes as segments, which the
    runner expands (the bounds protocol, item 5), and a raw row's `limits`, an absent
    `max_depth` the runtime's default and an absent `max_encoded_len` none (-1)."""
    segments = ", ".join(f"{{{_go(hexed)}, {count}}}" for hexed, count in parity.segments(row))
    fields = [f"name: {_go(row['name'])}", f"stage: {_go(row['stage'])}",
              f"schema: {_go(row.get('schema', ''))}", f"segments: []segment{{{segments}}}",
              f"length: {row.get('len', -1)}"]
    if "limits" in row:
        limits = row["limits"]
        fields += ["limits: true", f"maxDepth: {limits.get('max_depth', 'taut.DefaultMaxDepth')}",
                   f"maxEncodedLen: {limits.get('max_encoded_len', -1)}"]
    return f"\t{{{', '.join(fields)}}},"


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail = [], []
    for row in parity.int_rows():
        value = row["value"]
        if row["kind"] == "round_trip":
            pairs = ", ".join(f"{{{_go(k)}, {_go(v)}}}" for k, v in value["by_id"])
            round_trip.append(f"\t{{name: {_go(row['name'])}, cbor: {_go(row['cbor'])}, "
                              f"n: {_go(value['n'])}, byID: [][2]string{{{pairs}}}}},")
        else:
            ints = [value["n"], *(item for pair in value["by_id"] for item in pair)]
            encode_fail.append(f"\t{{name: {_go(row['name'])}, "
                               f"values: []string{{{', '.join(_go(i) for i in ints)}}}}},")
    decode = [_decode_row(row) for row in parity.decode_rows()]
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(decode)


def _dispatch() -> tuple[str, str, str]:
    """The `switch` cases for every message (`from_cbor`, and the bounds its typed entry
    point applies) and enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()

    def message(name: str) -> str:
        return (f"\tcase {_go(name)}:\n\t\tv, err := taut.Try{name}FromBytes(data)\n"
                f"\t\tif err != nil {{\n\t\t\treturn nil, err\n\t\t}}\n"
                f"\t\treturn taut.Encode(v.ToCbor()), nil")

    def bounds(name: str) -> str:
        return f"\tcase {_go(name)}:\n\t\treturn bounds(taut.{name}MaxDepth, taut.{name}MaxEncodedLen)"

    def enum(name: str) -> str:
        return f"\tcase {_go(name)}:\n\t\t_, err := taut.Try{name}FromCbor(c)\n\t\treturn err"

    return ("\n".join(map(message, dispatch.messages)), "\n".join(map(bounds, dispatch.messages)),
            "\n".join(map(enum, dispatch.enums)))


def _source() -> str:
    round_trip, encode_fail, decode = _tables()
    from_cbor, resolved, from_wire = _dispatch()
    return (_MAIN
            .replace("@PACKAGE@", _PACKAGE)
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@DECODE_ROWS@", decode)
            .replace("@FROM_CBOR@", from_cbor)
            .replace("@RESOLVED@", resolved)
            .replace("@FROM_WIRE@", from_wire))


def _build_env(work: Path) -> dict[str, str]:
    """Modules off; GOPATH, the build cache and Go's temporary files inside `work`."""
    env = os.environ.copy()
    for name in ("gocache", "gotmp"):
        (work / name).mkdir(exist_ok=True)
    env.update(GO111MODULE="off", GOPATH=str(work / "gopath"), GOCACHE=str(work / "gocache"),
               GOTMPDIR=str(work / "gotmp"), GOTOOLCHAIN="local", GOFLAGS="")
    return env


def run(forward_compat: bool = False) -> parity.TargetReport:
    """The go gate, or with `forward_compat` its `go/fc` variant (`parity_rust.py`)."""
    name = parity.variant(TARGET, forward_compat)
    go = toolchains.find_go()
    if go is None:
        return parity.skipped(name, "go not found")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        package = work / "gopath" / "src" / _PACKAGE
        failed = parity.generate(name, package, runtime=True)
        if failed is not None:
            return failed
        runner = package / "runner"
        runner.mkdir()
        (runner / "main.go").write_text(_source())
        binary = work / "parity_runner"
        failed = parity.build(name, [go, "build", "-o", str(binary), f"{_PACKAGE}/runner"],
                              cwd=work, env=_build_env(work))
        if failed is not None:
            return failed
        return parity.run_runner(name, [str(binary)], cwd=work)
