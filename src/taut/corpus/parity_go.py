"""Go runner for the parity gate (see `parity_rust.py` for the shape).

The generated code is `package taut`. The runner is a `package main` that imports
it from a GOPATH laid out in the temporary directory (`gopath/src/parity/go`), and
it is built with modules off and with GOPATH, the build cache and Go's temporary
files all inside that directory, so the build never touches the user's Go cache
or GOPATH.

The runner reports what the generated Go codec did with each row; for a malformed
row the gate judges it (`parity.judge`).
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

type malformedRow struct {
	name   string
	stage  string
	schema string
	bytes  string
}

var roundTrips = []intRow{
@ROUND_TRIP@
}

var encodeFails = []encodeFailRow{
@ENCODE_FAIL@
}

var malformed = []malformedRow{
@MALFORMED@
}

var detailSpaces = strings.NewReplacer("\t", " ", "\n", " ", "\r", " ")

func emit(name, outcome, detail string) {
	fmt.Printf("%s\t%s\t%s\n", name, outcome, detailSpaces.Replace(detail))
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
	c, err := taut.TryDecode(data)
	if err != nil {
		return "fail", "decode: " + err.Error()
	}
	decoded, err := taut.TryIntBoxFromCbor(c)
	if err != nil {
		return "fail", "from_cbor: " + err.Error()
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

// fromCbor is a from_cbor row's typed entry point, by message name (from the fixture schema).
func fromCbor(message string, c taut.Cbor) error {
	switch message {
@FROM_CBOR@
	}
	return fmt.Errorf("no from_cbor entry point for %s", message)
}

// fromWire is a from_wire row's typed entry point, by enum name (from the fixture schema).
func fromWire(enum string, c taut.Cbor) error {
	switch enum {
@FROM_WIRE@
	}
	return fmt.Errorf("no from_wire entry point for %s", enum)
}

func decodeRow(row malformedRow) error {
	data, err := hex.DecodeString(row.bytes)
	if err != nil {
		return fmt.Errorf("row hex: %w", err)
	}
	c, err := taut.TryDecode(data)
	if err != nil {
		return err
	}
	switch row.stage {
	case "raw_decode":
		return nil
	case "from_cbor":
		return fromCbor(row.schema, c)
	case "from_wire":
		return fromWire(row.schema, c)
	}
	return fmt.Errorf("unknown stage %s", row.stage)
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
		return fmt.Sprintf("%s;key=%d", e.Tag, e.Key), true
	case "WrongType":
		return fmt.Sprintf("%s;expected=%s", e.Tag, e.Expected), true
	case "UnknownEnum":
		return fmt.Sprintf("%s;enum=%s;value=%s", e.Tag, e.Enum, e.Value), true
	case "NonCanonicalInt", "IntOverflow":
		return fmt.Sprintf("%s;value=%s", e.Tag, e.Value), true
	}
	return "", false
}

// observe decodes one malformed row and reports what happened: ok, err with the
// tag and payload, or untyped for any other error or a panic.
func observe(row malformedRow) (outcome, detail string) {
	defer func() {
		if r := recover(); r != nil {
			outcome, detail = "untyped", fmt.Sprintf("panic: %v", r)
		}
	}()
	err := decodeRow(row)
	if err == nil {
		return "ok", ""
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
	for _, row := range roundTrips {
		outcome, detail := roundTrip(row)
		emit(row.name, outcome, detail)
	}
	for _, row := range encodeFails {
		outcome, detail := encodeFail(row)
		emit(row.name, outcome, detail)
	}
	for _, row := range malformed {
		outcome, detail := observe(row)
		emit(row.name, outcome, detail)
	}
}
'''


def _go(value: str) -> str:
    """A Go string literal (row names, integers and hex are ASCII)."""
    return json.dumps(value)


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail, malformed = [], [], []
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
    for row in parity.malformed_rows():
        malformed.append(f"\t{{name: {_go(row['name'])}, stage: {_go(row['stage'])}, "
                         f"schema: {_go(row.get('schema', ''))}, bytes: {_go(row['bytes'])}}},")
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(malformed)


def _dispatch() -> tuple[str, str]:
    """The `switch` cases for every message (`from_cbor`) and enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()

    def case(name: str) -> str:
        return f"\tcase {_go(name)}:\n\t\t_, err := taut.Try{name}FromCbor(c)\n\t\treturn err"

    return "\n".join(map(case, dispatch.messages)), "\n".join(map(case, dispatch.enums))


def _source() -> str:
    round_trip, encode_fail, malformed = _tables()
    from_cbor, from_wire = _dispatch()
    return (_MAIN
            .replace("@PACKAGE@", _PACKAGE)
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@MALFORMED@", malformed)
            .replace("@FROM_CBOR@", from_cbor)
            .replace("@FROM_WIRE@", from_wire))


def _build_env(work: Path) -> dict[str, str]:
    """Modules off; GOPATH, the build cache and Go's temporary files inside `work`."""
    env = os.environ.copy()
    for name in ("gocache", "gotmp"):
        (work / name).mkdir(exist_ok=True)
    env.update(GO111MODULE="off", GOPATH=str(work / "gopath"), GOCACHE=str(work / "gocache"),
               GOTMPDIR=str(work / "gotmp"), GOTOOLCHAIN="local", GOFLAGS="")
    return env


def run() -> parity.TargetReport:
    go = toolchains.find_go()
    if go is None:
        return parity.skipped(TARGET, "go not found")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        package = work / "gopath" / "src" / _PACKAGE
        failed = parity.generate(TARGET, package, runtime=True)
        if failed is not None:
            return failed
        runner = package / "runner"
        runner.mkdir()
        (runner / "main.go").write_text(_source())
        binary = work / "parity_runner"
        failed = parity.build(TARGET, [go, "build", "-o", str(binary), f"{_PACKAGE}/runner"],
                              cwd=work, env=_build_env(work))
        if failed is not None:
            return failed
        return parity.run_runner(TARGET, [str(binary)], cwd=work)
