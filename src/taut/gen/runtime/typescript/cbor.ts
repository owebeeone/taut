// Minimal deterministic CBOR — the TypeScript binding of the frozen wire
// substrate. Byte-for-byte identical to taut/src/taut/wire/cbor.py: same tiny
// subset (int, float, bytes, text, array, int-keyed map, bool, null), same core
// deterministic encoding (definite length, shortest-form ints, ascending map
// keys). Maps use integer keys only — they carry field tags.

export class CborFloat {
  readonly value: number;

  constructor(value: number) {
    this.value = value;
  }
}

export type CborValue =
  | bigint
  | number
  | CborFloat
  | string
  | boolean
  | null
  | Uint8Array
  | CborValue[]
  | Map<number, CborValue>;

export type DecodeErrorTag =
  | "Truncated"
  | "TrailingBytes"
  | "InvalidUtf8"
  | "UnsupportedInfo"
  | "UnsupportedMajor"
  | "NonIntegerMapKey"
  | "IntOverflow"
  | "DuplicateMapKey"
  | "MissingKey"
  | "WrongType"
  | "UnknownEnum"
  | "NonCanonicalInt"
  | "NegativeMapKey";

export interface DecodeErrorFields {
  info?: number;
  major?: number;
  key?: number | bigint;
  value?: string;
  expected?: string;
  enum?: string;
}

export class DecodeError extends Error {
  readonly tag: DecodeErrorTag;
  readonly info?: number;
  readonly major?: number;
  readonly key?: number | bigint;
  readonly value?: string;
  readonly expected?: string;
  readonly enum?: string;

  constructor(tag: DecodeErrorTag, fields: DecodeErrorFields = {}) {
    const detail = Object.entries(fields).map(([k, v]) => `${k}=${String(v)}`).join(" ");
    super(detail ? `${tag} ${detail}` : tag);
    this.name = "DecodeError";
    this.tag = tag;
    Object.assign(this, fields);
  }
}

export class EncodeError extends Error {
  readonly tag = "IntOutOfSubset";
  readonly value?: string;

  constructor(value?: bigint | number | string) {
    super(value === undefined ? "IntOutOfSubset" : `IntOutOfSubset value=${String(value)}`);
    this.name = "EncodeError";
    this.value = value === undefined ? undefined : String(value);
  }
}

export const I64_MIN = -(1n << 63n);
export const I64_MAX = (1n << 63n) - 1n;

const U32_LIMIT = 0x100000000n;
const textDecoder = new TextDecoder("utf-8", { fatal: true });
const floatScratch = new DataView(new ArrayBuffer(8));
const F64_FRAC_MASK = (1n << 52n) - 1n;
const F64_HIDDEN_BIT = 1n << 52n;

function f64Bits(value: number): bigint {
  floatScratch.setFloat64(0, value, false);
  return floatScratch.getBigUint64(0, false);
}

function f64BitsEqual(a: number, b: number): boolean {
  return f64Bits(a) === f64Bits(b);
}

function roundToEvenInt(mantissa: bigint, valuePow2: number, unitPow2: number): bigint {
  const shift = valuePow2 - unitPow2;
  if (shift >= 0) return mantissa << BigInt(shift);

  const r = -shift;
  const quotient = mantissa >> BigInt(r);
  const divisor = 1n << BigInt(r);
  const remainder = mantissa & (divisor - 1n);
  const half = 1n << BigInt(r - 1);
  if (remainder > half || (remainder === half && (quotient & 1n) === 1n)) {
    return quotient + 1n;
  }
  return quotient;
}

function doubleToHalfBits(value: number): number {
  const bits = f64Bits(value);
  const signBits = Number((bits >> 48n) & 0x8000n);
  const exp = Number((bits >> 52n) & 0x7ffn);
  const frac = bits & F64_FRAC_MASK;

  if (exp === 0x7ff) return signBits | (frac === 0n ? 0x7c00 : 0x7e00);
  if (exp === 0 && frac === 0n) return signBits;

  let mantissa: bigint;
  let valuePow2: number;
  let actualExp = -1022;
  if (exp === 0) {
    mantissa = frac;
    valuePow2 = -1074;
  } else {
    actualExp = exp - 1023;
    mantissa = F64_HIDDEN_BIT | frac;
    valuePow2 = actualExp - 52;
  }

  if (exp === 0 || actualExp < -14) {
    const subnormal = roundToEvenInt(mantissa, valuePow2, -24);
    if (subnormal === 0n) return signBits;
    if (subnormal >= 1024n) return signBits | 0x0400 | Number(subnormal - 1024n);
    return signBits | Number(subnormal);
  }

  if (actualExp > 15) return signBits | 0x7c00;

  let halfMantissa = roundToEvenInt(mantissa, valuePow2, actualExp - 10);
  if (halfMantissa === 2048n) {
    actualExp += 1;
    halfMantissa = 1024n;
  }
  if (actualExp > 15) return signBits | 0x7c00;

  return signBits | ((actualExp + 15) << 10) | (Number(halfMantissa) - 1024);
}

