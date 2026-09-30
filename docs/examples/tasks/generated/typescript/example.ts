// Tasks example — load the IR and round-trip a Task through the IR-driven codec.
// (TypeScript uses the runtime codec: instantiate from the IR JSON, zero codegen.)
// Run: node --experimental-strip-types example.ts
import { readFileSync } from "node:fs";
import { DecodeError } from "./cbor.ts";
import { decode, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const ir = JSON.parse(readFileSync(new URL("../../tasks.ir.json", import.meta.url), "utf8"));
const schema = loadSchema(ir);
const task = {
  id: 1n, title: "ship taut", state: "done",
  assignee: { id: 7n, name: "ann" },
  comments: [{ author: { id: 2n, name: "bob" }, text: "lgtm" }],
  labels: new Map([["team", "infra"], ["area", "wire"]]),
};
const bytes = encode(schema, "Task", task);
// The typed decode, under Task's bounds from the IR's `effective` (schema.effective("Task")).
const back = decode(schema, "Task", bytes);
let ok = encode(schema, "Task", back).join() === bytes.join();
// Decode is fail-closed: bytes cut short throw DecodeError, nothing else.
try {
  decode(schema, "Task", bytes.subarray(0, bytes.length - 1));
  ok = false;
} catch (e) {
  ok = ok && e instanceof DecodeError && e.tag === "Truncated";
}
console.log(`typescript: Task round-tripped in ${bytes.length} bytes (${ok ? "ok" : "MISMATCH"})`);
if (!ok) {
  process.exitCode = 1;
}
