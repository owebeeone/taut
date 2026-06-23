"use strict";

// Generic extension accessors over the frozen CBOR runtime. These know only the
// host wire bytes and the extension band tag; callers provide typed extension
// values as nested Cbor maps via the generated message's instance toCbor().

const { CMap, decode, encode } = require("./cbor.js");

const BAND_START = 2 ** 20;

function checkTag(tag) {
  if (!Number.isSafeInteger(tag) || tag < BAND_START) {
    throw new Error(`extension tag ${tag} is below the band (< ${BAND_START})`);
  }
}

function hostMap(hostBytes, tag) {
  checkTag(tag);
  const host = decode(hostBytes);
  if (!host || !Array.isArray(host.map)) {
    throw new Error("extension host must be a top-level CBOR map");
  }
  return host.map;
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
