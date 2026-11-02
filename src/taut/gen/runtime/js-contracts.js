"use strict";
// Canonical CommonJS foundation. Build labels are informational, contracts are semantic.
class ConfigurationError extends Error {}
const OWNER = "taut.javascript.foundation";
const BUILD = "javascript-oneof-reference.1";
const CAPABILITIES = Object.freeze(["codec.v1", "descriptors.v1", "oneof.v1"]);
const ownerToken = Object.freeze({});
let engine = null;
function claimEngine(validate, isValid) {
  if (engine && (engine.validate !== validate || engine.isValid !== isValid)) throw new ConfigurationError("split JavaScript validation engine; re-export the actual shared engine");
  if (!engine) engine = Object.freeze({validate,isValid});
}
function requireContract(artifact, owner = OWNER, descriptor = 1, codec = 1, capabilities = CAPABILITIES) {
  if (owner !== OWNER || descriptor !== 1 || codec !== 1 || !Array.isArray(capabilities) ||
      capabilities.some(c => !CAPABILITIES.includes(c))) {
    throw new ConfigurationError(`${artifact}: incompatible foundation owner/descriptor/codec/capabilities; regenerate/rebind`);
  }
}
module.exports = Object.freeze({ConfigurationError, OWNER, BUILD, CAPABILITIES, ownerToken, requireContract, claimEngine});
