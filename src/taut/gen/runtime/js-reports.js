"use strict";
const cbor = require("./cbor.js");
const strings = (...values) => { if (values.some(v => typeof v !== "string")) throw new TypeError("diagnostic fields must be strings"); };
class PathSegment {
  constructor(kind, fieldName = null, index = null, keyType = null, keyCborBase64 = null) {
    let good = false;
    if (kind === "field") good = typeof fieldName === "string" && index === null && keyType === null && keyCborBase64 === null;
    if (kind === "index") good = Number.isSafeInteger(index) && index >= 0 && fieldName === null && keyType === null && keyCborBase64 === null;
    if (kind === "key" && fieldName === null && index === null && ["str","int","bool"].includes(keyType) && typeof keyCborBase64 === "string") {
      try {
        const bytes = Buffer.from(keyCborBase64, "base64"), value = cbor.decode(bytes);
        const expected = {str:cbor.CText("" ).kind, int:cbor.CInt(0n).kind, bool:cbor.CBool(false).kind}[keyType];
        good = bytes.toString("base64") === keyCborBase64 && value.kind === expected && Buffer.from(cbor.encode(value)).equals(bytes);
      } catch (_) { good = false; }
    }
    if (!good) throw new TypeError("invalid validation path segment");
    Object.assign(this, {kind, fieldName, index, keyType, keyCborBase64}); Object.freeze(this);
  }
  static forField(name) { return new PathSegment("field", name); }
  static forIndex(index) { return new PathSegment("index", null, index); }
  static forKey(type, bytes) { return new PathSegment("key", null, null, type, Buffer.from(bytes).toString("base64")); }
}
function pathSnapshot(path) {
  const result = [...path];
  if (result.some(p => !(p instanceof PathSegment))) throw new TypeError("path requires shared immutable PathSegments");
  return Object.freeze(result);
}
class ValidationIssue {
  constructor(code, rule, path, message) { strings(code,rule,message); Object.assign(this, {code,rule,path:pathSnapshot(path),message}); Object.freeze(this); }
}
class DeferredCheck {
  constructor(rule, path, reasonCode, message) { strings(rule,reasonCode,message); Object.assign(this, {rule,path:pathSnapshot(path),reasonCode,message}); Object.freeze(this); }
}
class ValidationReport {
  constructor(issues = [], deferredChecks = [], scope = "recursive") {
    const i = [...issues], d = [...deferredChecks];
    if (!["local","recursive"].includes(scope) || i.some(v => !(v instanceof ValidationIssue)) || d.some(v => !(v instanceof DeferredCheck))) throw new TypeError("invalid shared ValidationReport");
    Object.assign(this, {issues:Object.freeze(i),deferredChecks:Object.freeze(d),scope}); Object.freeze(this);
  }
  isValid() { return this.issues.length === 0; }
  isComplete() { return this.deferredChecks.length === 0; }
}
module.exports = Object.freeze({PathSegment, ValidationIssue, DeferredCheck, ValidationReport});
