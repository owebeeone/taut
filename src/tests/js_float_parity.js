"use strict";

const fs = require("fs");
const path = require("path");
const { CFloat, encode, decode } = require("../taut/gen/runtime/cbor.js");

const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, "../../corpus/float_vectors.json"), "utf8"));
const view = new DataView(new ArrayBuffer(8));

function bytesFromHex(hex) {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}

function hexFromBytes(bytes) {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function f64FromHex(hex) {
  const bytes = bytesFromHex(hex);
  for (let i = 0; i < 8; i++) view.setUint8(i, bytes[i]);
  return view.getFloat64(0, false);
}

function f64Hex(value) {
  view.setFloat64(0, value, false);
  return Array.from({ length: 8 }, (_, i) => view.getUint8(i).toString(16).padStart(2, "0")).join("");
}

for (const row of vectors) {
  const value = f64FromHex(row.f64);
  const encoded = hexFromBytes(encode(CFloat(value)));
  if (encoded !== row.cbor) {
    throw new Error(`${row.note}: encode got ${encoded}, want ${row.cbor}`);
  }

  const decoded = decode(bytesFromHex(row.cbor));
  const reencoded = hexFromBytes(encode(decoded));
  if (reencoded !== row.cbor) {
    throw new Error(`${row.note}: re-encode got ${reencoded}, want ${row.cbor}`);
  }

  if (!row.note.startsWith("nan")) {
    const got = f64Hex(decoded.f);
    if (got !== row.f64) throw new Error(`${row.note}: decode bits got ${got}, want ${row.f64}`);
  }
}

for (const [label, hex] of [["half", "f93e00"], ["single", "fa3fc00000"], ["double", "fb3ff8000000000000"]]) {
  const decoded = decode(bytesFromHex(hex));
  const got = f64Hex(decoded.f);
  if (got !== "3ff8000000000000") throw new Error(`${label}: decode bits got ${got}`);
  const reencoded = hexFromBytes(encode(decoded));
  if (reencoded !== "f93e00") throw new Error(`${label}: re-encode got ${reencoded}`);
}

console.log(`js float parity: ${vectors.length} vectors ok`);
