// Tasks example — load the IR and round-trip a Task through the IR-driven codec.
// (TypeScript/JS use the runtime codec: instantiate from the IR JSON, zero codegen.)
// Run: node --experimental-strip-types example.ts
import { readFileSync } from "node:fs";
import { loadSchema } from "./schema.ts";
import { encode, decode } from "./codec.ts";

const ir = JSON.parse(readFileSync(new URL("../../tasks.ir.json", import.meta.url), "utf8"));
const schema = loadSchema(ir);
const task = {
  id: 1, title: "ship taut", state: "done",
  assignee: { id: 7, name: "ann" },
  comments: [{ author: { id: 2, name: "bob" }, text: "lgtm" }],
};
const bytes = encode(schema, "Task", task);
const back = decode(schema, "Task", bytes);
const ok = encode(schema, "Task", back).join() === bytes.join();
console.log(`typescript: Task round-tripped in ${bytes.length} bytes (${ok ? "ok" : "MISMATCH"})`);
