"use strict";
// Minimal deterministic CBOR — the JavaScript binding of the frozen wire
// substrate. Same tiny subset (i64 int, float, bytes, text, array, int-keyed map,
// bool, null), core-deterministic (definite length, shortest-form ints/floats,
// ascending map keys). Hand-rolled, no dependencies. Codec integer values are
// BigInt so every i64 value is exact; raw map keys remain structural field tags.

const INT = 0, BYTES = 1, TEXT = 2, ARR = 3, MAP = 4, BOOL = 5, NULL = 6, FLOAT = 7;

const INT_MIN = -(1n << 63n);
const INT_MAX = (1n << 63n) - 1n;
const UINT64_MAX = (1n << 64n) - 1n;
const MAX_SAFE_BIGINT = BigInt(Number.MAX_SAFE_INTEGER);

function stringValue(value) {
  return typeof value === "bigint" ? value.toString() : String(value);
}

class DecodeError extends Error {
  constructor(tag, payload = {}) {
    super(formatDecodeError(tag, payload));
    this.name = "DecodeError";
    this.tag = tag;
    Object.assign(this, payload);
  }
}

class EncodeError extends Error {
  constructor(tag, payload = {}) {
    super(formatEncodeError(tag, payload));
    this.name = "EncodeError";
    this.tag = tag;
    Object.assign(this, payload);
  }
}

function formatDecodeError(tag, payload) {
  switch (tag) {
    case "Truncated": return "truncated CBOR item";
    case "TrailingBytes": return "trailing bytes after top-level CBOR item";
    case "InvalidUtf8": return "invalid UTF-8 text string";
    case "UnsupportedInfo": return `unsupported additional-info ${payload.info}`;
    case "UnsupportedMajor": return `unsupported major type ${payload.major}`;
    case "NonIntegerMapKey": return "CBOR map key is not an integer";
    case "DuplicateMapKey": return `duplicate CBOR map key ${payload.key}`;
    case "IntOverflow": return `integer outside i64 subset: ${payload.value}`;
    case "MissingKey": return `missing map key ${payload.key}`;
    case "WrongType": return `wrong CBOR type, expected ${payload.expected}`;
    case "UnknownEnum": return `unknown ${payload.enum} enum value ${payload.value}`;
    case "NonCanonicalInt": return "non-canonical integer encoding";
    case "NegativeMapKey": return `negative CBOR map key ${payload.key}`;
    default: return tag;
  }
}

function formatEncodeError(tag, payload) {
  if (tag === "IntOutOfSubset") return `integer outside i64 subset: ${payload.value}`;
  return tag;
}

function encodeIntError(value) {
  return new EncodeError("IntOutOfSubset", { value: stringValue(value) });
}

function decodeIntOverflow(value) {
  return new DecodeError("IntOverflow", { value: stringValue(value) });
}

function toExactBigInt(value) {
  if (typeof value === "bigint") return value;
  if (typeof value === "number" && Number.isSafeInteger(value)) return BigInt(value);
  throw encodeIntError(value);
}

function checkI64ForEncode(value) {
  const n = toExactBigInt(value);
  if (n < INT_MIN || n > INT_MAX) throw encodeIntError(n);
  return n;
}

function checkI64ForDecode(value) {
  if (value < INT_MIN || value > INT_MAX) throw decodeIntOverflow(value);
  return value;
}

function rawCInt(n) {
  return { kind: INT, i: n };
}

function rawCMap(m) {
  return { kind: MAP, map: m };
}

const CInt = (n) => rawCInt(checkI64ForEncode(n));
const CFloat = (x) => ({ kind: FLOAT, f: x });
const CText = (s) => ({ kind: TEXT, s });
const CBytes = (b) => ({ kind: BYTES, b });
const CBool = (x) => ({ kind: BOOL, i: x ? 1 : 0 });
const CArr = (a) => ({ kind: ARR, arr: a });
const CMap = (m) => ({ kind: MAP, map: m.map(([k, v]) => [normalizeMapKeyForEncode(k), v]) });
const CNull = () => ({ kind: NULL });

function wrongType(expected) {
  throw new DecodeError("WrongType", { expected });
}

function expectKind(c, kind, expected) {
  if (!c || c.kind !== kind) wrongType(expected);
  return c;
}

function expectInt(c) {
  return expectKind(c, INT, "int").i;
}

function expectFloat(c) {
  return expectKind(c, FLOAT, "float").f;
}

function expectText(c) {
  return expectKind(c, TEXT, "str").s;
}

