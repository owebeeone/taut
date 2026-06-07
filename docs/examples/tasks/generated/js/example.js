"use strict";
// Tasks example — build a Task, round-trip it through the generated codec.
// Run: node example.js
const { Task, Comment, User, TaskState } = require("./api.js");
const { encode, decode } = require("./cbor.js");

const task = new Task({
  id: 1, title: "ship taut", state: TaskState.done,
  assignee: new User({ id: 7, name: "ann" }),
  comments: [new Comment({ author: new User({ id: 2, name: "bob" }), text: "lgtm" })],
});
const bytes = encode(task.toCbor());
const back = Task.fromCbor(decode(bytes));
const ok = Buffer.compare(Buffer.from(encode(back.toCbor())), Buffer.from(bytes)) === 0;
console.log(`js: Task round-tripped in ${bytes.length} bytes (${ok ? "ok" : "MISMATCH"})`);
