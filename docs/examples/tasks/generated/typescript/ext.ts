// Structural extension accessors for taut TypeScript runtimes.
//
// Extensions ride on a host message as a top-level CBOR map entry whose tag is
// in the extension band. The value is the nested extension message as CborValue,
// not pre-serialized bytes.
//
// They fail closed (TautCheckedDecode.md CD-E4): for any host bytes each returns or
// throws DecodeError, nothing else, and a host that is not a map is WrongType{map}.
// Not knowing the host's root, they read it at the depth ceiling with no length
// bound, the only bounds every valid host meets, and leave the host's own bounds to
// its reader (TautOptions.md G3). A tag below the band is the caller's error, a
// RangeError thrown before the host is read.

import {
  type CborValue,
  DecodeError,
  MAX_DEPTH_CEILING,
  type MapKey,
  decode as cborDecode,
  encode as cborEncode,
} from "./cbor.ts";

export const BAND_START = 2 ** 20;

function checkTag(tag: number): void {
  if (!Number.isSafeInteger(tag) || tag < BAND_START) {
    throw new RangeError(`extension tag ${tag} is below the band (< ${BAND_START})`);
  }
}

function decodeHostMap(host: Uint8Array): Map<MapKey, CborValue> {
  const top = cborDecode(host, { maxDepth: MAX_DEPTH_CEILING });
  if (!(top instanceof Map)) {
    throw new DecodeError("WrongType", { expected: "map" });
  }
  return top;
}

export function extSet(host: Uint8Array, tag: number, value: CborValue): Uint8Array {
  checkTag(tag);
  const top = decodeHostMap(host);
  const out = new Map<MapKey, CborValue>();
  for (const [k, v] of top) {
    if (k !== tag) {
      out.set(k, v);
    }
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
  const out = new Map<MapKey, CborValue>();
  for (const [k, v] of top) {
    if (k !== tag) {
      out.set(k, v);
    }
  }
  return cborEncode(out);
}