function halfToNumber(bits: number): number {
  const sign = (bits & 0x8000) !== 0;
  const exp = (bits >> 10) & 0x1f;
  const frac = bits & 0x03ff;

  if (exp === 0) {
    if (frac === 0) return sign ? -0 : 0;
    const value = frac * 2 ** -24;
    return sign ? -value : value;
  }
  if (exp === 0x1f) {
    if (frac === 0) return sign ? -Infinity : Infinity;
    return NaN;
  }

  const value = (1 + frac / 1024) * 2 ** (exp - 15);
  return sign ? -value : value;
}

function pushFloat16(out: number[], bits: number): void {
  out.push(0xf9, (bits >> 8) & 0xff, bits & 0xff);
}

function pushFloat32(out: number[], value: number): void {
  floatScratch.setFloat32(0, value, false);
  out.push(0xfa);
  for (let i = 0; i < 4; i++) out.push(floatScratch.getUint8(i));
}

function pushFloat64(out: number[], value: number): void {
  floatScratch.setFloat64(0, value, false);
  out.push(0xfb);
  for (let i = 0; i < 8; i++) out.push(floatScratch.getUint8(i));
}

function pushShortestFloat(out: number[], value: number): void {
  if (Number.isNaN(value)) {
    pushFloat16(out, 0x7e00);
    return;
  }

  const halfBits = doubleToHalfBits(value);
  if (f64BitsEqual(halfToNumber(halfBits), value)) {
    pushFloat16(out, halfBits);
    return;
  }

  const single = Math.fround(value);
  if (f64BitsEqual(single, value)) {
    pushFloat32(out, single);
    return;
  }

  pushFloat64(out, value);
}

function checkedInt(value: bigint | number): bigint {
  let n: bigint;
  if (typeof value === "bigint") {
    n = value;
  } else {
    if (!Number.isInteger(value)) throw new Error("frozen CBOR subset: no floats");
    if (!Number.isSafeInteger(value)) throw new EncodeError(value);
    n = BigInt(value);
  }
  if (n < I64_MIN || n > I64_MAX) throw new EncodeError(n);
  return n;
}

function pushHead(out: number[], major: number, n: bigint | number): void {
  const bn = typeof n === "bigint" ? n : BigInt(n);
  const mt = major << 5;
  if (bn < 0n) throw new EncodeError(bn);
  if (bn < 24n) out.push(mt | Number(bn));
  else if (bn < 0x100n) out.push(mt | 24, Number(bn));
  else if (bn < 0x10000n) out.push(mt | 25, Number((bn >> 8n) & 0xffn), Number(bn & 0xffn));
  else if (bn < U32_LIMIT) {
    out.push(
      mt | 26,
      Number((bn >> 24n) & 0xffn),
      Number((bn >> 16n) & 0xffn),
      Number((bn >> 8n) & 0xffn),
      Number(bn & 0xffn),
    );
  } else {
    out.push(mt | 27);
    for (let i = 7; i >= 0; i--) out.push(Number((bn >> BigInt(i * 8)) & 0xffn));
  }
}

function enc(value: CborValue, out: number[]): void {
  if (value === null) { out.push(0xf6); return; }
  if (value === true) { out.push(0xf5); return; }
  if (value === false) { out.push(0xf4); return; }
  if (value instanceof CborFloat) {
    pushShortestFloat(out, value.value);
    return;
  }
  if (typeof value === "bigint" || typeof value === "number") {
    const n = checkedInt(value);
    if (n >= 0n) pushHead(out, 0, n);
    else pushHead(out, 1, -1n - n);
    return;
  }
  if (value instanceof Uint8Array) {
    pushHead(out, 2, value.length);
    for (const b of value) out.push(b);
    return;
  }
  if (typeof value === "string") {
    const e = new TextEncoder().encode(value);
    pushHead(out, 3, e.length);
    for (const b of e) out.push(b);
    return;
  }
  if (Array.isArray(value)) {
    pushHead(out, 4, value.length);
    for (const v of value) enc(v, out);
    return;
  }
  if (value instanceof Map) {
    const keys = [...value.keys()].sort((a, b) => a - b); // deterministic
    pushHead(out, 5, keys.length);
    for (const k of keys) {
      if (!Number.isSafeInteger(k) || k < 0) throw new Error(`invalid CBOR map key ${k}`);
      pushHead(out, 0, k);
      enc(value.get(k) as CborValue, out);
    }
    return;
  }
  throw new Error("type not in the frozen CBOR subset");
}

export function encode(value: CborValue): Uint8Array {
  const out: number[] = [];
  enc(value, out);
  return Uint8Array.from(out);
}

function requireBytes(data: Uint8Array, off: number, count: number): void {
  if (off + count > data.length) throw new DecodeError("Truncated");
}

