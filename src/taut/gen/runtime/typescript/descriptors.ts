// Canonical TypeScript foundation. No compiler, authoring loader or validation engine.
import { snapshot } from "./snapshots.ts";
import { CborContract, CborFloat, DecodeError, EncodeError } from "./cbor.ts";
import { CodecContract } from "./codec.ts";
import { SchemaContract } from "./schema.ts";
import { JsonCodecContract } from "./jsoncodec.ts";
import * as cborExports from "./cbor.ts";
import * as codecExports from "./codec.ts";
import * as schemaExports from "./schema.ts";
import * as jsonExports from "./jsoncodec.ts";
import * as extExports from "./ext.ts";
import * as reportExports from "./reports.ts";
export { snapshot } from "./snapshots.ts";
export const ONEOF_RULE = "taut.oneof.v1";
export class ConfigurationError extends Error {}
export const Foundation = Object.freeze({
  owner: "taut.typescript.foundation", descriptorContract: 1, codecContract: 1,
  build: "typescript-oneof-reference.1",
  capabilities: Object.freeze(["codec.v1", "descriptors.v1", "oneof.v1"]),
  codecTypes: Object.freeze({CborFloat, DecodeError, EncodeError}),
});
export function requireFoundation(selected?: unknown): typeof Foundation {
  if (Foundation.owner !== "taut.typescript.foundation" || Foundation.descriptorContract !== 1 || Foundation.codecContract !== 1 ||
      !Array.isArray(Foundation.capabilities) || ["codec.v1","descriptors.v1","oneof.v1"].some(c => !Foundation.capabilities.includes(c)))
    throw new ConfigurationError("compatible TypeScript foundation required: descriptor=1 codec=1; regenerate/rebind runtime");
  if ([CborContract,CodecContract,SchemaContract,JsonCodecContract].some(c=>!c || c.owner!==Foundation.owner || c.contract!==1) ||
      !SchemaContract.irVersions.includes(3) || !JsonCodecContract.oneofSparse)
    throw new ConfigurationError("actual loaded TypeScript codec/schema/JSON artifact is old or incompatible; regenerate/rebind foundation");
  if (selected !== undefined) {
    // Compare actual exported identities, not the facade's labels or this checker's
    // lexical dependencies. Namespace wrappers may differ while genuine re-exports
    // still expose these exact implementation values.
    const check = (actual:unknown, expected:object, where:string):void => {
      if (!actual || (typeof actual!=="object" && typeof actual!=="function")) throw new ConfigurationError(`selected TypeScript foundation missing ${where}; rebind owner`);
      for (const [name,value] of Object.entries(expected)) {
        if (name==="default" || name==="__esModule") continue;
        if ((actual as Record<string,unknown>)[name] !== value) throw new ConfigurationError(`selected TypeScript foundation ${where}.${name} has a missing/incompatible export or split runtime owner; rebind foundation`);
      }
    };
    check(selected, {Foundation,ConfigurationError,ONEOF_RULE,snapshot,typeDescriptor,EnumDescriptor,FieldDescriptor,
      OneOfDescriptor,ConstraintDescriptor,MessageDescriptor,MessageBinding,SchemaDescriptor,requireExternal,publish,requireFoundation}, "exports");
    check(selected,cborExports,"CBOR exports");
    check(selected,reportExports,"report exports");
    for (const [name,expected] of Object.entries({codec:codecExports,schema:schemaExports,jsoncodec:jsonExports,ext:extExports}))
      check((selected as Record<string,unknown>)[name],expected,name);
  }
  return Foundation;
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
  constructor(readonly rule:string, parameters:Options={}) {
    if (typeof rule!=="string" || parameters===null || typeof parameters!=="object" ||
        ![Object.prototype,null].includes(Object.getPrototypeOf(parameters)) ||
        Reflect.ownKeys(parameters).some(k=>typeof k!=="string" || !Object.prototype.propertyIsEnumerable.call(parameters,k)))
      throw new ConfigurationError("invalid portable constraint record/parameters");
    try { this.parameters=snapshot(parameters); }
    catch (_) { throw new ConfigurationError("invalid portable constraint parameter values"); }
    Object.freeze(this);
  }
}
function constraintSnapshot(value:ConstraintDescriptor):ConstraintDescriptor {
  if (!value || typeof value!=="object" || Reflect.ownKeys(value).length!==2 ||
      !Object.hasOwn(value,"rule") || !Object.hasOwn(value,"parameters"))
    throw new ConfigurationError("invalid constraint record shape");
  return new ConstraintDescriptor(value.rule,value.parameters);
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
    this.constraints=Object.freeze(constraints.map(constraintSnapshot)); this.reservedNumbers=Object.freeze([...reservedNumbers]);
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
      if (!(g instanceof OneOfDescriptor) || typeof g.controllingField!=="string" || !f || f.type.kind!=="enum" || f.type.enum()!==g.enumDescriptor || f.virtual!==g.virtual || f.presence!=="required" ||
          typeof g.virtual!=="boolean" || typeof g.exhaustive!=="boolean" ||
          Object.keys(g.members).sort().join("\0")!==Object.keys(g.enumDescriptor.members).sort().join("\0")) throw new ConfigurationError("invalid oneof descriptor links");
      for (const p of new Set(Object.values(g.members))) {
        if (p===null) { if(g.exhaustive) throw new ConfigurationError("nonexhaustive descriptor"); continue; }
        if (!d.fieldsByName[p] || d.fieldsByName[p].presence==="required" || owned.has(p)) throw new ConfigurationError("invalid/shared oneof payload");
        owned.add(p);
      }
    }
    const controls=new Set<string>();
    for (const c of d.constraints) {
      const control=c.parameters.controlling_field;
      if (!(c instanceof ConstraintDescriptor) || !Object.isFrozen(c) || !Object.isFrozen(c.parameters) || c.rule!==ONEOF_RULE ||
          Reflect.ownKeys(c.parameters).length!==1 || !Object.hasOwn(c.parameters,"controlling_field") || typeof control!=="string" ||
          !Object.hasOwn(d.groupsByField,control) || controls.has(control)) throw new ConfigurationError("unsupported/invalid oneof constraint parameters or duplicate control");
      controls.add(control);
    }
    if (controls.size!==d.oneofs.length) throw new ConfigurationError("missing oneof constraint control");
  }
  bindings.forEach(check);
}
