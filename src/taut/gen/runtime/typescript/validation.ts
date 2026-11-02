import { encode, I64_MIN, I64_MAX } from "./cbor.ts";
import { ConfigurationError, Foundation, MessageBinding, ONEOF_RULE, type TypeDescriptor } from "./descriptors.ts";
import { PathSegment, ValidationIssue, DeferredCheck, ValidationReport, recursiveOption, type ValidationOptions } from "./reports.ts";
export const ValidationEngine = Object.freeze({contract:1, owner:Foundation});
type Path=readonly PathSegment[];
type Event=readonly [boolean,string,string,Path];
function issue(code:string,path:Path,rule="validation.shape.v1"):Event { return [false,code,rule,path]; }
function primitive(kind:string,value:unknown):boolean {
  switch(kind) {
    case "int":return typeof value==="bigint" && value>=I64_MIN && value<=I64_MAX;
    case "float":return typeof value==="number";
    case "str":return typeof value==="string";
    case "bool":return typeof value==="boolean";
    case "bytes":return value instanceof Uint8Array;
    default:return false;
  }
}
export function compareCanonical(a:Uint8Array,b:Uint8Array):number {
  for(let i=0;i<Math.min(a.length,b.length);i++) if(a[i]!==b[i]) return a[i]-b[i]; return a.length-b.length;
}
function* walkType(value:unknown,t:TypeDescriptor,path:Path,ancestors:Set<unknown>):Generator<Event> {
  if(t.kind==="message") { yield* walk(value,t.binding(),path,ancestors,true);return; }
  if(t.kind==="list" || t.kind==="map") {
    if(t.kind==="list" ? !Array.isArray(value) : !(value instanceof Map)) {yield issue("validation.type_mismatch",path);return;}
    if(ancestors.has(value)) {yield issue("validation.ownership_cycle",path);return;}
    ancestors.add(value);
    try {
      if(t.kind==="list") for(let i=0;i<(value as unknown[]).length;i++) yield* walkType((value as unknown[])[i],t.element,[...path,PathSegment.forIndex(i)],ancestors);
      else {
        const entries:[Uint8Array,unknown][]=[];
        for(const [key,child] of value as Map<unknown,unknown>) {
          if(!primitive(t.key.kind,key)) yield issue("validation.type_mismatch",path);
          else entries.push([encode(key as string|bigint|boolean),child]);
        }
        entries.sort((a,b)=>compareCanonical(a[0],b[0]));
        for(const [bytes,child] of entries) yield* walkType(child,t.value,[...path,PathSegment.forKey(t.key.kind,bytes)],ancestors);
      }
    } finally {ancestors.delete(value);} return;
  }
  if(t.kind==="enum" ? typeof value!=="string" || !Object.hasOwn(t.enum().members,value) : !primitive(t.kind,value)) yield issue("validation.type_mismatch",path);
}
function* walk(value:unknown,b:MessageBinding<any>,path:Path,ancestors:Set<unknown>,recursive:boolean):Generator<Event> {
  if(!(b instanceof MessageBinding) || b.owner!==Foundation) throw new ConfigurationError("incompatible typed binding/runtime owner");
  if(!b.accepts(value)) {yield issue("validation.type_mismatch",path);return;}
  if(ancestors.has(value)) {yield issue("validation.ownership_cycle",path);return;} ancestors.add(value);
  try {
    const d=b.descriptor;
    for(let i=0;i<d.fields.length;i++) {
      const f=d.fields[i], group=d.groupsByField[f.name]; const fieldpath=[...path,PathSegment.forField(f.name)];
      if(group) {
        if(group.virtual) yield [true,"oneof.virtual_deferred",ONEOF_RULE,fieldpath];
        else {
          const tag=b.read(value,i);
          if(typeof tag!=="string" || !Object.hasOwn(group.members,tag)) yield issue("oneof.invalid_discriminator",fieldpath,ONEOF_RULE);
          else {
            const selected=group.members[tag], payloads=new Set(Object.values(group.members));
            for(let j=0;j<d.fields.length;j++) { const p=d.fields[j]; if(!payloads.has(p.name)) continue;
              const child=b.read(value,j), pp=[...path,PathSegment.forField(p.name)];
              if(p.name===selected && child==null) yield issue("oneof.payload_missing",pp,ONEOF_RULE);
              else if(p.name!==selected && child!=null) yield issue("oneof.payload_unexpected",pp,ONEOF_RULE);
            }
          }
        }
      }
      if(recursive && !f.virtual && !group) {
        const child=b.read(value,i);
        if(child===undefined) {if(f.presence!=="missing_ok" && !d.payloadsByField[f.name]) yield issue("validation.type_mismatch",fieldpath);}
        else if(child!==null) yield* walkType(child,f.type,fieldpath,ancestors);
        else if(f.presence==="required") yield issue("validation.type_mismatch",fieldpath);
      }
    }
  } finally {ancestors.delete(value);}
}
export function validateRecord<T>(value:T,binding:MessageBinding<T>,options?:ValidationOptions):ValidationReport {
  const recursive=recursiveOption(options),issues:ValidationIssue[]=[],deferred:DeferredCheck[]=[];
  for(const [later,code,rule,path] of walk(value,binding,[],new Set(),recursive)) {
    if(later) deferred.push(new DeferredCheck(rule,path,code,"virtual selection is deferred"));
    else issues.push(new ValidationIssue(code,rule,path,code));
  }
  return new ValidationReport(issues,deferred,recursive?"recursive":"local");
}
export function isRecordValid<T>(value:T,binding:MessageBinding<T>,options?:ValidationOptions):boolean {
  const events=walk(value,binding,[],new Set(),recursiveOption(options));
  try{return events.next().done===true;}finally{events.return(undefined);}
}
