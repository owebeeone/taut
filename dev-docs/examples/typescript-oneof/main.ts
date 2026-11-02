import { Content, ContentDescriptor, type ContentFields, CODEC_SCHEMA } from "./typescript/api.ts";
import * as foundation from "FOUNDATION";

// Migration: a plain data object has no validation methods. Construct the enabled class.
const fields: ContentFields = {kind:"number",text:"an unfinished draft"};
const draft = new Content(fields);
const before = draft.validate();
if (draft.isValid() || before.issues.length !== 2) throw Error("expected invalid draft");
// Structural serialization retains every populated payload and never validates the selection.
const json = foundation.jsoncodec.toJsonValue(CODEC_SCHEMA,"Content",draft);
const bytes = foundation.codec.encode(CODEC_SCHEMA,"Content",draft);
draft.text = null;
draft.number = 0n; // zero is present
const after = draft.validate();
if (!draft.isValid() || !after.isValid() || !after.isComplete()) throw Error("expected repaired content");
if (Content.descriptor() !== ContentDescriptor || !Object.isFrozen(ContentDescriptor.fields)) throw Error("metadata identity");
console.log(JSON.stringify({
  before:before.issues.map(issue=>({code:issue.code,path:issue.path.map(segment=>segment.fieldName)})),
  json, cborBytes:bytes.length, after:{valid:after.isValid(),complete:after.isComplete(),scope:after.scope},
  fields:ContentDescriptor.fields.map(field=>field.name),
}));
