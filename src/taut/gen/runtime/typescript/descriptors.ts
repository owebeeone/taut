// Canonical TypeScript foundation. No compiler, authoring loader or validation engine.
import { snapshot } from "./snapshots.ts";
import { CborContract, CborFloat, DecodeError, EncodeError } from "./cbor.ts";
import { CodecContract } from "./codec.ts";
import { SchemaContract } from "./schema.ts";
import { JsonCodecContract } from "./jsoncodec.ts";
export { snapshot } from "./snapshots.ts";
export const ONEOF_RULE = "taut.oneof.v1";
export class ConfigurationError extends Error {}
export const Foundation = Object.freeze({
  owner: "taut.typescript.foundation", descriptorContract: 1, codecContract: 1,
  build: "typescript-oneof-reference.1",
  capabilities: Object.freeze(["codec.v1", "descriptors.v1", "oneof.v1"]),
  codecTypes: Object.freeze({CborFloat, DecodeError, EncodeError}),
});
export function requireFoundation(actual: unknown = Foundation): void {
  const a = actual as typeof Foundation;
  if (!a || a.owner !== Foundation.owner || a.descriptorContract !== 1 || a.codecContract !== 1 ||
      !Array.isArray(a.capabilities) || Foundation.capabilities.some(c => !a.capabilities.includes(c)))
    throw new ConfigurationError("compatible TypeScript foundation required: descriptor=1 codec=1; regenerate/rebind runtime");
  if ([CborContract,CodecContract,SchemaContract,JsonCodecContract].some(c=>!c || c.owner!==Foundation.owner || c.contract!==1) ||
      !SchemaContract.irVersions.includes(3) || !JsonCodecContract.oneofSparse)
    throw new ConfigurationError("actual loaded TypeScript codec/schema/JSON artifact is old or incompatible; regenerate/rebind foundation");
}
export type Options = Readonly<Record<string, unknown>>;
function record<T>(values: Readonly<Record<string,T>>): Readonly<Record<string,T>> {
  return Object.freeze(Object.assign(Object.create(null), values));
}
export type TypeDescriptor =
  | Readonly<{kind: "int" | "str" | "bool" | "bytes" | "float"}>
  | Readonly<{kind: "message"; binding: () => MessageBinding<any>}>
  | Readonly<{kind: "enum"; enum: () => EnumDescriptor}>
  | Readonly<{kind: "list"; element: TypeDescriptor}>
  | Readonly<{kind: "map"; key: TypeDescriptor; value: TypeDescriptor}>;
