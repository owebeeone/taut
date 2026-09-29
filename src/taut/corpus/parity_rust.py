"""Rust runner for the parity gate — the model a compiled runner copies.

The gate finds a target's runner by module name, `taut.corpus.parity_<target>`,
and calls its `run(forward_compat: bool = False) -> TargetReport` (see
`parity._RUNNERS`): once as the target, and once with `forward_compat=True` as its
`<target>/fc` variant, whose name the report carries (`parity.variant`). The steps:

  1. find the toolchain (`toolchains`); a missing one is the only skip;
  2. generate the fixture's code (`parity.generate`, which generates the `/fc` variant
     with forward_compat); a refusal is RED;
  3. write a runner whose row tables come from `parity.int_rows()` and
     `parity.malformed_rows()` and whose dispatch comes from
     `parity.fixture_dispatch()`, never from hard-coded message names;
  4. build it (`parity.build`); a failure is RED;
  5. run it (`parity.run_runner`), which parses and judges its report.

The runner prints `name<TAB>outcome<TAB>detail` per row. It checks int rows
itself; for a malformed row it only reports what happened (`ok` with the hex of the
re-encoding; `err` with the tag and payload; `untyped` for a panic) and the gate
judges it.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import parity, toolchains

TARGET = "rust"

_MAIN = r'''
#![allow(warnings)]
extern crate alloc;
#[path = "@CBOR@"]
mod cbor;
#[path = "@API@"]
mod api;

use cbor::{encode, try_decode, Cbor, DecodeError};
use std::collections::BTreeMap;

struct IntRow { name: &'static str, cbor: &'static str, n: &'static str, by_id: &'static [(&'static str, &'static str)] }
struct EncFail { name: &'static str, value: &'static str }
struct Mal { name: &'static str, stage: &'static str, schema: &'static str, bytes: &'static str }

static ROUND_TRIP: &[IntRow] = &[
@ROUND_TRIP@
];
static ENCODE_FAIL: &[EncFail] = &[
@ENCODE_FAIL@
];
static MALFORMED: &[Mal] = &[
@MALFORMED@
];

fn unhex(s: &str) -> Vec<u8> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap()).collect()
}

fn hexof(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

fn pi(s: &str) -> i64 {
    s.parse::<i64>().unwrap()
}

fn emit(name: &str, outcome: &str, detail: &str) {
    println!("{name}\t{outcome}\t{}", detail.replace(&['\t', '\n', '\r'][..], " "));
}

/// A from_cbor row's typed entry point, by message name (from the fixture schema):
/// the decoded value's own encoding.
fn from_cbor(message: &str, c: &Cbor) -> Result<Vec<u8>, DecodeError> {
    match message {
@FROM_CBOR@
        _ => panic!("no from_cbor entry point for {message}"),
    }
}

/// A from_wire row's typed entry point, by enum name (from the fixture schema).
fn from_wire(name: &str, v: i64) -> Result<(), DecodeError> {
    match name {
@FROM_WIRE@
        _ => panic!("no from_wire entry point for {name}"),
    }
}

/// A decoded row's re-encoding: the tree for raw_decode, the typed value for
/// from_cbor, and nothing for from_wire (an enum row never accepts).
fn decode_row(row: &Mal) -> Result<Vec<u8>, DecodeError> {
    let c = try_decode(&unhex(row.bytes))?;
    match row.stage {
        "raw_decode" => Ok(encode(&c)),
        "from_cbor" => from_cbor(row.schema, &c),
        "from_wire" => from_wire(row.schema, c.try_int()?).map(|_| Vec::new()),
        other => panic!("unknown stage {other}"),
    }
}

/// An `err` detail: the tag, then `;field=value` for each payload field it carries.
/// Exhaustive on purpose: a new variant fails the build until it is reported here.
fn describe(e: &DecodeError) -> String {
    match e {
        DecodeError::Truncated => "Truncated".to_string(),
        DecodeError::TrailingBytes => "TrailingBytes".to_string(),
        DecodeError::InvalidUtf8 => "InvalidUtf8".to_string(),
        DecodeError::UnsupportedInfo(info) => format!("UnsupportedInfo;info={info}"),
        DecodeError::UnsupportedMajor(major) => format!("UnsupportedMajor;major={major}"),
        DecodeError::NonIntegerMapKey => "NonIntegerMapKey".to_string(),
        DecodeError::DuplicateMapKey(key) => format!("DuplicateMapKey;key={key}"),
        DecodeError::IntOverflow => "IntOverflow".to_string(),
        DecodeError::NonCanonicalInt(value) => format!("NonCanonicalInt;value={value}"),
        DecodeError::NegativeMapKey(key) => format!("NegativeMapKey;key={key}"),
        DecodeError::MissingKey(key) => format!("MissingKey;key={key}"),
        DecodeError::WrongType { expected } => format!("WrongType;expected={expected}"),
        DecodeError::UnknownEnum { enum_name, value } => format!("UnknownEnum;enum={enum_name};value={value}"),
    }
}

fn panic_text(payload: &(dyn std::any::Any + Send)) -> String {
    if let Some(text) = payload.downcast_ref::<&str>() {
        return text.to_string();
    }
    if let Some(text) = payload.downcast_ref::<String>() {
        return text.clone();
    }
    "non-string panic payload".to_string()
}

fn main() {
    for row in ROUND_TRIP {
        let by_id: BTreeMap<i64, i64> = row.by_id.iter().map(|(k, v)| (pi(k), pi(v))).collect();
        // `..Default::default()` fills the forward-compat `wire_residual`.
        let built = api::IntBox { n: pi(row.n), by_id: by_id.clone(), ..Default::default() };
        let enc = hexof(&encode(&built.to_cbor()));
        if enc != row.cbor {
            emit(row.name, "fail", &format!("encode {} != {}", enc, row.cbor));
            continue;
        }
        match try_decode(&unhex(row.cbor)).and_then(|c| api::IntBox::from_cbor(&c)) {
            Err(e) => emit(row.name, "fail", &format!("decode {e:?}")),
            Ok(d) => {
                let re = hexof(&encode(&d.to_cbor()));
                if d.n == pi(row.n) && d.by_id == by_id && re == row.cbor {
                    emit(row.name, "pass", "");
                } else {
                    emit(row.name, "fail", &format!("reencode {re}"));
                }
            }
        }
    }
    for row in ENCODE_FAIL {
        // i64 is the encode-side subset guard: an out-of-subset value is
        // unrepresentable, so this is satisfied by the type system.
        if row.value.parse::<i64>().is_err() {
            emit(row.name, "type-satisfied", "unrepresentable in i64");
        } else {
            emit(row.name, "fail", "value fits i64 but expected out-of-subset");
        }
    }
    for row in MALFORMED {
        match std::panic::catch_unwind(|| decode_row(row)) {
            Ok(Ok(again)) => emit(row.name, "ok", &hexof(&again)),
            Ok(Err(e)) => emit(row.name, "err", &describe(&e)),
            Err(payload) => emit(row.name, "untyped", &format!("panic: {}", panic_text(payload.as_ref()))),
        }
    }
}
'''


def _rs(value: str) -> str:
    """A Rust string literal (row names and hex are ASCII)."""
    return json.dumps(value)


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail, malformed = [], [], []
    for row in parity.int_rows():
        if row["kind"] == "round_trip":
            pairs = ", ".join(f"({_rs(k)}, {_rs(v)})" for k, v in row["value"]["by_id"])
            round_trip.append(f"    IntRow {{ name: {_rs(row['name'])}, cbor: {_rs(row['cbor'])}, "
                              f"n: {_rs(row['value']['n'])}, by_id: &[{pairs}] }},")
        else:
            encode_fail.append(f"    EncFail {{ name: {_rs(row['name'])}, value: {_rs(row['value']['n'])} }},")
    for row in parity.malformed_rows():
        malformed.append(f"    Mal {{ name: {_rs(row['name'])}, stage: {_rs(row['stage'])}, "
                         f"schema: {_rs(row.get('schema', ''))}, bytes: {_rs(row['bytes'])} }},")
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(malformed)


def _dispatch() -> tuple[str, str]:
    """The `match` arms for every message (`from_cbor`) and enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()
    from_cbor = [f"        {_rs(name)} => api::{name}::from_cbor(c).map(|v| encode(&v.to_cbor())),"
                 for name in dispatch.messages]
    from_wire = [f"        {_rs(name)} => api::{name}::from_wire(v).map(|_| ()),"
                 for name in dispatch.enums]
    return "\n".join(from_cbor), "\n".join(from_wire)


def _source(generated: Path) -> str:
    round_trip, encode_fail, malformed = _tables()
    from_cbor, from_wire = _dispatch()
    return (_MAIN
            .replace("@CBOR@", (generated / "cbor.rs").as_posix())
            .replace("@API@", (generated / "api.rs").as_posix())
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@MALFORMED@", malformed)
            .replace("@FROM_CBOR@", from_cbor)
            .replace("@FROM_WIRE@", from_wire))


def run(forward_compat: bool = False) -> parity.TargetReport:
    """The rust gate, or with `forward_compat` its `rust/fc` variant."""
    name = parity.variant(TARGET, forward_compat)
    rustc = toolchains.find_rustc()
    if rustc is None:
        return parity.skipped(name, "rustc not found")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(name, work, runtime=True, fail_closed=True)
        if failed is not None:
            return failed
        runner = work / "parity_runner.rs"
        runner.write_text(_source(work / TARGET))
        binary = work / "parity_runner"
        failed = parity.build(name, [rustc, "--edition", "2021", str(runner), "-o", str(binary)], cwd=work)
        if failed is not None:
            return failed
        return parity.run_runner(name, [str(binary)], cwd=work)
