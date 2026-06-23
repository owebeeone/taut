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
  | number
  | CborFloat
  | string
  | boolean
  | null
  | Uint8Array
  | CborValue[]
  | Map<number, CborValue>;

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

function pushHead(out: number[], major: number, n: number): void {
  const mt = major << 5;
  if (n < 24) out.push(mt | n);
  else if (n < 0x100) out.push(mt | 24, n);
  else if (n < 0x10000) out.push(mt | 25, (n >> 8) & 0xff, n & 0xff);
  else if (n < 0x100000000)
    out.push(mt | 26, (n >>> 24) & 0xff, (n >>> 16) & 0xff, (n >>> 8) & 0xff, n & 0xff);
  else {
    out.push(mt | 27);
    const bn = BigInt(n);
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
  if (typeof value === "number") {
    if (!Number.isInteger(value)) throw new Error("frozen CBOR subset: no floats");
    if (value >= 0) pushHead(out, 0, value);
    else pushHead(out, 1, -1 - value);
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

function readArg(data: Uint8Array, off: number, info: number): [number, number] {
  if (info < 24) return [info, off];
  if (info === 24) return [data[off], off + 1];
  if (info === 25) return [(data[off] << 8) | data[off + 1], off + 2];
  if (info === 26)
    return [
      data[off] * 0x1000000 + data[off + 1] * 0x10000 + data[off + 2] * 0x100 + data[off + 3],
      off + 4,
    ];
  if (info === 27) {
    let bn = 0n;
    for (let i = 0; i < 8; i++) bn = (bn << 8n) | BigInt(data[off + i]);
    return [Number(bn), off + 8];
  }
  throw new Error(`unsupported additional-info ${info}`);
}

function dec(data: Uint8Array, off: number): [CborValue, number] {
  const initial = data[off];
  const major = initial >> 5;
  const info = initial & 0x1f;
  off++;
  if (major === 0) return readArg(data, off, info);
  if (major === 1) {
    const [n, o] = readArg(data, off, info);
    return [-1 - n, o];
  }
  if (major === 2) {
    const [n, o] = readArg(data, off, info);
    return [data.slice(o, o + n), o + n];
  }
  if (major === 3) {
    const [n, o] = readArg(data, off, info);
    return [new TextDecoder().decode(data.slice(o, o + n)), o + n];
  }
  if (major === 4) {
    let [n, o] = readArg(data, off, info);
    const arr: CborValue[] = [];
    for (let i = 0; i < n; i++) {
      const [v, o2] = dec(data, o);
      arr.push(v);
      o = o2;
    }
    return [arr, o];
  }
  if (major === 5) {
    let [n, o] = readArg(data, off, info);
    const m = new Map<number, CborValue>();
    for (let i = 0; i < n; i++) {
      const [k, o2] = dec(data, o);
      const [v, o3] = dec(data, o2);
      m.set(k as number, v);
      o = o3;
    }
    return [m, o];
  }
  if (major === 7) {
    if (info === 20) return [false, off];
    if (info === 21) return [true, off];
    if (info === 22) return [null, off];
    if (info === 25) {
      return [new CborFloat(halfToNumber((data[off] << 8) | data[off + 1])), off + 2];
    }
    if (info === 26) {
      const v = new DataView(data.buffer, data.byteOffset + off, 4).getFloat32(0, false);
      return [new CborFloat(v), off + 4];
    }
    if (info === 27) {
      const v = new DataView(data.buffer, data.byteOffset + off, 8).getFloat64(0, false);
      return [new CborFloat(v), off + 8];
    }
    throw new Error(`unsupported simple value ${info}`);
  }
  throw new Error(`unsupported major type ${major}`);
}

export function decode(data: Uint8Array): CborValue {
  const [value, off] = dec(data, 0);
  if (off !== data.length) throw new Error("trailing bytes after top-level CBOR item");
  return value;
}
