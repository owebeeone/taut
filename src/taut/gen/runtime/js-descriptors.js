"use strict";
const {ConfigurationError, ownerToken, requireContract} = require("./contracts.js");
const codec = require("./cbor.js");
const fail = message => { throw new ConfigurationError(message); };
function requireCodec(loaded) {
  if (!loaded || codec.foundationCodecContract !== 1 || codec.foundationOwner !== ownerToken ||
      Object.keys(codec).some(name => loaded[name] !== codec[name])) fail("split/incompatible JavaScript codec owner; re-export the actual canonical codec");
}
// Maps are private-free frozen records, never frozen Map wrappers with live mutators.
function record(entries) { return Object.freeze(Object.assign(Object.create(null), Object.fromEntries(entries))); }
function snapshot(value) {
  if (value === null || ["string", "number", "boolean", "bigint", "undefined"].includes(typeof value)) return value;
  if (Array.isArray(value) || value instanceof Uint8Array) return Object.freeze(Array.from(value, snapshot));
  if (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null)
    return record(Object.entries(value).map(([k,v]) => [k,snapshot(v)]));
  fail("unsupported portable metadata value");
}
class TypeDescriptor {
  constructor(kind, reference = null, element = null, key = null, value = null) {
    Object.assign(this, {kind, reference, element, key, value});
    const expected = {int:[], str:[], bool:[], bytes:[], float:[], message:["reference"], enum:["reference"], list:["element"], map:["key","value"]};
    if (!Object.hasOwn(expected, kind) || JSON.stringify(["reference","element","key","value"].filter(k => this[k] !== null)) !== JSON.stringify(expected[kind])) fail("invalid TypeDescriptor");
    Object.freeze(this);
  }
}
class FieldDescriptor {
  constructor(name, attribute, number, type, presence, transient = false, virtual = false, options = {}) {
    Object.assign(this, {name, attribute, number, type, presence, transient, virtual, options:snapshot(options)}); Object.freeze(this);
  }
}
class EnumDescriptor {
  constructor(name, qualifiedName, members, options = {}, memberOptions = {}, fingerprint = "") {
    Object.assign(this, {name, qualifiedName, members:snapshot(members), options:snapshot(options), memberOptions:snapshot(memberOptions), fingerprint}); Object.freeze(this);
  }
}
class OneOfDescriptor {
  constructor(controllingField, enumeration, virtual, exhaustive, members) {
    Object.assign(this, {controllingField, enum:enumeration, virtual, exhaustive, members:snapshot(members)}); Object.freeze(this);
  }
}
class ConstraintDescriptor {
  constructor(rule, parameters = {}) { Object.assign(this, {rule, parameters:snapshot(parameters)}); Object.freeze(this); }
}
class MessageDescriptor {
  constructor(name, qualifiedName, descriptorContractVersion, fields, oneofs = [], constraints = [], reservedNumbers = [], reservedNames = [], nextId = null, options = {}, effectiveOptions = {}, fingerprint = "") {
    Object.assign(this, {name, qualifiedName, descriptorContractVersion, fields:Object.freeze([...fields]), oneofs:Object.freeze([...oneofs]), constraints:Object.freeze([...constraints]), reservedNumbers:snapshot(reservedNumbers), reservedNames:snapshot(reservedNames), nextId, options:snapshot(options), effectiveOptions:snapshot(effectiveOptions), fingerprint});
    this.fieldsByName = record(fields.map(f => [f.name,f])); this.groupsByField = record(oneofs.map(g => [g.controllingField,g])); Object.freeze(this);
  }
}
class SchemaDescriptor {
  constructor(descriptorContractVersion, irVersion, identity, messages, enums, options = {}, effectiveOptions = {}) {
    Object.assign(this, {descriptorContractVersion, irVersion, identity, messages:record(Object.entries(messages)), enums:record(Object.entries(enums)), options:snapshot(options), effectiveOptions:snapshot(effectiveOptions)}); Object.freeze(this);
  }
}
class SchemaBinding {
  constructor(schema, adapters, external = {}) {
    requireContract(schema.identity, undefined, schema.descriptorContractVersion);
    if (!(schema instanceof SchemaDescriptor) || ![1,2,3].includes(schema.irVersion) || codec.foundationOwner !== ownerToken || codec.foundationCodecContract !== 1) fail("incompatible schema/codec runtime owner/contract; regenerate/rebind");
    this.schema = schema;
    this.adapters = record(Object.entries(adapters).map(([name,a]) => [name,Object.freeze({type:a.type, read:record(Object.entries(a.read))})]));
    this.external = record(Object.entries(external));
    if (Object.keys(adapters).length !== Object.keys(schema.messages).length) fail("incomplete typed message bindings");
    const checkType = t => {
      if (!(t instanceof TypeDescriptor)) fail("incompatible TypeDescriptor owner");
      if (t.kind === "message" && !(schema.messages[t.reference] instanceof MessageDescriptor)) fail(`missing/wrong-category message ${t.reference}`);
      if (t.kind === "enum" && !(schema.enums[t.reference] instanceof EnumDescriptor)) fail(`missing/wrong-category enum ${t.reference}`);
      if (t.kind === "map" && !["str","int","bool"].includes(t.key.kind)) fail("invalid map key descriptor");
      for (const child of [t.element,t.key,t.value]) if (child !== null) checkType(child);
    };
    for (const [name,e] of Object.entries(schema.enums)) {
      if (!(e instanceof EnumDescriptor) || e.name !== name || !Object.keys(e.members).length || Object.values(e.members).some(v => typeof v !== "bigint" || v < -(1n<<63n) || v >= (1n<<63n))) fail(`invalid enum descriptor ${name}`);
    }
    for (const [name,d] of Object.entries(schema.messages)) {
      if (!(d instanceof MessageDescriptor) || d.name !== name || d.descriptorContractVersion !== 1) fail(`incompatible message descriptor ${name}`);
      const a = this.adapters[name];
      if (!a || typeof a.type !== "function") fail(`missing generated class binding ${name}`);
      if (Object.keys(d.fieldsByName).length !== d.fields.length || new Set(d.fields.map(f => f.number)).size !== d.fields.length || Object.keys(d.groupsByField).length !== d.oneofs.length) fail(`duplicate field/group ${name}`);
      let previous = 0;
      for (const f of d.fields) {
        if (!(f instanceof FieldDescriptor) || !Number.isSafeInteger(f.number) || f.number <= previous || !["required","nullable","missing_ok"].includes(f.presence) || typeof f.virtual !== "boolean" || typeof f.transient !== "boolean" || f.virtual !== (f.attribute === null) || (!f.virtual && typeof a.read[f.name] !== "function")) fail(`invalid field/accessor ${name}.${f.name}`);
        previous = f.number; checkType(f.type);
      }
      const payloads = new Set();
      for (const g of d.oneofs) {
        const ctrl = d.fieldsByName[g.controllingField];
        if (!(g instanceof OneOfDescriptor) || !ctrl || ctrl.type.kind !== "enum" || schema.enums[ctrl.type.reference] !== g.enum || typeof g.virtual !== "boolean" || typeof g.exhaustive !== "boolean" || ctrl.virtual !== g.virtual || ctrl.presence !== "required" || JSON.stringify(Object.keys(g.members).sort()) !== JSON.stringify(Object.keys(g.enum.members).sort())) fail(`invalid oneof links ${name}`);
        for (const payload of new Set(Object.values(g.members))) {
          if (payload === null) { if (g.exhaustive) fail("exhaustive group has payload-free choice"); continue; }
          if (!d.fieldsByName[payload] || d.fieldsByName[payload].presence === "required" || payloads.has(payload)) fail(`invalid/shared payload ${payload}`);
          payloads.add(payload);
        }
      }
      const controls = new Set();
      for (const c of d.constraints) {
        if (!(c instanceof ConstraintDescriptor) || c.rule !== "taut.oneof.v1" || Object.keys(c.parameters).join() !== "controlling_field" || !d.groupsByField[c.parameters.controlling_field] || controls.has(c.parameters.controlling_field)) fail("unsupported/dangling/duplicate constraint; regenerate/rebind");
        controls.add(c.parameters.controlling_field);
      }
      if (controls.size !== d.oneofs.length) fail("incomplete normalized constraints");
      if (this.external[name]) {
        const b = this.external[name];
        if (!(b instanceof SchemaBinding) || b.schema.messages[name] !== d || b.adapters[name].type !== a.type) fail(`split external owner ${name}`);
      }
    }
    Object.freeze(this);
  }
  checkDescriptor(descriptor) {
    if (!(descriptor instanceof MessageDescriptor) || this.schema.messages[descriptor.name] !== descriptor) fail("mismatched descriptor/binding owner");
  }
  bindingFor(name) { return this.external[name] || this; }
}
module.exports = Object.freeze({TypeDescriptor, FieldDescriptor, EnumDescriptor, OneOfDescriptor, ConstraintDescriptor, MessageDescriptor, SchemaDescriptor, SchemaBinding, requireCodec});
