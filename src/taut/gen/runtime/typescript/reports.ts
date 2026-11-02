import { decode, encode } from "./cbor.ts";
export interface ValidationOptions { readonly recursive?:boolean; }
export function recursiveOption(options?:ValidationOptions):boolean {
  if(options===undefined) return true;
  if(options===null || typeof options!=="object" || Array.isArray(options) || Object.keys(options).some(k=>k!=="recursive") ||
      (options.recursive!==undefined && typeof options.recursive!=="boolean")) throw new TypeError("ValidationOptions.recursive must be Boolean");
  return options.recursive ?? true;
}
export function base64(bytes:Uint8Array):string { let s=""; for(const b of bytes) s+=String.fromCharCode(b); return btoa(s); }
export class PathSegment {
  constructor(readonly kind:"field"|"index"|"key", readonly fieldName:string|null=null,
              readonly index:number|null=null, readonly keyType:string|null=null, readonly keyCborBase64:string|null=null) {
    let good=false;
    if(kind==="field") good=typeof fieldName==="string" && index===null && keyType===null && keyCborBase64===null;
    if(kind==="index") good=typeof index==="number" && Number.isSafeInteger(index) && index>=0 && fieldName===null && keyType===null && keyCborBase64===null;
    if(kind==="key" && fieldName===null && index===null && ["str","int","bool"].includes(keyType!) && typeof keyCborBase64==="string") {
      try {
        const bytes=Uint8Array.from(atob(keyCborBase64),c=>c.charCodeAt(0)); const value=decode(bytes);
        good=base64(bytes)===keyCborBase64 && typeof value===({str:"string",int:"bigint",bool:"boolean"} as Record<string,string>)[keyType!] && base64(encode(value))===keyCborBase64;
      } catch { good=false; }
    }
    if(!good) throw new TypeError("invalid validation path segment"); Object.freeze(this);
  }
  static forField(name:string):PathSegment { return new PathSegment("field",name); }
  static forIndex(index:number):PathSegment { return new PathSegment("index",null,index); }
  static forKey(type:string, bytes:Uint8Array):PathSegment { return new PathSegment("key",null,null,type,base64(bytes)); }
}
function pathSnapshot(path:readonly PathSegment[]):readonly PathSegment[] {
  if(!Array.isArray(path) || path.some(p=>!(p instanceof PathSegment))) throw new TypeError("path requires shared PathSegment values");
  return Object.freeze([...path]);
}
function strings(...values:unknown[]):void { if(values.some(v=>typeof v!=="string")) throw new TypeError("diagnostic fields must be strings"); }
export class ValidationIssue {
  readonly path:readonly PathSegment[];
  constructor(readonly code:string, readonly rule:string, path:readonly PathSegment[], readonly message:string) {
    strings(code,rule,message); this.path=pathSnapshot(path); Object.freeze(this);
  }
}
export class DeferredCheck {
  readonly path:readonly PathSegment[];
  constructor(readonly rule:string, path:readonly PathSegment[], readonly reasonCode:string, readonly message:string) {
    strings(rule,reasonCode,message); this.path=pathSnapshot(path); Object.freeze(this);
  }
}
export class ValidationReport {
  readonly issues:readonly ValidationIssue[]; readonly deferredChecks:readonly DeferredCheck[];
  constructor(issues:readonly ValidationIssue[]=[], deferredChecks:readonly DeferredCheck[]=[], readonly scope:"local"|"recursive"="recursive") {
    if(!["local","recursive"].includes(scope) || issues.some(i=>!(i instanceof ValidationIssue)) || deferredChecks.some(d=>!(d instanceof DeferredCheck))) throw new TypeError("invalid shared ValidationReport inputs");
    this.issues=Object.freeze([...issues]);this.deferredChecks=Object.freeze([...deferredChecks]);Object.freeze(this);
  }
  isValid():boolean { return this.issues.length===0; }
  isComplete():boolean { return this.deferredChecks.length===0; }
}
