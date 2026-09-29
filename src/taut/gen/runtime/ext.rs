//! Active extension helpers for forward-compatible Taut messages.
//!
//! Extensions ride in the top-level host map under reserved band tags. These
//! helpers know only CBOR, not the host schema; callers pass the generated
//! extension message's `to_cbor()` value and decode `ext_get()`'s value with
//! `ExtMsg::from_cbor()`.
//!
//! They fail closed (TautCheckedDecode.md CD-E4): whatever the host bytes, each
//! returns its result or a [`DecodeError`], and a host that is not a map is
//! `WrongType { expected: "map" }`. A tag below the extension band is the
//! caller's error, not the input's, so each panics on one, before it reads the
//! host.

use crate::cbor::{encode, try_decode, Cbor, DecodeError};

const BAND_START: i64 = 1 << 20;

fn check_band(tag: i64) {
    if tag < BAND_START {
        panic!("extension tag {} is below the extension band", tag);
    }
}

/// The host's top-level map entries; a host that is not a map is
/// `WrongType { expected: "map" }`.
fn host_map(host: &[u8]) -> Result<Vec<(i64, Cbor)>, DecodeError> {
    // TODO(D1): read the host at the depth ceiling with no length bound, the
    // only bounds every valid host meets (TautOptions.md G3), once D1 gives the
    // raw decode its depth parameter.
    match try_decode(host)? {
        Cbor::Map(m) => Ok(m),
        _ => Err(DecodeError::WrongType { expected: "map" }),
    }
}

/// The host with `value` riding at `tag`, in place of any value already there.
///
/// # Panics
///
/// If `tag` is below the extension band.
pub fn ext_set(host: &[u8], tag: i64, value: Cbor) -> Result<Vec<u8>, DecodeError> {
    check_band(tag);
    let mut entries: Vec<(i64, Cbor)> = host_map(host)?
        .into_iter()
        .filter(|(k, _)| *k != tag)
        .collect();
    entries.push((tag, value));
    Ok(encode(&Cbor::Map(entries)))
}

/// The value riding at `tag`, or `None` when the host has none.
///
/// # Panics
///
/// If `tag` is below the extension band.
pub fn ext_get(host: &[u8], tag: i64) -> Result<Option<Cbor>, DecodeError> {
    check_band(tag);
    for (k, v) in host_map(host)? {
        if k == tag {
            return Ok(Some(v));
        }
    }
    Ok(None)
}

/// The host without the value at `tag`.
///
/// # Panics
///
/// If `tag` is below the extension band.
pub fn ext_clear(host: &[u8], tag: i64) -> Result<Vec<u8>, DecodeError> {
    check_band(tag);
    let entries: Vec<(i64, Cbor)> = host_map(host)?
        .into_iter()
        .filter(|(k, _)| *k != tag)
        .collect();
    Ok(encode(&Cbor::Map(entries)))
}
