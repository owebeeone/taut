//! Active extension helpers for forward-compatible Taut messages.
//!
//! Extensions ride in the top-level host map under reserved band tags. These
//! helpers know only CBOR, not the host schema; callers pass the generated
//! extension message's `to_cbor()` value and decode `ext_get()` with
//! `ExtMsg::from_cbor()`.

use crate::cbor::{decode, encode, Cbor};

const BAND_START: i64 = 1 << 20;

fn check_band(tag: i64) {
    if tag < BAND_START {
        panic!("extension tag {} is below the extension band", tag);
    }
}

fn host_map(host: &[u8]) -> Vec<(i64, Cbor)> {
    match decode(host) {
        Cbor::Map(m) => m,
        _ => panic!("extension host must be a top-level CBOR map"),
    }
}

pub fn ext_set(host: &[u8], tag: i64, value: Cbor) -> Vec<u8> {
    check_band(tag);
    let mut entries: Vec<(i64, Cbor)> = host_map(host)
        .into_iter()
        .filter(|(k, _)| *k != tag)
        .collect();
    entries.push((tag, value));
    encode(&Cbor::Map(entries))
}

pub fn ext_get(host: &[u8], tag: i64) -> Option<Cbor> {
    check_band(tag);
    for (k, v) in host_map(host) {
        if k == tag {
            return Some(v);
        }
    }
    None
}

pub fn ext_clear(host: &[u8], tag: i64) -> Vec<u8> {
    check_band(tag);
    let entries: Vec<(i64, Cbor)> = host_map(host)
        .into_iter()
        .filter(|(k, _)| *k != tag)
        .collect();
    encode(&Cbor::Map(entries))
}