function expectBytes(c) {
  return expectKind(c, BYTES, "bytes").b;
}

function expectBool(c) {
  return expectKind(c, BOOL, "bool").i !== 0;
}

function expectArray(c) {
  return expectKind(c, ARR, "array").arr;
}

function expectMap(c) {
  return expectKind(c, MAP, "map").map;
}

function enumFromWire(value, enumName, allowed) {
  let wire;
  if (typeof value === "bigint") {
    wire = value;
  } else if (typeof value === "number" && Number.isInteger(value)) {
    wire = BigInt(value);
  } else {
    throw new DecodeError("UnknownEnum", { enum: enumName, value: stringValue(value) });
  }
  if (wire >= -MAX_SAFE_BIGINT && wire <= MAX_SAFE_BIGINT) {
    const n = Number(wire);
    if (allowed.has(n)) return n;
  }
  throw new DecodeError("UnknownEnum", { enum: enumName, value: wire.toString() });
}

function enumFromCbor(c, enumName, allowed) {
  return enumFromWire(expectInt(c), enumName, allowed);
}

function mapKeyBigInt(key) {
  if (typeof key === "bigint") return key;
  if (typeof key === "number" && Number.isSafeInteger(key)) return BigInt(key);
  throw encodeIntError(key);
}

function normalizeMapKeyForEncode(key) {
  const n = mapKeyBigInt(key);
  if (n < 0n || n > UINT64_MAX) throw encodeIntError(key);
  return n <= MAX_SAFE_BIGINT ? Number(n) : n;
}

function normalizeMapKeyForDecode(key) {
  if (key < 0n) return key;
  return key <= MAX_SAFE_BIGINT ? Number(key) : key;
}

function mapKeyId(key) {
  return mapKeyBigInt(key).toString();
}

function mapKeyEquals(a, b) {
  return mapKeyBigInt(a) === mapKeyBigInt(b);
}

function compareMapKeys(a, b) {
  const aa = mapKeyBigInt(a);
  const bb = mapKeyBigInt(b);
  return aa < bb ? -1 : aa > bb ? 1 : 0;
}

function cget(c, key) {
  for (const [k, v] of expectMap(c)) if (mapKeyEquals(k, key)) return v;
  throw new DecodeError("MissingKey", { key });
}

const cmapEntries = (c) => expectMap(c); // forward-compat residual
const isNull = (c) => c && c.kind === NULL;

function head(out, major, value) {
  const n = typeof value === "bigint" ? value : BigInt(value);
  if (n < 0n || n > UINT64_MAX) throw encodeIntError(value);
  const mt = major << 5;
  if (n < 24n) {
    out.push(mt | Number(n));
  } else if (n < 0x100n) {
    out.push(mt | 24, Number(n & 0xffn));
  } else if (n < 0x10000n) {
    out.push(mt | 25, Number((n >> 8n) & 0xffn), Number(n & 0xffn));
  } else if (n < 0x100000000n) {
    out.push(
      mt | 26,
      Number((n >> 24n) & 0xffn),
      Number((n >> 16n) & 0xffn),
      Number((n >> 8n) & 0xffn),
      Number(n & 0xffn),
    );
  } else {
    out.push(mt | 27);
    for (let shift = 56n; shift >= 0n; shift -= 8n) out.push(Number((n >> shift) & 0xffn));
  }
}

const _buf = new ArrayBuffer(8);
const _view = new DataView(_buf);
const HALF_MIN_NORMAL = 6.103515625e-5; // 2^-14

function roundShiftRight(m, shift) {
  if (shift <= 0) return m;
  const s = BigInt(shift);
  const q = m >> s;
  const r = m - (q << s);
  const half = 1n << (s - 1n);
  return (r > half || (r === half && (q & 1n) === 1n)) ? q + 1n : q;
}

function roundScaled(m, scale) {
  return scale >= 0 ? m << BigInt(scale) : roundShiftRight(m, -scale);
}

function f64Parts(v) {
  _view.setFloat64(0, v, false);
  const hi = _view.getUint32(0, false), lo = _view.getUint32(4, false);
  return {
    sign: hi >>> 31,
    exp: (hi >>> 20) & 0x7ff,
    frac: (BigInt(hi & 0xfffff) << 32n) | BigInt(lo),
  };
}

