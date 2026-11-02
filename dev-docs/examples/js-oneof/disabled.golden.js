"use strict";
// GENERATED native JavaScript types + codec; mandatory descriptor ABI 1.
const $tautCodec = require("./cbor.js");
const { CInt, CFloat, CText, CBytes, CBool, CArr, CMap, CNull, cget, cgetOrNull, mapFromCbor, cmapEntries, compareCodePoints, isNull, expectInt, expectFloat, expectText, expectBytes, expectBool, expectArray, expectMap, enumFromWire, enumFromCbor, decode } = $tautCodec;
const $tautD = require("./descriptors.js");
const $tautC = require("./contracts.js");
$tautC.requireContract("schema_fbbfcaa31eceac80", "taut.javascript.foundation", 1, 1, ["codec.v1", "descriptors.v1", "oneof.v1"]);
if (typeof $tautD.requireCodec !== "function") throw new $tautC.ConfigurationError("compatible JavaScript codec/descriptor foundation required; regenerate/rebind");
$tautD.requireCodec($tautCodec);
const Kind = Object.freeze(Object.fromEntries([["text", 0], ["number", 1], ["empty", 2], ["child", 3], ["flag", 4], ["items", 5]]));
const KindValues = new Set([0, 1, 2, 3, 4, 5]);
function KindFromWire(v) { return enumFromWire(v, "Kind", KindValues); }
function KindFromCbor(c) { return enumFromCbor(c, "Kind", KindValues); }

