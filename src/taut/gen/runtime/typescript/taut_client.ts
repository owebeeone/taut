// IR-driven WebSocket client. Reads the service contract from the same neutral
// IR the Python server uses: per method it knows the param/output/event TypeRefs,
// encodes args and decodes results via the CBOR/IR codec. The envelope rides as
// JSON; payload values are base64(CBOR). No per-method code is hand-written here
// beyond the generic call/subscribe — the contract drives everything.
//
// A payload that does not decode fails what it belongs to (TautCheckedDecode.md
// CD-E3): a call's promise rejects with the DecodeError itself, and a stream ends,
// as unsubscribing does, and hands the DecodeError to its onError. Neither escapes
// the socket's message handler.

import { type SchemaIndex, type TypeRef, methodEvents, methodOutput } from "./schema.ts";
import { decodeRef, encodeRef } from "./codec.ts";

const b64 = (bytes: Uint8Array): string => Buffer.from(bytes).toString("base64");
const unb64 = (s: string): Uint8Array => new Uint8Array(Buffer.from(s, "base64"));

interface Envelope {
  messageId: string;
  kind: string;
  method?: string;
  streamId?: string;
  seq?: number;
  event?: string;
  payload?: Record<string, string>;
  error?: { code: string; message: string };
}

type Pending = { resolve: (v: unknown) => void; reject: (e: Error) => void; output: TypeRef | null };
type StreamHandler = (event: string, value: unknown) => void;
type StreamErrorHandler = (error: Error) => void;
type Stream = { handler: StreamHandler; onError?: StreamErrorHandler; events: Map<string, TypeRef> };

export class tautClient {
  private nextId = 0;
  private pending = new Map<string, Pending>();
  private streams = new Map<string, Stream>();
  private ws: WebSocket;
  private schema: SchemaIndex;

  private constructor(ws: WebSocket, schema: SchemaIndex) {
    this.ws = ws;
    this.schema = schema;
    ws.onmessage = (e: MessageEvent) => this.onMessage(String(e.data));
  }

  static connect(url: string, schema: SchemaIndex): Promise<tautClient> {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(url);
      ws.onopen = () => resolve(new tautClient(ws, schema));
      ws.onerror = () => reject(new Error(`failed to connect to ${url}`));
    });
  }

  private id(prefix: string): string {
    return `${prefix}${++this.nextId}`;
  }

  private encodeArgs(method: string, args: Record<string, unknown>): Record<string, string> {
    const m = this.schema.method(method);
    const payload: Record<string, string> = {};
    for (const p of m.params) payload[p.name] = b64(encodeRef(this.schema, p.type, args[p.name]));
    return payload;
  }

  call(method: string, args: Record<string, unknown> = {}): Promise<unknown> {
    const m = this.schema.method(method);
    const messageId = this.id("c");
    const env: Envelope = { messageId, kind: "request", method, payload: this.encodeArgs(method, args) };
    return new Promise((resolve, reject) => {
      this.pending.set(messageId, { resolve, reject, output: methodOutput(m) });
      this.ws.send(JSON.stringify(env));
    });
  }

  // `onError` hears why a stream ended early: an event whose payload does not decode.
  subscribe(
    method: string,
    args: Record<string, unknown>,
    onEvent: StreamHandler,
    onError?: StreamErrorHandler,
  ): () => void {
    const m = this.schema.method(method);
    const streamId = this.id("s");
    const events = new Map<string, TypeRef>(methodEvents(m));
    this.streams.set(streamId, { handler: onEvent, onError, events });
    const env: Envelope = {
      messageId: this.id("c"),
      kind: "request",
      method,
      streamId,
      payload: this.encodeArgs(method, args),
    };
    this.ws.send(JSON.stringify(env));
    return () => this.unsubscribe(streamId);
  }

  // Ends a stream once: it is forgotten and the server told, however often it is called.
  private unsubscribe(streamId: string): void {
    if (!this.streams.delete(streamId)) {
      return;
    }
    this.ws.send(JSON.stringify({ messageId: this.id("c"), kind: "request", method: "$unsubscribe", streamId }));
  }

  private onMessage(data: string): void {
    const env = JSON.parse(data) as Envelope;
    const value = (t: TypeRef | null) =>
      t && env.payload?.value !== undefined ? decodeRef(this.schema, t, unb64(env.payload.value)) : undefined;

    if (env.kind === "stream-event") {
      const streamId = env.streamId ?? "";
      const stream = this.streams.get(streamId);
      if (stream && env.event) {
        const t = stream.events.get(env.event);
        let event: unknown;
        try {
          event = t ? value(t) : undefined;
        } catch (e) {
          // Fail closed: later events may build on this one, so the stream ends here.
          this.unsubscribe(streamId);
          stream.onError?.(e as Error);
          return;
        }
        stream.handler(env.event, event);
      }
      return;
    }
    const p = this.pending.get(env.messageId);
    if (!p) {
      return;
    }
    this.pending.delete(env.messageId);
    if (env.kind === "error") {
      p.reject(new Error(env.error?.message ?? "error"));
      return;
    }
    let result: unknown;
    try {
      result = value(p.output);
    } catch (e) {
      p.reject(e as Error); // the DecodeError itself, the call's failure
      return;
    }
    p.resolve(result);
  }

  close(): void {
    this.ws.close();
  }
}
