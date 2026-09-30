// The neutral IR, as consumed by TypeScript. Parsed from taut/corpus/
// griplab.ir.json — the same artifact Python authored. No schema is re-declared
// here; this is the cross-language contract.
//
// loadSchema reads IR versions 1 and 2 and refuses any other (TautOptions.md
// OPT-I1, OPT-F4). Version 2 adds options: every level's declared values, raw,
// and at the file and at each message `effective`, every option resolved by
// Python, defaults included (OPT-I2). This runtime reads only `effective`, and
// Python checks the raw values when it loads the IR. A version-1 IR declares
// nothing, so its effective values are the defaults.

import { DEFAULT_MAX_DEPTH, MAX_DEPTH_CEILING } from "./cbor.ts";

export type TypeRef =
  | { k: "scalar"; scalar: "int" | "str" | "bytes" | "bool" | "float" }
  | { k: "enum"; name: string }
  | { k: "msg"; name: string }
  | { k: "list"; elem: TypeRef }
  | { k: "map"; key: TypeRef; value: TypeRef };

// The IR's `optional`: false is required and true may be null; MISSING_OK may be
// null or absent, and reads an absent key as null (TautCheckedDecode.md CD-E5).
export const MISSING_OK = "missing_ok";

// The option values declared at one level, as written (version 2).
export type OptionMap = Record<string, unknown>;

// The wire options' values for a decode call's root (OPT-D4): its depth bound, and
// its length bound in bytes, or null for none. D1 enforces both.
export interface Effective {
  max_depth: number;
  max_encoded_len: number | null;
}

export interface FieldDef {
  name: string;
  tag: number;
  options?: OptionMap; // version 2
  type: TypeRef;
  optional: boolean | typeof MISSING_OK;
  transient: boolean;
}

export interface MessageDef {
  name: string;
  options?: OptionMap; // version 2
  effective?: Effective; // version 2; read it through SchemaIndex.effective
  fields: FieldDef[];
}

export interface EnumDef {
  name: string;
  options?: OptionMap; // version 2
  members: Record<string, number>;
  member_options?: Record<string, OptionMap>; // version 2: each member's, reserved
}

export interface ParamDef {
  name: string;
  type: TypeRef;
}

export interface OutSlot {
  slot: string;
  type: TypeRef;
}

// The minimal contract (D22): (name, in, out, shape). `shape` is the sole
// discriminator; `out` binds a type to each of the shape's delivery slots.
// `kind`/`output`/`events` are derived (see methodOutput / methodEvents).
export interface MethodDef {
  name: string;
  options?: OptionMap; // version 2: reserved
  role: string;
  shape: string;
  params: ParamDef[];
  out: OutSlot[];
}

// Derived view: the single return type of a once-delivered (unary) method.
export function methodOutput(m: MethodDef): TypeRef | null {
  return m.out.length ? m.out[0].type : null;
}

// Derived view: the slot->type bindings a streamed method delivers.
export function methodEvents(m: MethodDef): [string, TypeRef][] {
  return m.out.map((o) => [o.slot, o.type]);
}

export interface ServiceDef {
  name: string;
  options?: OptionMap; // version 2: reserved
  methods: MethodDef[];
}

export interface Schema {
  version: number; // 1 or 2
  options?: OptionMap; // version 2: the file's
  effective?: Effective; // version 2: the file's
  enums: EnumDef[];
  messages: MessageDef[];
  services: ServiceDef[];
}

// taut's numbers for the two wire options (OPT-D5, OPT-D6): the defaults, which a
// version-1 IR resolves to, and the ranges an effective value lies in. The depth
// numbers are the raw decoder's own, so the IR and the decoder cannot disagree.
const MAX_ENCODED_LEN_CEILING = 2 ** 31 - 1;
const DEFAULTS: Effective = Object.freeze({ max_depth: DEFAULT_MAX_DEPTH, max_encoded_len: null });

// The options this runtime knows. An `effective` naming any other is refused: a
// newer taut wrote it, and whether ignoring it is safe cannot be known (OPT-F1).
const KNOWN_OPTIONS: readonly string[] = ["max_depth", "max_encoded_len"];

function show(value: unknown): string {
  return JSON.stringify(value) ?? "none";
}

function irVersion(ir: Schema): 1 | 2 {
  const version: unknown = ir.version;
  if (version !== 1 && version !== 2) {
    throw new Error(
      `unsupported IR version ${show(version)}: this runtime reads versions 1 and 2; ` +
        "a newer taut wrote this IR, or it is not one",
    );
  }
  return version;
}

