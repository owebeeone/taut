"use strict";
// node example.js ABSOLUTE_API_PATH ABSOLUTE_CBOR_PATH
const assert = require("node:assert/strict");
const {Content,Kind,ContentDescriptor,Virtual} = require(process.argv[2]);
const codec = require(process.argv[3]);
const draft = new Content({kind:Kind.number,text:"also populated"});
const snapshot = draft.validate();
console.log("draft", snapshot.issues.map(i => ({code:i.code,path:i.path.map(s=>s.fieldName)})));
// Encoding preserves every populated payload; it never calls semantic validation.
const copy = Content.decode(codec.encode(draft.toCbor()));
assert.equal(copy.text,"also populated");assert.equal(copy.number,null);
draft.text=null;draft.number=0n;
assert.equal(draft.isValid(),true);assert.equal(snapshot.isValid(),false);
console.log("repaired",draft.isValid(),"descriptor fields",ContentDescriptor.fields.map(f=>f.name));
const virtual = new Virtual({child:draft});
console.log("virtual",{valid:virtual.validate().isValid(),complete:virtual.validate().isComplete(),fast:virtual.isValid()});
assert.equal(virtual.isValid(),false);