function doubleToHalfBits(v) {
  const p = f64Parts(v);
  const sign = p.sign << 15;
  if (p.exp === 0x7ff) return sign | (p.frac === 0n ? 0x7c00 : 0x7e00);
  if (p.exp === 0 && p.frac === 0n) return sign;

  const m = p.exp === 0 ? p.frac : (1n << 52n) | p.frac;
  const e = p.exp === 0 ? -1074 : p.exp - 1023 - 52;

  if (Math.abs(v) < HALF_MIN_NORMAL) {
    const sub = Number(roundScaled(m, e + 24));
    if (sub === 0) return sign;
    return sign | (sub >= 1024 ? 0x0400 : sub);
  }

  let exp = p.exp - 1023;
  let sig = roundScaled(m, e - exp + 10);
  if (sig === 2048n) {
    sig = 1024n;
    exp += 1;
  }
  if (exp > 15) return sign | 0x7c00;
  return sign | ((exp + 15) << 10) | (Number(sig) - 1024);
}

function halfToNumber(bits) {
  const sign = (bits & 0x8000) ? -1 : 1;
  const exp = (bits >>> 10) & 0x1f;
  const frac = bits & 0x03ff;
  if (exp === 0) {
    if (frac === 0) return sign < 0 ? -0 : 0;
    return sign * frac * Math.pow(2, -24);
  }
  if (exp === 0x1f) return frac === 0 ? sign * Infinity : NaN;
  return sign * (1 + frac / 1024) * Math.pow(2, exp - 15);
}

function pushFloat16(out, bits) {
  out.push(0xf9, (bits >>> 8) & 0xff, bits & 0xff);
}

function pushFloat32(out, v) {
  _view.setFloat32(0, v, false);
  out.push(0xfa, _view.getUint8(0), _view.getUint8(1), _view.getUint8(2), _view.getUint8(3));
}

function pushFloat64(out, v) {
  _view.setFloat64(0, v, false);
  out.push(0xfb);
  for (let i = 0; i < 8; i++) out.push(_view.getUint8(i));
}

function encFloat(value, out) {
  const v = Number(value);
  if (Number.isNaN(v)) {
    out.push(0xf9, 0x7e, 0x00);
    return;
  }
  const h = doubleToHalfBits(v);
  if (Object.is(halfToNumber(h), v)) {
    pushFloat16(out, h);
  } else if (Object.is(Math.fround(v), v)) {
    pushFloat32(out, v);
  } else {
    pushFloat64(out, v);
  }
}

function encode(c) {
  const out = [];
  enc(c, out);
  return Uint8Array.from(out);
}

function enc(c, out) {
  switch (c.kind) {
    case INT: {
      const n = checkI64ForEncode(c.i);
      if (n >= 0n) head(out, 0, n);
      else head(out, 1, -1n - n);
      break;
    }
    case FLOAT: encFloat(c.f, out); break;
    case BYTES: head(out, 2, c.b.length); for (const x of c.b) out.push(x); break;
    case TEXT: { const bb = new TextEncoder().encode(c.s); head(out, 3, bb.length); for (const x of bb) out.push(x); break; }
    case ARR: head(out, 4, c.arr.length); for (const x of c.arr) enc(x, out); break;
    case MAP: {
      const m = [...c.map].map(([k, v]) => [normalizeMapKeyForEncode(k), v]).sort((a, b) => compareMapKeys(a[0], b[0]));
      head(out, 5, m.length);
      for (const [k, v] of m) { head(out, 0, mapKeyBigInt(k)); enc(v, out); }
      break;
    }
    case BOOL: out.push(c.i ? 0xf5 : 0xf4); break;
    case NULL: out.push(0xf6); break;
    default: throw new EncodeError("UnsupportedType", { value: c && c.kind });
  }
}

function requireBytes(data, off, length) {
  if (off + length > data.length) throw new DecodeError("Truncated");
}

function readArg(data, off, info) {
  if (info < 24) return [BigInt(info), off];
  let value;
  let next;
  let fitsShorter;
  if (info === 24) {
    requireBytes(data, off, 1);
    value = BigInt(data[off]);
    next = off + 1;
    fitsShorter = value < 24n;
  } else if (info === 25) {
    requireBytes(data, off, 2);
    value = (BigInt(data[off]) << 8n) | BigInt(data[off + 1]);
    next = off + 2;
    fitsShorter = value <= 0xffn;
  } else if (info === 26) {
    requireBytes(data, off, 4);
    value = 0n;
    for (let j = 0; j < 4; j++) value = (value << 8n) | BigInt(data[off + j]);
    next = off + 4;
    fitsShorter = value <= 0xffffn;
  } else if (info === 27) {
    requireBytes(data, off, 8);
    value = 0n;
    for (let j = 0; j < 8; j++) value = (value << 8n) | BigInt(data[off + j]);
    next = off + 8;
    fitsShorter = value <= 0xffffffffn;
  } else {
    throw new DecodeError("UnsupportedInfo", { info });
  }
  // Strict-canonical (D2): a multi-byte argument that fits a shorter width is
  // non-minimal — the canonical encoder never emits it, so reject it.
  if (fitsShorter) throw new DecodeError("NonCanonicalInt", { value: stringValue(value) });
  return [value, next];
}