function isIntIn(value: unknown, low: number, high: number): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= low && value <= high;
}

function checkedDepth(value: unknown, where: string): number {
  if (!isIntIn(value, 1, MAX_DEPTH_CEILING)) {
    throw new Error(
      `${where}: effective max_depth must be an integer from 1 to ${MAX_DEPTH_CEILING}, not ${show(value)}`,
    );
  }
  return value;
}

function checkedLength(value: unknown, where: string): number | null {
  if (value === null) {
    return null;
  }
  if (!isIntIn(value, 1, MAX_ENCODED_LEN_CEILING)) {
    throw new Error(
      `${where}: effective max_encoded_len must be null or an integer from 1 to ` +
        `${MAX_ENCODED_LEN_CEILING}, not ${show(value)}`,
    );
  }
  return value;
}

// The effective values of the file or of a message: in version 1 the defaults, as it
// carries none; in version 2 the ones Python resolved, each known and in range.
function readEffective(level: { effective?: unknown }, where: string, version: 1 | 2): Effective {
  const values = level.effective;
  if (version === 1) {
    if (values !== undefined) {
      throw new Error(`${where}: a version 1 IR carries no effective values; re-export the schema`);
    }
    return DEFAULTS;
  }
  if (values === undefined) {
    throw new Error(
      `${where}: a version 2 IR carries effective values at the file and at each message; ` +
        "re-export the schema",
    );
  }
  if (typeof values !== "object" || values === null || Array.isArray(values)) {
    throw new Error(`${where}: effective must be an object, not ${show(values)}`);
  }
  for (const name of Object.keys(values)) {
    if (!KNOWN_OPTIONS.includes(name)) {
      throw new Error(
        `${where}: effective names ${name}, an option this runtime does not know ` +
          `(it knows ${KNOWN_OPTIONS.join(", ")}); a newer taut wrote this IR`,
      );
    }
  }
  for (const name of KNOWN_OPTIONS) {
    if (!Object.hasOwn(values, name)) {
      throw new Error(`${where}: effective lacks ${name}`);
    }
  }
  const raw = values as Record<string, unknown>;
  return Object.freeze({
    max_depth: checkedDepth(raw.max_depth, where),
    max_encoded_len: checkedLength(raw.max_encoded_len, where),
  });
}

export class SchemaIndex {
  private msgs = new Map<string, MessageDef>();
  private enms = new Map<string, EnumDef>();
  private mths = new Map<string, MethodDef>();
  private fileEffective: Effective;
  private msgEffective = new Map<string, Effective>();

  constructor(schema: Schema) {
    const version = irVersion(schema);
    this.fileEffective = readEffective(schema, "the file", version);
    for (const m of schema.messages) {
      this.msgs.set(m.name, m);
      this.msgEffective.set(m.name, readEffective(m, `message ${m.name}`, version));
    }
    for (const e of schema.enums) {
      this.enms.set(e.name, e);
    }
    for (const s of schema.services ?? []) {
      for (const m of s.methods) {
        this.mths.set(m.name, m);
      }
    }
  }

  // A message's effective values, or the file's when no message is named.
  effective(message?: string): Effective {
    if (message === undefined) {
      return this.fileEffective;
    }
    const e = this.msgEffective.get(message);
    if (!e) {
      throw new Error(`unknown message ${message}`);
    }
    return e;
  }

  // The effective values that bound a decode call rooted at `t` (OPT-D4, OPT-L6): a
  // message's own; for any other root, such as an RPC slot typed list<Tree>, the file's.
  rootEffective(t: TypeRef): Effective {
    if (t.k === "msg") {
      return this.effective(t.name);
    }
    return this.fileEffective;
  }

  method(name: string): MethodDef {
    const m = this.mths.get(name);
    if (!m) {
      throw new Error(`unknown method ${name}`);
    }
    return m;
  }

  message(name: string): MessageDef {
    const m = this.msgs.get(name);
    if (!m) {
      throw new Error(`unknown message ${name}`);
    }
    return m;
  }

  enumDef(name: string): EnumDef {
    const e = this.enms.get(name);
    if (!e) {
      throw new Error(`unknown enum ${name}`);
    }
    return e;
  }

  wireFields(m: MessageDef): FieldDef[] {
    return m.fields.filter((f) => !f.transient);
  }
}

export function loadSchema(json: unknown): SchemaIndex {
  if (typeof json !== "object" || json === null || Array.isArray(json)) {
    throw new Error(`a taut IR is a JSON object, not ${show(json)}`);
  }
  return new SchemaIndex(json as Schema);
}
