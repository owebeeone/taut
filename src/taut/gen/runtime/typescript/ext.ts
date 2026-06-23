// Structural extension accessors for taut TypeScript runtimes.
//
// Extensions ride on a host message as a top-level CBOR map entry whose tag is
// in the extension band. The value is the nested extension message as CborValue,
// not pre-serialized bytes.

import { type CborValue, decode as cborDecode, encode as cborEncode } from "./cbor.ts";

export const BAND_START = 2 ** 20;

function checkTag(tag: number): void {
  if (!Number.isSafeInteger(tag) || tag < BAND_START) {
    throw new Error(`extension tag ${tag} is below the band (< ${BAND_START})`);
  }
}

function decodeHostMap(host: Uint8Array): Map<number, CborValue> {
  const top = cborDecode(host);
  if (!(top instanceof Map)) {
    throw new Error("extension host must decode to a top-level CBOR map");
  }
  return top;
}

export function extSet(host: Uint8Array, tag: number, value: CborValue): Uint8Array {
  checkTag(tag);
  const top = decodeHostMap(host);
  const out = new Map<number, CborValue>();
  for (const [k, v] of top) {
    if (k !== tag) out.set(k, v);
  }
  out.set(tag, value);
  return cborEncode(out);
}

export function extGet(host: Uint8Array, tag: number): CborValue | null {
  checkTag(tag);
  const top = decodeHostMap(host);
  return top.has(tag) ? top.get(tag)! : null;
}

export function extClear(host: Uint8Array, tag: number): Uint8Array {
  checkTag(tag);
  const top = decodeHostMap(host);
  const out = new Map<number, CborValue>();
  for (const [k, v] of top) {
    if (k !== tag) out.set(k, v);
  }
  return cborEncode(out);
}
