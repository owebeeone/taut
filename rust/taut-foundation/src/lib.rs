//! One nominal owner for the Taut Rust foundation. No compiler or shape engine.
#![no_std]
#![forbid(unsafe_code)]
extern crate alloc;

pub mod cbor;
pub use cbor::descriptors;
pub mod ext;
#[cfg(feature = "validation")]
pub mod validation;
