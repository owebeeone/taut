"use strict";
const {ConfigurationError, ownerToken, claimEngine} = require("./contracts.js");
const {SchemaBinding} = require("./descriptors.js");
const {PathSegment, ValidationIssue, DeferredCheck, ValidationReport} = require("./reports.js");
const cbor = require("./cbor.js");
const issue = (code,path,message,rule = "validation.shape.v1") => [false,code,rule,path,message];
function recursiveOption(options) {
  if (options === undefined) return true;
  if (options === null || typeof options !== "object" || Array.isArray(options) ||
      ![Object.prototype,null].includes(Object.getPrototypeOf(options)) ||
      Reflect.ownKeys(options).some(k => k !== "recursive") ||
      (Object.hasOwn(options,"recursive") && typeof options.recursive !== "boolean")) throw new TypeError("options must contain optional Boolean recursive");
  return Object.hasOwn(options,"recursive") ? options.recursive : true;
}
function read(value, binding, descriptor, field, path) {
  try {
    if (!Object.hasOwn(value,field.attribute)) return [undefined,issue("validation.type_mismatch",path,"generated field is uninitialized")];
    return [binding.adapters[descriptor.name].read[field.name](value),null];
  } catch (_) { return [undefined,issue("validation.type_mismatch",path,"cannot read generated field")]; }
}
function enumName(value, enumeration) {
  if (typeof value === "number" && Number.isSafeInteger(value)) value = BigInt(value);
  if (typeof value !== "bigint") return null;
  return Object.keys(enumeration.members).find(k => enumeration.members[k] === value) ?? null;
}
function* groupEvents(value, descriptor, binding, group, path) {
  const ctrl = descriptor.fieldsByName[group.controllingField], cp = [...path,PathSegment.forField(ctrl.name)];
  if (group.virtual) { yield [true,"oneof.virtual_deferred","taut.oneof.v1",cp,"virtual selection is deferred"]; return; }
  const [tag,error] = read(value,binding,descriptor,ctrl,cp), member = enumName(tag,group.enum);
  if (error || member === null) { yield issue("oneof.invalid_discriminator",cp,"expected controlling enum member","taut.oneof.v1"); return; }
  const selected = group.members[member], payloads = new Set(Object.values(group.members));
  for (const f of descriptor.fields) {
    if (!payloads.has(f.name)) continue;
    const fp = [...path,PathSegment.forField(f.name)], [payload,error] = read(value,binding,descriptor,f,fp);
    if (error) yield error;
    if (f.name === selected && payload == null) yield issue("oneof.payload_missing",fp,"selected payload is absent","taut.oneof.v1");
    else if (f.name !== selected && payload != null) yield issue("oneof.payload_unexpected",fp,"nonselected payload is present","taut.oneof.v1");
  }
}
function scalarMatches(kind,value) {
  if (kind === "int") return typeof value === "bigint" && value >= -(1n<<63n) && value < (1n<<63n);
  if (kind === "float") return typeof value === "number";
  if (kind === "bytes") return value instanceof Uint8Array;
  return typeof value === {str:"string",bool:"boolean"}[kind];
}
function* walkType(value,t,binding,path,ancestors) {
  if (t.kind === "message") {
    const child = binding.bindingFor(t.reference), d = child.schema.messages[t.reference];
    if (!(value instanceof child.adapters[t.reference].type)) { yield issue("validation.type_mismatch",path,"expected generated message"); return; }
    yield* walk(value,d,child,path,ancestors,true);
  } else if (t.kind === "list" || t.kind === "map") {
    if (!(t.kind === "list" ? Array.isArray(value) : value instanceof Map)) { yield issue("validation.type_mismatch",path,`expected ${t.kind}`); return; }
    if (ancestors.has(value)) { yield issue("validation.ownership_cycle",path,"active ancestor encountered"); return; }
    ancestors.add(value);
    try {
      if (t.kind === "list") {
        for (let i=0;i<value.length;i++) yield* walkType(value[i],t.element,binding,[...path,PathSegment.forIndex(i)],ancestors);
      } else {
        const entries = [];
        for (const [key,child] of value) {
          if (!scalarMatches(t.key.kind,key)) yield issue("validation.type_mismatch",path,"invalid map key type/range");
          else {
            const node = t.key.kind === "int" ? cbor.CInt(key) : t.key.kind === "str" ? cbor.CText(key) : cbor.CBool(key);
            entries.push([Buffer.from(cbor.encode(node)),child]);
          }
        }
        entries.sort((a,b) => Buffer.compare(a[0],b[0]));
        for (const [bytes,child] of entries) yield* walkType(child,t.value,binding,[...path,PathSegment.forKey(t.key.kind,bytes)],ancestors);
      }
    } finally { ancestors.delete(value); }
  } else if (t.kind === "enum") {
    if (enumName(value,binding.schema.enums[t.reference]) === null) yield issue("validation.type_mismatch",path,"expected generated enum member");
  } else if (!scalarMatches(t.kind,value)) yield issue("validation.type_mismatch",path,`expected ${t.kind}`);
}
function* walk(value,descriptor,binding,path,ancestors,recursive) {
  if (ancestors.has(value)) { yield issue("validation.ownership_cycle",path,"active ancestor encountered"); return; }
  ancestors.add(value);
  try {
    for (const f of descriptor.fields) {
      const group = descriptor.groupsByField[f.name];
      if (group) yield* groupEvents(value,descriptor,binding,group,path);
      if (recursive && !f.virtual && !group) {
        const fp = [...path,PathSegment.forField(f.name)], [child,error] = read(value,binding,descriptor,f,fp);
        if (error) yield error;
        else if (child != null) yield* walkType(child,f.type,binding,fp,ancestors);
      }
    }
  } finally { ancestors.delete(value); }
}
function* events(value,descriptor,binding,recursive) {
  if (!(binding instanceof SchemaBinding)) throw new ConfigurationError("expected shared SchemaBinding; rebind owner");
  binding.checkDescriptor(descriptor);
  if (!(value instanceof binding.adapters[descriptor.name].type)) { yield issue("validation.type_mismatch",[],"root does not match generated binding"); return; }
  yield* walk(value,descriptor,binding,[],new Set(),recursive);
}
function validateRecord(value,descriptor,binding,options) {
  const recursive = recursiveOption(options), issues = [], deferred = [];
  for (const [isDeferred,code,rule,path,message] of events(value,descriptor,binding,recursive)) {
    if (isDeferred) deferred.push(new DeferredCheck(rule,path,code,message));
    else issues.push(new ValidationIssue(code,rule,path,message));
  }
  return new ValidationReport(issues,deferred,recursive ? "recursive" : "local");
}
function isRecordValid(value,descriptor,binding,options) {
  const iterator = events(value,descriptor,binding,recursiveOption(options));
  try { return iterator.next().done; } finally { iterator.return(); }
}
claimEngine(validateRecord,isRecordValid);
module.exports = Object.freeze({validateRecord,isRecordValid,engineOwner:ownerToken,engineContract:1});
