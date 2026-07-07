// IR-driven codec — native value <-> CBOR bytes, driven by the schema. The
// TypeScript mirror of taut/src/taut/wire/codec.py. A "native value" is a
// plain object keyed by field name (enums as member-name strings, bytes as
// Uint8Array). The wire is a projection of the tagged subset: messages -> CBOR
// maps keyed by field tag, transient fields skipped, optionals always emitted
// (null when absent).

import {
  CborFloat,
  DecodeError,
  EncodeError,
  I64_MAX,
  I64_MIN,
  type CborValue,
  decode as cborDecode,
  encode as cborEncode,
} from "./cbor.ts";
import { type SchemaIndex, type TypeRef } from "./schema.ts";

// deno-lint friendly: native values are dynamic by nature.
type Native = any; // eslint-disable-line @typescript-eslint/no-explicit-any

function wrong(expected: string): never {
  throw new DecodeError("WrongType", { expected });
}

function intToWire(value: Native): bigint {
  let n: bigint;
  if (typeof value === "bigint") {
    n = value;
  } else if (typeof value === "number" && Number.isSafeInteger(value)) {
    n = BigInt(value);
  } else {
    throw new EncodeError(String(value));
  }
  if (n < I64_MIN || n > I64_MAX) throw new EncodeError(n);
  return n;
}

function mapEntries(value: Native): [Native, Native][] {
  if (value instanceof Map) return [...value.entries()];
  throw new Error("taut map values must be Map instances in TypeScript");
}

function compareNativeKey(a: Native, b: Native): number {
  if (typeof a === "bigint" && typeof b === "bigint") return a < b ? -1 : a > b ? 1 : 0;
  if (typeof a === "number" && typeof b === "number") return a - b;
  const as = String(a);
  const bs = String(b);
  return as < bs ? -1 : as > bs ? 1 : 0;
}

function toWire(schema: SchemaIndex, t: TypeRef, value: Native): CborValue {
  switch (t.k) {
    case "scalar":
      if (t.scalar === "int") return intToWire(value);
      if (t.scalar === "float") return new CborFloat(Number(value));
      if (t.scalar === "bytes") {
        if (!(value instanceof Uint8Array)) throw new Error("bytes values must be Uint8Array");
        return value;
      }
      if (t.scalar === "str") {
        if (typeof value !== "string") throw new Error("str values must be string");
        return value;
      }
      if (t.scalar === "bool") {
        if (typeof value !== "boolean") throw new Error("bool values must be boolean");
        return value;
      }
      return value as CborValue;
    case "enum":
      return BigInt(schema.enumDef(t.name).members[value as string]);
    case "list":
      return (value as Native[]).map((v) => toWire(schema, t.elem, v));
    case "map": {
      const entries = mapEntries(value).sort((a, b) => compareNativeKey(a[0], b[0])); // ascending keys
      return entries.map(([k, v]) =>
        new Map<number, CborValue>([[1, toWire(schema, t.key, k)], [2, toWire(schema, t.value, v)]]));
    }
    case "msg": {
      const m = schema.message(t.name);
      const out = new Map<number, CborValue>();
      for (const f of schema.wireFields(m)) {
        const fv = value[f.name];
        out.set(f.tag, fv === null || fv === undefined ? null : toWire(schema, f.type, fv));
      }
      // forward-compat: re-emit unknown tags this schema doesn't name (cbor sorts keys)
      const residual = value.__unknown__ as Map<number, CborValue> | undefined;
      if (residual) for (const [tag, raw] of residual) out.set(tag, raw);
      return out;
    }
  }
}

function intFromWire(cv: CborValue): bigint {
  if (typeof cv === "bigint") return cv;
  wrong("int");
}

function fromWire(schema: SchemaIndex, t: TypeRef, cv: CborValue): Native {
  switch (t.k) {
    case "scalar":
      if (t.scalar === "int") return intFromWire(cv);
      if (t.scalar === "float") {
        if (!(cv instanceof CborFloat)) wrong("float");
        return cv.value;
      }
      if (t.scalar === "bytes") {
        if (!(cv instanceof Uint8Array)) wrong("bytes");
        return cv;
      }
      if (t.scalar === "str") {
        if (typeof cv !== "string") wrong("str");
        return cv;
      }
      if (t.scalar === "bool") {
        if (typeof cv !== "boolean") wrong("bool");
        return cv;
      }
      return cv;
    case "enum": {
      const wire = intFromWire(cv);
      const members = schema.enumDef(t.name).members;
      for (const [name, val] of Object.entries(members)) if (BigInt(val) === wire) return name;
      throw new DecodeError("UnknownEnum", { enum: t.name, value: wire.toString() });
    }
    case "list":
      if (!Array.isArray(cv)) wrong("list");
      return cv.map((v) => fromWire(schema, t.elem, v));
    case "map": {
      if (!Array.isArray(cv)) wrong("list");
      const out = new Map<Native, Native>();
      for (const e of cv) {
        if (!(e instanceof Map)) wrong("map");
        if (!e.has(1)) throw new DecodeError("MissingKey", { key: 1 });
        if (!e.has(2)) throw new DecodeError("MissingKey", { key: 2 });
        const key = fromWire(schema, t.key, e.get(1)!);
        if (out.has(key)) throw new DecodeError("DuplicateMapKey", { key });
        out.set(key, fromWire(schema, t.value, e.get(2)!));
      }
      return out;
    }
    case "msg": {
      const m = schema.message(t.name);
      if (!(cv instanceof Map)) wrong("map");
      const map = cv as Map<number, CborValue>;
      const out: Native = {};
      const known = new Set<number>();
      for (const f of schema.wireFields(m)) {
        known.add(f.tag);
        if (!map.has(f.tag)) {
          if (f.optional) {
            out[f.name] = null;
            continue;
          }
          throw new DecodeError("MissingKey", { key: f.tag });
        }
        const raw = map.get(f.tag)!;
        out[f.name] = raw === null && f.optional ? null : fromWire(schema, f.type, raw);
      }
      // forward-compat: capture tags this schema doesn't know (preserved raw)
      const residual = new Map<number, CborValue>();
      for (const [tag, raw] of map) if (!known.has(tag)) residual.set(tag, raw);
      if (residual.size) out.__unknown__ = residual;
      return out;
    }
  }
}

export function encode(schema: SchemaIndex, message: string, value: Native): Uint8Array {
  return cborEncode(toWire(schema, { k: "msg", name: message }, value));
}

export function decode(schema: SchemaIndex, message: string, data: Uint8Array): Native {
  return fromWire(schema, { k: "msg", name: message }, cborDecode(data));
}

// TypeRef-driven (for IR-declared method params / outputs / events).
export function encodeRef(schema: SchemaIndex, tref: TypeRef, value: Native): Uint8Array {
  return cborEncode(toWire(schema, tref, value));
}

export function decodeRef(schema: SchemaIndex, tref: TypeRef, data: Uint8Array): Native {
  return fromWire(schema, tref, cborDecode(data));
}
