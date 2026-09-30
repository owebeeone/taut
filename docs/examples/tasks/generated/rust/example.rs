// Tasks example — build a Task, round-trip it through the generated codec.
// Run: rustc --edition 2021 example.rs -o example && ./example
extern crate alloc; // cbor.rs uses `alloc`, so it builds in a no_std crate too
mod api;
#[allow(dead_code)] // the example uses only part of the runtime
mod cbor;
use api::*;
use cbor::{encode, DecodeError};

fn main() {
    let task = Task {
        id: 1,
        title: "ship taut".into(),
        state: TaskState::Done,
        assignee: Some(User { id: 7, name: "ann".into() }),
        comments: vec![Comment { author: User { id: 2, name: "bob".into() }, text: "lgtm".into() }],
        labels: std::collections::BTreeMap::from([("team".to_string(), "infra".to_string()), ("area".to_string(), "wire".to_string())]),
    };
    let bytes = encode(&task.to_cbor());
    // The typed decode from bytes, under Task's bounds (Task::MAX_DEPTH, Task::MAX_ENCODED_LEN).
    let back = Task::decode(&bytes);
    let same = match &back {
        Ok(t) => *t == task && encode(&t.to_cbor()) == bytes,
        Err(_) => false,
    };
    // Decode is fail-closed: bytes cut short are a DecodeError, never a panic.
    let cut = Task::decode(&bytes[..bytes.len() - 1]);
    let ok = same && cut == Err(DecodeError::Truncated);
    println!("rust: Task round-tripped in {} bytes ({})", bytes.len(), if ok { "ok" } else { "MISMATCH" });
    if !ok {
        std::process::exit(1);
    }
}