export function typeDescriptor(t: TypeDescriptor): TypeDescriptor {
  if (t.kind === "list") return Object.freeze({kind:t.kind,element:typeDescriptor(t.element)});
  if (t.kind === "map") return Object.freeze({kind:t.kind,key:typeDescriptor(t.key),value:typeDescriptor(t.value)});
  return Object.freeze({...t});
}
export class EnumDescriptor {
  readonly members: Readonly<Record<string,bigint>>;
  readonly options: Options;
  readonly memberOptions: Readonly<Record<string,Options>>;
  readonly owner = Foundation;
  constructor(readonly name:string, readonly qualifiedName:string, members:Record<string,bigint>,
              options:Options={}, memberOptions:Record<string,Options>={}, readonly fingerprint="") {
    this.members=record(members); this.options=snapshot(options); this.memberOptions=snapshot(memberOptions);
    if (!Object.keys(members).length || Object.values(members).some(n=>typeof n!=="bigint"))
      throw new ConfigurationError(`${name}: invalid enum descriptor`);
    Object.freeze(this);
  }
}
export class FieldDescriptor {
  readonly type: TypeDescriptor; readonly options:Options;
  constructor(readonly name:string, readonly attribute:string|null, readonly number:number,
              type:TypeDescriptor, readonly presence:"required"|"nullable"|"missing_ok",
              readonly transient=false, readonly virtual=false, options:Options={}) {
    this.type=typeDescriptor(type); this.options=snapshot(options); Object.freeze(this);
  }
}
export class OneOfDescriptor {
  readonly members:Readonly<Record<string,string|null>>;
  constructor(readonly controllingField:string, readonly enumDescriptor:EnumDescriptor,
              readonly virtual:boolean, readonly exhaustive:boolean, members:Record<string,string|null>) {
    this.members=record(members); Object.freeze(this);
  }
}
export class ConstraintDescriptor {
  readonly parameters:Options;
  constructor(readonly rule:string, parameters:Options={}) { this.parameters=snapshot(parameters); Object.freeze(this); }
}
export class MessageDescriptor {
  readonly fields:readonly FieldDescriptor[]; readonly oneofs:readonly OneOfDescriptor[];
  readonly constraints:readonly ConstraintDescriptor[]; readonly reservedNumbers:readonly number[];
  readonly reservedNames:readonly string[]; readonly options:Options; readonly effectiveOptions:Options;
  readonly fieldsByName:Readonly<Record<string,FieldDescriptor>>;
  readonly groupsByField:Readonly<Record<string,OneOfDescriptor>>;
  readonly payloadsByField:Readonly<Record<string,true>>;
  readonly owner=Foundation;
  constructor(readonly name:string, readonly qualifiedName:string, readonly descriptorContractVersion:number,
              fields:readonly FieldDescriptor[], oneofs:readonly OneOfDescriptor[]=[],
              constraints:readonly ConstraintDescriptor[]=[], reservedNumbers:readonly number[]=[],
              reservedNames:readonly string[]=[], readonly nextId:number|null=null, options:Options={},
              effectiveOptions:Options={}, readonly fingerprint="") {
    this.fields=Object.freeze([...fields]); this.oneofs=Object.freeze([...oneofs]);
    this.constraints=Object.freeze([...constraints]); this.reservedNumbers=Object.freeze([...reservedNumbers]);
    this.reservedNames=Object.freeze([...reservedNames]); this.options=snapshot(options); this.effectiveOptions=snapshot(effectiveOptions);
    this.fieldsByName=record(Object.fromEntries(fields.map(f=>[f.name,f])));
    this.groupsByField=record(Object.fromEntries(oneofs.map(g=>[g.controllingField,g])));
    this.payloadsByField=record(Object.fromEntries(oneofs.flatMap(g=>Object.values(g.members).filter((name):name is string=>name!==null).map(name=>[name,true]))));
    Object.freeze(this);
  }
}
// Typed generated readers receive the current value; static metadata never captures an instance.
export class MessageBinding<T> {
  readonly owner=Foundation;
  constructor(readonly descriptor:MessageDescriptor, readonly read:(value:T,index:number)=>unknown,
              readonly accepts:(value:unknown)=>value is T) { Object.freeze(this); }
}
export class SchemaDescriptor {
  readonly messages:Readonly<Record<string,MessageDescriptor>>;
  readonly enums:Readonly<Record<string,EnumDescriptor>>;
  readonly options:Options; readonly effectiveOptions:Options;
  readonly descriptorContractVersion=1;
  constructor(readonly identity:string, readonly irVersion:number,
              messages:Record<string,MessageDescriptor>, enums:Record<string,EnumDescriptor>,
              options:Options={}, effectiveOptions:Options={}) {
    this.messages=record(messages); this.enums=record(enums); this.options=snapshot(options);
    this.effectiveOptions=snapshot(effectiveOptions); Object.freeze(this);
  }
}
export function requireExternal(value:unknown, fingerprint:string, name:string, category:"message"|"enum"):void {
  const desc = category === "message" ? (value as MessageBinding<unknown>)?.descriptor : value as EnumDescriptor;
  if (!(category === "message" ? value instanceof MessageBinding : value instanceof EnumDescriptor) ||
      !(desc instanceof (category === "message" ? MessageDescriptor : EnumDescriptor)) ||
      desc.owner !== Foundation || desc.fingerprint!==fingerprint)
    throw new ConfigurationError(`${name}: incompatible/missing external ${category} descriptor, facts or split runtime owner; regenerate/rebind child`);
}
export function publish(schema:SchemaDescriptor, bindings:readonly MessageBinding<any>[]):void {
  requireFoundation();
  if (![1,2,3].includes(schema.irVersion)) throw new ConfigurationError("unsupported descriptor IR version");
  if(bindings.length!==Object.keys(schema.messages).length || Object.values(schema.messages).some(d=>!bindings.some(b=>b.descriptor===d)) ||
      Object.values(schema.enums).some(e=>!(e instanceof EnumDescriptor) || e.owner!==Foundation)) throw new ConfigurationError("incomplete/wrong-category schema descriptor bindings");
  const visited=new Set<MessageDescriptor>();
  function effective(options:Options):void {
    const keys=Object.keys(options).sort();
    if(keys.join(",")!=="max_depth,max_encoded_len" || !Number.isInteger(options.max_depth) ||
      (options.max_depth as number)<1 || (options.max_depth as number)>128 ||
      (options.max_encoded_len!==null && (!Number.isInteger(options.max_encoded_len) || (options.max_encoded_len as number)<1 || (options.max_encoded_len as number)>2**31-1)))
      throw new ConfigurationError("unsupported/incompatible effective codec options");
  }
  effective(schema.effectiveOptions);
  function checkType(t:TypeDescriptor):void {
    const expected:Record<string,string>={int:"kind",str:"kind",bool:"kind",bytes:"kind",float:"kind",message:"binding,kind",enum:"enum,kind",list:"element,kind",map:"key,kind,value"};
    if(!t || Object.keys(t).sort().join(",")!==expected[t.kind]) throw new ConfigurationError("invalid type descriptor data");
    switch(t.kind) {
      case "message": if(typeof t.binding!=="function") throw new ConfigurationError("missing typed message link"); check(t.binding()); break;
      case "enum": if (typeof t.enum!=="function" || !(t.enum() instanceof EnumDescriptor) || t.enum().owner!==Foundation) throw new ConfigurationError("invalid enum link/owner"); break;
      case "list": checkType(t.element); break;
      case "map": if (!["str","int","bool"].includes(t.key.kind)) throw new ConfigurationError("invalid map key descriptor"); checkType(t.key);checkType(t.value);break;
      case "int":case "str":case "bool":case "bytes":case "float":break;
      default:throw new ConfigurationError("unknown type descriptor");
    }
  }
  function check(b:MessageBinding<any>):void {
    if (!(b instanceof MessageBinding) || b.owner!==Foundation || !(b.descriptor instanceof MessageDescriptor)) throw new ConfigurationError("missing typed message binding or split owner");
    const d=b.descriptor;
    effective(d.effectiveOptions);
    if (d.descriptorContractVersion!==1) throw new ConfigurationError(`${d.name}: unsupported descriptor version`);
    if (visited.has(d)) return; visited.add(d);
    if (Object.keys(d.fieldsByName).length!==d.fields.length || new Set(d.fields.map(f=>f.number)).size!==d.fields.length ||
        d.fields.some((f,i)=>!(f instanceof FieldDescriptor) || !Number.isSafeInteger(f.number) || f.number<1 ||
          (i>0 && d.fields[i-1].number>=f.number) || !["required","nullable","missing_ok"].includes(f.presence) ||
          typeof f.virtual!=="boolean" || typeof f.transient!=="boolean" || f.virtual!==(f.attribute===null))) throw new ConfigurationError(`${d.name}: invalid field inventory`);
    d.fields.forEach(f=>checkType(f.type));
    const owned=new Set<string>();
    if (Object.keys(d.groupsByField).length!==d.oneofs.length) throw new ConfigurationError("duplicate oneof group");
    for (const g of d.oneofs) {
      const f=d.fieldsByName[g.controllingField];
      if (!(g instanceof OneOfDescriptor) || !f || f.type.kind!=="enum" || f.type.enum()!==g.enumDescriptor || f.virtual!==g.virtual || f.presence!=="required" ||
          typeof g.virtual!=="boolean" || typeof g.exhaustive!=="boolean" ||
          Object.keys(g.members).sort().join("\0")!==Object.keys(g.enumDescriptor.members).sort().join("\0")) throw new ConfigurationError("invalid oneof descriptor links");
      for (const p of new Set(Object.values(g.members))) {
        if (p===null) { if(g.exhaustive) throw new ConfigurationError("nonexhaustive descriptor"); continue; }
        if (!d.fieldsByName[p] || d.fieldsByName[p].presence==="required" || owned.has(p)) throw new ConfigurationError("invalid/shared oneof payload");
        owned.add(p);
      }
    }
    if (d.constraints.length!==d.oneofs.length || d.constraints.some(c=>c.rule!==ONEOF_RULE || !d.groupsByField[String(c.parameters.controlling_field)])) throw new ConfigurationError("unsupported/invalid constraints");
  }
  bindings.forEach(check);
}