function readArg(data: Uint8Array, off: number, info: number): [bigint, number] {
  if (info < 24) return [BigInt(info), off];
  let value: bigint;
  let next: number;
  let fitsShorter: boolean;
  if (info === 24) {
    requireBytes(data, off, 1);
    value = BigInt(data[off]);
    next = off + 1;
    fitsShorter = value < 24n;
  } else if (info === 25) {
    requireBytes(data, off, 2);
    value = BigInt((data[off] << 8) | data[off + 1]);
    next = off + 2;
    fitsShorter = value <= 0xffn;
  } else if (info === 26) {
    requireBytes(data, off, 4);
    value = BigInt(data[off]) << 24n |
      BigInt(data[off + 1]) << 16n |
      BigInt(data[off + 2]) << 8n |
      BigInt(data[off + 3]);
    next = off + 4;
    fitsShorter = value <= 0xffffn;
  } else if (info === 27) {
    requireBytes(data, off, 8);
    value = 0n;
    for (let i = 0; i < 8; i++) value = (value << 8n) | BigInt(data[off + i]);
    next = off + 8;
    fitsShorter = value <= 0xffffffffn;
  } else {
    throw new DecodeError("UnsupportedInfo", { info });
  }
  // Strict-canonical (D2): a multi-byte argument that fits a shorter width is
  // non-minimal — the canonical encoder never emits it, so reject it.
  if (fitsShorter) throw new DecodeError("NonCanonicalInt", { value: value.toString() });
  return [value, next];
}

function readLength(data: Uint8Array, off: number, info: number): [number, number] {
  const [n, o] = readArg(data, off, info);
  if (n > BigInt(Number.MAX_SAFE_INTEGER)) throw new DecodeError("IntOverflow", { value: n.toString() });
  return [Number(n), o];
}

function dec(data: Uint8Array, off: number): [CborValue, number] {
  requireBytes(data, off, 1);
  const initial = data[off];
  const major = initial >> 5;
  const info = initial & 0x1f;
  off++;
  if (major === 0) {
    const [n, o] = readArg(data, off, info);
    if (n > I64_MAX) throw new DecodeError("IntOverflow", { value: n.toString() });
    return [n, o];
  }
  if (major === 1) {
    const [n, o] = readArg(data, off, info);
    if (n > I64_MAX) throw new DecodeError("IntOverflow", { value: (-1n - n).toString() });
    return [-1n - n, o];
  }
  if (major === 2) {
    const [n, o] = readLength(data, off, info);
    requireBytes(data, o, n);
    return [data.slice(o, o + n), o + n];
  }
  if (major === 3) {
    const [n, o] = readLength(data, off, info);
    requireBytes(data, o, n);
    try {
      return [textDecoder.decode(data.slice(o, o + n)), o + n];
    } catch {
      throw new DecodeError("InvalidUtf8");
    }
  }
  if (major === 4) {
    let [n, o] = readLength(data, off, info);
    const arr: CborValue[] = [];
    for (let i = 0; i < n; i++) {
      const [v, o2] = dec(data, o);
      arr.push(v);
      o = o2;
    }
    return [arr, o];
  }
  if (major === 5) {
    let [n, o] = readLength(data, off, info);
    const m = new Map<number, CborValue>();
    const seen = new Set<string>();
    for (let i = 0; i < n; i++) {
      const [k, o2] = dec(data, o);
      if (typeof k !== "bigint") throw new DecodeError("NonIntegerMapKey");
      if (k < 0n) throw new DecodeError("NegativeMapKey", { key: k });
      if (k > BigInt(Number.MAX_SAFE_INTEGER)) throw new DecodeError("NonIntegerMapKey");
      const key = Number(k);
      const token = k.toString();
      if (seen.has(token)) throw new DecodeError("DuplicateMapKey", { key });
      seen.add(token);
      const [v, o3] = dec(data, o2);
      m.set(key, v);
      o = o3;
    }
    return [m, o];
  }
  if (major === 6) throw new DecodeError("UnsupportedMajor", { major });
  if (major === 7) {
    if (info === 20) return [false, off];
    if (info === 21) return [true, off];
    if (info === 22) return [null, off];
    if (info === 25) {
      requireBytes(data, off, 2);
      return [new CborFloat(halfToNumber((data[off] << 8) | data[off + 1])), off + 2];
    }
    if (info === 26) {
      requireBytes(data, off, 4);
      const v = new DataView(data.buffer, data.byteOffset + off, 4).getFloat32(0, false);
      return [new CborFloat(v), off + 4];
    }
    if (info === 27) {
      requireBytes(data, off, 8);
      const v = new DataView(data.buffer, data.byteOffset + off, 8).getFloat64(0, false);
      return [new CborFloat(v), off + 8];
    }
    throw new DecodeError("UnsupportedInfo", { info });
  }
  throw new DecodeError("UnsupportedMajor", { major });
}

export function decode(data: Uint8Array): CborValue {
  const [value, off] = dec(data, 0);
  if (off !== data.length) throw new DecodeError("TrailingBytes");
  return value;
}