class Content {
  static get MAX_DEPTH() { return 32; }
  static get MAX_ENCODED_LEN() { return null; }
  constructor(o = {}) {
    Object.defineProperty(this, "kind", {value:o["kind"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "text", {value:o["text"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "number", {value:o["number"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "child", {value:o["child"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "flag", {value:o["flag"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "items", {value:o["items"], writable:true, enumerable:true, configurable:true});
  }
  static descriptor() { return ContentDescriptor; }
  toCbor() {
    const m = [
      [1, CInt(this["kind"])],
      [2, (this["text"] != null ? CText(this["text"]) : CNull())],
      [3, (this["number"] != null ? CInt(this["number"]) : CNull())],
      [4, (this["child"] != null ? this["child"].toCbor() : CNull())],
      [5, (this["flag"] != null ? CBool(this["flag"]) : CNull())],
      [6, (this["items"] != null ? CArr(this["items"].map((e) => CInt(e))) : CNull())],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new Content();
    v["kind"] = KindFromCbor(cget(c, 1));
    { const f = cget(c, 2); v["text"] = isNull(f) ? null : expectText(f); }
    { const f = cget(c, 3); v["number"] = isNull(f) ? null : expectInt(f); }
    { const f = cget(c, 4); v["child"] = isNull(f) ? null : Content.fromCbor(f); }
    { const f = cget(c, 5); v["flag"] = isNull(f) ? null : expectBool(f); }
    { const f = cget(c, 6); v["items"] = isNull(f) ? null : expectArray(f).map((e) => expectInt(e)); }
    return v;
  }
  static decode(bytes) {
    return Content.fromCbor(decode(bytes, { maxDepth: Content.MAX_DEPTH, maxEncodedLen: Content.MAX_ENCODED_LEN }));
  }
}

class Wrapper {
  static get MAX_DEPTH() { return 32; }
  static get MAX_ENCODED_LEN() { return null; }
  constructor(o = {}) {
    Object.defineProperty(this, "child", {value:o["child"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "children", {value:o["children"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "by_text", {value:o["by_text"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "by_int", {value:o["by_int"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "by_bool", {value:o["by_bool"], writable:true, enumerable:true, configurable:true});
  }
  static descriptor() { return WrapperDescriptor; }
  toCbor() {
    const m = [
      [1, this["child"].toCbor()],
      [2, CArr(this["children"].map((e) => e.toCbor()))],
      [3, CArr([...this["by_text"].entries()].sort((a, b) => compareCodePoints(a[0], b[0])).map(([k, v]) => CMap([[1, CText(k)], [2, v.toCbor()]])))],
      [4, CArr([...this["by_int"].entries()].sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0).map(([k, v]) => CMap([[1, CInt(k)], [2, v.toCbor()]])))],
      [5, CArr([...this["by_bool"].entries()].sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0).map(([k, v]) => CMap([[1, CBool(k)], [2, v.toCbor()]])))],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new Wrapper();
    v["child"] = Content.fromCbor(cget(c, 1));
    v["children"] = expectArray(cget(c, 2)).map((e) => Content.fromCbor(e));
    v["by_text"] = mapFromCbor(new Map(), cget(c, 3), (key) => expectText(key), (value) => Content.fromCbor(value));
    v["by_int"] = mapFromCbor(new Map(), cget(c, 4), (key) => expectInt(key), (value) => Content.fromCbor(value));
    v["by_bool"] = mapFromCbor(new Map(), cget(c, 5), (key) => expectBool(key), (value) => Content.fromCbor(value));
    return v;
  }
  static decode(bytes) {
    return Wrapper.fromCbor(decode(bytes, { maxDepth: Wrapper.MAX_DEPTH, maxEncodedLen: Wrapper.MAX_ENCODED_LEN }));
  }
}

class Virtual {
  static get MAX_DEPTH() { return 32; }
  static get MAX_ENCODED_LEN() { return null; }
  constructor(o = {}) {
    Object.defineProperty(this, "text", {value:o["text"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "child", {value:o["child"], writable:true, enumerable:true, configurable:true});
  }
  static descriptor() { return VirtualDescriptor; }
  toCbor() {
    const m = [
      [2, (this["text"] != null ? CText(this["text"]) : CNull())],
      [3, this["child"].toCbor()],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new Virtual();
    { const f = cget(c, 2); v["text"] = isNull(f) ? null : expectText(f); }
    v["child"] = Content.fromCbor(cget(c, 3));
    return v;
  }
  static decode(bytes) {
    return Virtual.fromCbor(decode(bytes, { maxDepth: Virtual.MAX_DEPTH, maxEncodedLen: Virtual.MAX_ENCODED_LEN }));
  }
}

class Multi {
  static get MAX_DEPTH() { return 32; }
  static get MAX_ENCODED_LEN() { return null; }
  constructor(o = {}) {
    Object.defineProperty(this, "left", {value:o["left"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "right", {value:o["right"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "a", {value:o["a"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "b", {value:o["b"], writable:true, enumerable:true, configurable:true});
  }
  static descriptor() { return MultiDescriptor; }
  toCbor() {
    const m = [
      [1, CInt(this["left"])],
      [2, CInt(this["right"])],
      [3, (this["a"] != null ? CText(this["a"]) : CNull())],
      [4, (this["b"] != null ? CInt(this["b"]) : CNull())],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new Multi();
    v["left"] = KindFromCbor(cget(c, 1));
    v["right"] = KindFromCbor(cget(c, 2));
    { const f = cget(c, 3); v["a"] = isNull(f) ? null : expectText(f); }
    { const f = cget(c, 4); v["b"] = isNull(f) ? null : expectInt(f); }
    return v;
  }
  static decode(bytes) {
    return Multi.fromCbor(decode(bytes, { maxDepth: Multi.MAX_DEPTH, maxEncodedLen: Multi.MAX_ENCODED_LEN }));
  }
}

class Plain {
  static get MAX_DEPTH() { return 32; }
  static get MAX_ENCODED_LEN() { return null; }
  constructor(o = {}) {
    Object.defineProperty(this, "value", {value:o["value"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "blob", {value:o["blob"], writable:true, enumerable:true, configurable:true});
    Object.defineProperty(this, "ratio", {value:o["ratio"], writable:true, enumerable:true, configurable:true});
  }
  static descriptor() { return PlainDescriptor; }
  toCbor() {
    const m = [
      [1, CInt(this["value"])],
      [2, (this["blob"] != null ? CBytes(this["blob"]) : CNull())],
      [3, (this["ratio"] != null ? CFloat(this["ratio"]) : CNull())],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new Plain();
    v["value"] = expectInt(cget(c, 1));
    { const f = cget(c, 2); v["blob"] = isNull(f) ? null : expectBytes(f); }
    { const f = cget(c, 3); v["ratio"] = isNull(f) ? null : expectFloat(f); }
    return v;
  }
  static decode(bytes) {
    return Plain.fromCbor(decode(bytes, { maxDepth: Plain.MAX_DEPTH, maxEncodedLen: Plain.MAX_ENCODED_LEN }));
  }
}

const KindDescriptor = new $tautD.EnumDescriptor("Kind", "schema_fbbfcaa31eceac80.Kind", Object.fromEntries([["text", 0n], ["number", 1n], ["empty", 2n], ["child", 3n], ["flag", 4n], ["items", 5n]]), Object.fromEntries([]), Object.fromEntries([["text", Object.fromEntries([])], ["number", Object.fromEntries([])], ["empty", Object.fromEntries([])], ["child", Object.fromEntries([])], ["flag", Object.fromEntries([])], ["items", Object.fromEntries([])]]), "3ad3851b62312a8d3e291ef91477fe455bac1716dd270507bb78ee6c1172db6e");
const ContentDescriptor = new $tautD.MessageDescriptor("Content", "schema_fbbfcaa31eceac80.Content", 1, [new $tautD.FieldDescriptor("kind", "kind", 1, new $tautD.TypeDescriptor("enum", "Kind"), "required", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("text", "text", 2, new $tautD.TypeDescriptor("str"), "nullable", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("number", "number", 3, new $tautD.TypeDescriptor("int"), "nullable", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("child", "child", 4, new $tautD.TypeDescriptor("message", "Content"), "nullable", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("flag", "flag", 5, new $tautD.TypeDescriptor("bool"), "nullable", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("items", "items", 6, new $tautD.TypeDescriptor("list", null, new $tautD.TypeDescriptor("int")), "nullable", false, false, Object.fromEntries([]))], [new $tautD.OneOfDescriptor("kind", KindDescriptor, false, false, Object.fromEntries([["text", "text"], ["number", "number"], ["empty", null], ["child", "child"], ["flag", "flag"], ["items", "items"]]))], [new $tautD.ConstraintDescriptor("taut.oneof.v1", Object.fromEntries([["controlling_field", "kind"]]))], [7], ["retired"], 9, Object.fromEntries([]), Object.fromEntries([["max_depth", 32], ["max_encoded_len", null]]), "d50a6ebd679c9d74bed58b33db4521be66a80919d5b88c25487e3e571bdff023");
const WrapperDescriptor = new $tautD.MessageDescriptor("Wrapper", "schema_fbbfcaa31eceac80.Wrapper", 1, [new $tautD.FieldDescriptor("child", "child", 1, new $tautD.TypeDescriptor("message", "Content"), "required", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("children", "children", 2, new $tautD.TypeDescriptor("list", null, new $tautD.TypeDescriptor("message", "Content")), "required", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("by_text", "by_text", 3, new $tautD.TypeDescriptor("map", null, null, new $tautD.TypeDescriptor("str"), new $tautD.TypeDescriptor("message", "Content")), "required", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("by_int", "by_int", 4, new $tautD.TypeDescriptor("map", null, null, new $tautD.TypeDescriptor("int"), new $tautD.TypeDescriptor("message", "Content")), "required", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("by_bool", "by_bool", 5, new $tautD.TypeDescriptor("map", null, null, new $tautD.TypeDescriptor("bool"), new $tautD.TypeDescriptor("message", "Content")), "required", false, false, Object.fromEntries([]))], [], [], [], [], null, Object.fromEntries([]), Object.fromEntries([["max_depth", 32], ["max_encoded_len", null]]), "7aab4615d8deb5388ba8dd4ef7cf4a2948446c53c34f12a3ac3aa4ad4ef0d0cb");
const VirtualDescriptor = new $tautD.MessageDescriptor("Virtual", "schema_fbbfcaa31eceac80.Virtual", 1, [new $tautD.FieldDescriptor("kind", null, 1, new $tautD.TypeDescriptor("enum", "Kind"), "required", false, true, Object.fromEntries([])), new $tautD.FieldDescriptor("text", "text", 2, new $tautD.TypeDescriptor("str"), "nullable", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("child", "child", 3, new $tautD.TypeDescriptor("message", "Content"), "required", false, false, Object.fromEntries([]))], [new $tautD.OneOfDescriptor("kind", KindDescriptor, true, false, Object.fromEntries([["text", "text"], ["number", null], ["empty", null], ["child", null], ["flag", null], ["items", null]]))], [new $tautD.ConstraintDescriptor("taut.oneof.v1", Object.fromEntries([["controlling_field", "kind"]]))], [], [], null, Object.fromEntries([]), Object.fromEntries([["max_depth", 32], ["max_encoded_len", null]]), "9a97979761a5a4b18d847760134abc33fb008c74d6bd6ab4e151414a7b035a94");
const MultiDescriptor = new $tautD.MessageDescriptor("Multi", "schema_fbbfcaa31eceac80.Multi", 1, [new $tautD.FieldDescriptor("left", "left", 1, new $tautD.TypeDescriptor("enum", "Kind"), "required", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("right", "right", 2, new $tautD.TypeDescriptor("enum", "Kind"), "required", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("a", "a", 3, new $tautD.TypeDescriptor("str"), "nullable", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("b", "b", 4, new $tautD.TypeDescriptor("int"), "nullable", false, false, Object.fromEntries([]))], [new $tautD.OneOfDescriptor("left", KindDescriptor, false, false, Object.fromEntries([["text", "a"], ["number", null], ["empty", null], ["child", null], ["flag", null], ["items", null]])), new $tautD.OneOfDescriptor("right", KindDescriptor, false, false, Object.fromEntries([["text", null], ["number", "b"], ["empty", null], ["child", null], ["flag", null], ["items", null]]))], [new $tautD.ConstraintDescriptor("taut.oneof.v1", Object.fromEntries([["controlling_field", "left"]])), new $tautD.ConstraintDescriptor("taut.oneof.v1", Object.fromEntries([["controlling_field", "right"]]))], [], [], null, Object.fromEntries([]), Object.fromEntries([["max_depth", 32], ["max_encoded_len", null]]), "fe44c71f1c4d5e6c1c59978641317793c5118e98a6ea967bd0b4b645d830646c");
const PlainDescriptor = new $tautD.MessageDescriptor("Plain", "schema_fbbfcaa31eceac80.Plain", 1, [new $tautD.FieldDescriptor("value", "value", 1, new $tautD.TypeDescriptor("int"), "required", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("blob", "blob", 2, new $tautD.TypeDescriptor("bytes"), "nullable", false, false, Object.fromEntries([])), new $tautD.FieldDescriptor("ratio", "ratio", 3, new $tautD.TypeDescriptor("float"), "nullable", false, false, Object.fromEntries([]))], [], [], [], [], null, Object.fromEntries([]), Object.fromEntries([["max_depth", 32], ["max_encoded_len", null]]), "d1e39990ba19514eeadde8435b33567c83cf6ea874efa2e8dd8bc3a89627085b");
const $tautSchema = new $tautD.SchemaDescriptor(1, 3, "schema_fbbfcaa31eceac80", Object.fromEntries([["Content", ContentDescriptor], ["Wrapper", WrapperDescriptor], ["Virtual", VirtualDescriptor], ["Multi", MultiDescriptor], ["Plain", PlainDescriptor]]), Object.fromEntries([["Kind", KindDescriptor]]), Object.fromEntries([]), Object.fromEntries([["max_depth", 32], ["max_encoded_len", null]]));
const $tautBinding = new $tautD.SchemaBinding($tautSchema, Object.fromEntries([["Content", {type:Content, read:Object.fromEntries([["kind", ($self) => $self["kind"]], ["text", ($self) => $self["text"]], ["number", ($self) => $self["number"]], ["child", ($self) => $self["child"]], ["flag", ($self) => $self["flag"]], ["items", ($self) => $self["items"]]])}], ["Wrapper", {type:Wrapper, read:Object.fromEntries([["child", ($self) => $self["child"]], ["children", ($self) => $self["children"]], ["by_text", ($self) => $self["by_text"]], ["by_int", ($self) => $self["by_int"]], ["by_bool", ($self) => $self["by_bool"]]])}], ["Virtual", {type:Virtual, read:Object.fromEntries([["text", ($self) => $self["text"]], ["child", ($self) => $self["child"]]])}], ["Multi", {type:Multi, read:Object.fromEntries([["left", ($self) => $self["left"]], ["right", ($self) => $self["right"]], ["a", ($self) => $self["a"]], ["b", ($self) => $self["b"]]])}], ["Plain", {type:Plain, read:Object.fromEntries([["value", ($self) => $self["value"]], ["blob", ($self) => $self["blob"]], ["ratio", ($self) => $self["ratio"]]])}]]), Object.fromEntries([]));
module.exports = Object.freeze(Object.fromEntries([["Kind", Kind], ["KindFromWire", KindFromWire], ["KindFromCbor", KindFromCbor], ["KindDescriptor", KindDescriptor], ["Content", Content], ["ContentDescriptor", ContentDescriptor], ["Wrapper", Wrapper], ["WrapperDescriptor", WrapperDescriptor], ["Virtual", Virtual], ["VirtualDescriptor", VirtualDescriptor], ["Multi", Multi], ["MultiDescriptor", MultiDescriptor], ["Plain", Plain], ["PlainDescriptor", PlainDescriptor], ["$tautBinding", $tautBinding], ["$tautSchema", $tautSchema]]));
