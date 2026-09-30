"use strict";

// Generic extension accessors over the frozen CBOR runtime. These know only the
// host wire bytes and the extension band tag; callers provide typed extension
// values as nested Cbor maps via the generated message's instance toCbor().
//
// They fail closed (TautCheckedDecode.md CD-E4): for any host bytes each returns or
// throws DecodeError, nothing else, and a host that is not a map is WrongType{map}.
// Not knowing the host's root, they read it at the depth ceiling with no length
// bound, the only bounds every valid host meets, and leave the host's own bounds to
// its reader (TautOptions.md G3). A tag below the band is the caller's error, a
// RangeError thrown before the host is read.

const { CMap, MAX_DEPTH_CEILING, decode, encode, expectMap } = require("./cbor.js");

const BAND_START = 2 ** 20;

function checkTag(tag) {
  if (!Number.isSafeInteger(tag) || tag < BAND_START) {
    throw new RangeError(`extension tag ${tag} is below the band (< ${BAND_START})`);
  }
}

function hostMap(hostBytes, tag) {
  checkTag(tag);
  return expectMap(decode(hostBytes, { maxDepth: MAX_DEPTH_CEILING }));
}

function extSet(hostBytes, tag, value) {
  const map = hostMap(hostBytes, tag).filter(([k]) => k !== tag);
  map.push([tag, value]);
  return encode(CMap(map));
}

function extGet(hostBytes, tag) {
  for (const [k, v] of hostMap(hostBytes, tag)) {
    if (k === tag) return v;
  }
  return null;
}

function extClear(hostBytes, tag) {
  return encode(CMap(hostMap(hostBytes, tag).filter(([k]) => k !== tag)));
}

module.exports = { extSet, extGet, extClear };
