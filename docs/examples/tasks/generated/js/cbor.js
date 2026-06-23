"use strict";
// Minimal deterministic CBOR — the JavaScript binding of the frozen wire
// substrate. Same tiny subset (int, float, bytes, text, array, int-keyed map, bool,
// null), core-deterministic (definite length, shortest-form ints/floats, ascending map
// keys). Hand-rolled, no dependencies. Integers are JS numbers (safe to 2^53,
// like the TS codec); bytes are Uint8Array.

const INT = 0, BYTES = 1, TEXT = 2, ARR = 3, MAP = 4, BOOL = 5, NULL = 6, FLOAT = 7;

const CInt = (n) => ({ kind: INT, i: n });
const CFloat = (x) => ({ kind: FLOAT, f: x });
const CText = (s) => ({ kind: TEXT, s });
const CBytes = (b) => ({ kind: BYTES, b });
const CBool = (x) => ({ kind: BOOL, i: x ? 1 : 0 });
const CArr = (a) => ({ kind: ARR, arr: a });
const CMap = (m) => ({ kind: MAP, map: m }); // m: array of [key, Cbor]
const CNull = () => ({ kind: NULL });

function cget(c, key) {
  for (const [k, v] of c.map) if (k === key) return v;
  throw new Error("no map key " + key);
}
const cmapEntries = (c) => (c.kind === MAP ? c.map : []); // forward-compat residual
const isNull = (c) => c.kind === NULL;

function head(out, major, n) {
  const mt = major << 5;
  if (n < 24) out.push(mt | n);
  else if (n < 0x100) out.push(mt | 24, n & 0xff);
  else if (n < 0x10000) out.push(mt | 25, (n >> 8) & 0xff, n & 0xff);
  else if (n < 0x100000000) out.push(mt | 26, (n >>> 24) & 0xff, (n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff);
  else {
    const hi = Math.floor(n / 0x100000000), lo = n >>> 0;
    out.push(mt | 27, (hi >> 24) & 0xff, (hi >> 16) & 0xff, (hi >> 8) & 0xff, hi & 0xff,
      (lo >>> 24) & 0xff, (lo >> 16) & 0xff, (lo >> 8) & 0xff, lo & 0xff);
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
    case INT: if (c.i >= 0) head(out, 0, c.i); else head(out, 1, -1 - c.i); break;
    case FLOAT: encFloat(c.f, out); break;
    case BYTES: head(out, 2, c.b.length); for (const x of c.b) out.push(x); break;
    case TEXT: { const bb = new TextEncoder().encode(c.s); head(out, 3, bb.length); for (const x of bb) out.push(x); break; }
    case ARR: head(out, 4, c.arr.length); for (const x of c.arr) enc(x, out); break;
    case MAP: {
      const m = [...c.map].sort((a, b) => a[0] - b[0]); // ascending keys
      head(out, 5, m.length);
      for (const [k, v] of m) { head(out, 0, k); enc(v, out); }
      break;
    }
    case BOOL: out.push(c.i ? 0xf5 : 0xf4); break;
    case NULL: out.push(0xf6); break;
  }
}

function readArg(data, off, info) {
  if (info < 24) return [info, off];
  if (info === 24) return [data[off], off + 1];
  if (info === 25) return [(data[off] << 8) | data[off + 1], off + 2];
  if (info === 26) { let v = 0; for (let j = 0; j < 4; j++) v = v * 256 + data[off + j]; return [v, off + 4]; }
  let v = 0; for (let j = 0; j < 8; j++) v = v * 256 + data[off + j]; return [v, off + 8];
}

function readFloat32(data, off) {
  for (let i = 0; i < 4; i++) _view.setUint8(i, data[off + i]);
  return _view.getFloat32(0, false);
}

function readFloat64(data, off) {
  for (let i = 0; i < 8; i++) _view.setUint8(i, data[off + i]);
  return _view.getFloat64(0, false);
}

function decode(data) {
  const [v, off] = dec(data, 0);
  if (off !== data.length) throw new Error("trailing bytes after top-level CBOR item");
  return v;
}

function dec(data, off0) {
  const initial = data[off0], major = initial >> 5, info = initial & 0x1f;
  let off = off0 + 1;
  switch (major) {
    case 0: { const [n, o] = readArg(data, off, info); return [CInt(n), o]; }
    case 1: { const [n, o] = readArg(data, off, info); return [CInt(-1 - n), o]; }
    case 2: { const [n, o] = readArg(data, off, info); return [CBytes(data.slice(o, o + n)), o + n]; }
    case 3: { const [n, o] = readArg(data, off, info); return [CText(new TextDecoder().decode(data.slice(o, o + n))), o + n]; }
    case 4: { let [n, o] = readArg(data, off, info); const a = []; for (let i = 0; i < n; i++) { const [v, o2] = dec(data, o); a.push(v); o = o2; } return [CArr(a), o]; }
    case 5: { let [n, o] = readArg(data, off, info); const m = []; for (let i = 0; i < n; i++) { const [k, o2] = dec(data, o); const [v, o3] = dec(data, o2); m.push([k.i, v]); o = o3; } return [CMap(m), o]; }
    case 7:
      if (info === 20) return [CBool(false), off];
      if (info === 21) return [CBool(true), off];
      if (info === 22) return [CNull(), off];
      if (info === 25) return [CFloat(halfToNumber((data[off] << 8) | data[off + 1])), off + 2];
      if (info === 26) return [CFloat(readFloat32(data, off)), off + 4];
      if (info === 27) return [CFloat(readFloat64(data, off)), off + 8];
  }
  throw new Error("unsupported CBOR item");
}

module.exports = { CInt, CFloat, CText, CBytes, CBool, CArr, CMap, CNull, cget, cmapEntries, isNull, encode, decode };
