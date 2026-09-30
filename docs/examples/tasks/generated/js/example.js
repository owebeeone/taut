"use strict";
// Tasks example — build a Task, round-trip it through the generated codec.
// Run: node example.js
const { Task, Comment, User, TaskState } = require("./api.js");
const { DecodeError, encode } = require("./cbor.js");

const task = new Task({
  id: 1, title: "ship taut", state: TaskState.done,
  assignee: new User({ id: 7, name: "ann" }),
  comments: [new Comment({ author: new User({ id: 2, name: "bob" }), text: "lgtm" })],
  labels: new Map([["team", "infra"], ["area", "wire"]]),
});
const bytes = encode(task.toCbor());
// The typed decode from bytes, under Task's bounds (Task.MAX_DEPTH, Task.MAX_ENCODED_LEN).
const back = Task.decode(bytes);
let ok = Buffer.compare(Buffer.from(encode(back.toCbor())), Buffer.from(bytes)) === 0;
// Decode is fail-closed: bytes cut short throw DecodeError, nothing else.
try {
  Task.decode(bytes.subarray(0, bytes.length - 1));
  ok = false;
} catch (e) {
  ok = ok && e instanceof DecodeError && e.tag === "Truncated";
}
console.log(`js: Task round-tripped in ${bytes.length} bytes (${ok ? "ok" : "MISMATCH"})`);
if (!ok) {
  process.exitCode = 1;
}