function readLength(data, off, info) {
  const [n, next] = readArg(data, off, info);
  if (n > MAX_SAFE_BIGINT) throw decodeIntOverflow(n);
  return [Number(n), next];
}

function readFloat32(data, off) {
  requireBytes(data, off, 4);
  for (let i = 0; i < 4; i++) _view.setUint8(i, data[off + i]);
  return _view.getFloat32(0, false);
}

function readFloat64(data, off) {
  requireBytes(data, off, 8);
  for (let i = 0; i < 8; i++) _view.setUint8(i, data[off + i]);
  return _view.getFloat64(0, false);
}

function decode(data) {
  const [v, off] = dec(data, 0);
  if (off !== data.length) throw new DecodeError("TrailingBytes");
  return v;
}

function dec(data, off0) {
  if (off0 >= data.length) throw new DecodeError("Truncated");
  const initial = data[off0], major = initial >> 5, info = initial & 0x1f;
  if (info >= 28) throw new DecodeError("UnsupportedInfo", { info });
  let off = off0 + 1;
  switch (major) {
    case 0: {
      const [n, o] = readArg(data, off, info);
      return [rawCInt(checkI64ForDecode(n)), o];
    }
    case 1: {
      const [n, o] = readArg(data, off, info);
      return [rawCInt(checkI64ForDecode(-1n - n)), o];
    }
    case 2: {
      const [n, o] = readLength(data, off, info);
      requireBytes(data, o, n);
      return [CBytes(data.slice(o, o + n)), o + n];
    }
    case 3: {
      const [n, o] = readLength(data, off, info);
      requireBytes(data, o, n);
      try {
        return [CText(new TextDecoder("utf-8", { fatal: true }).decode(data.slice(o, o + n))), o + n];
      } catch (_) {
        throw new DecodeError("InvalidUtf8");
      }
    }
    case 4: {
      let [n, o] = readLength(data, off, info);
      const a = [];
      for (let i = 0; i < n; i++) {
        const [v, o2] = dec(data, o);
        a.push(v);
        o = o2;
      }
      return [CArr(a), o];
    }
    case 5: {
      let [n, o] = readLength(data, off, info);
      const m = [];
      const seen = new Set();
      for (let i = 0; i < n; i++) {
        const [k, o2] = dec(data, o);
        if (!k || k.kind !== INT) throw new DecodeError("NonIntegerMapKey");
        if (k.i < 0n) throw new DecodeError("NegativeMapKey", { key: k.i });
        const rawKey = normalizeMapKeyForDecode(k.i);
        const id = mapKeyId(rawKey);
        if (seen.has(id)) throw new DecodeError("DuplicateMapKey", { key: rawKey });
        seen.add(id);
        const [v, o3] = dec(data, o2);
        m.push([rawKey, v]);
        o = o3;
      }
      return [rawCMap(m), o];
    }
    case 7:
      if (info === 20) return [CBool(false), off];
      if (info === 21) return [CBool(true), off];
      if (info === 22) return [CNull(), off];
      if (info === 25) {
        requireBytes(data, off, 2);
        return [CFloat(halfToNumber((data[off] << 8) | data[off + 1])), off + 2];
      }
      if (info === 26) return [CFloat(readFloat32(data, off)), off + 4];
      if (info === 27) return [CFloat(readFloat64(data, off)), off + 8];
      throw new DecodeError("UnsupportedInfo", { info });
    default:
      throw new DecodeError("UnsupportedMajor", { major });
  }
}

module.exports = {
  CInt,
  CFloat,
  CText,
  CBytes,
  CBool,
  CArr,
  CMap,
  CNull,
  DecodeError,
  EncodeError,
  cget,
  cmapEntries,
  isNull,
  expectInt,
  expectFloat,
  expectText,
  expectBytes,
  expectBool,
  expectArray,
  expectMap,
  enumFromWire,
  enumFromCbor,
  encode,
  decode,
};
