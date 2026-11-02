// Protected schema-fact snapshots; no descriptor or validation-engine dependency.
export function snapshot<T>(value: T): T {
  if(typeof value==="function" || typeof value==="symbol") throw new TypeError("unsupported portable metadata value");
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return Object.freeze(value.map(snapshot)) as T;
  if (value instanceof Uint8Array) return Object.freeze(Array.from(value)) as T;
  if(Object.getPrototypeOf(value)!==Object.prototype && Object.getPrototypeOf(value)!==null) throw new TypeError("portable metadata requires plain records");
  const out = Object.create(null) as Record<string, unknown>;
  for (const k of Object.keys(value)) out[k] = snapshot((value as Record<string,unknown>)[k]);
  return Object.freeze(out) as T;
}
