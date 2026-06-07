// Tasks example — build a Task, round-trip it through the generated codec.
// Run: rustc example.rs -o example && ./example
mod cbor;
mod api;
use api::*;
use cbor::{decode, encode};

fn main() {
    let task = Task {
        id: 1,
        title: "ship taut".into(),
        state: TaskState::Done,
        assignee: Some(User { id: 7, name: "ann".into() }),
        comments: vec![Comment { author: User { id: 2, name: "bob".into() }, text: "lgtm".into() }],
    };
    let bytes = encode(&task.to_cbor());
    let back = Task::from_cbor(&decode(&bytes));
    assert_eq!(back, task);
    println!("rust: Task round-tripped in {} bytes (ok)", bytes.len());
}
