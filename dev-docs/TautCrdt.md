# taut CRDT surface

Status: wire + API surface + type vocabulary DONE; reference engine for lww +
counter DONE; sequence/set engines are a pluggable slot (deferred).

Per the build prompt §4: CRDT must be representable **from day one** — ops/state
on the wire, `local-apply` / `merge-remote` / `sync` in the contract — while a
working convergence engine is **not** a per-platform deliverable.

## Type vocabulary (resolves tautPlan §10.4)

v1 CRDT field-merge types, declared in the IR per field:

| merge | meaning | reference merge |
| --- | --- | --- |
| `lww` | last-writer-wins register | max by `(seq, actor)` |
| `counter` | PN counter | sum of distinct per-`(actor, seq)` deltas |

Both are commutative/idempotent by construction, so the "engine" is arithmetic.
`text`/sequence and sets need a real engine (RGA/Yjs/Automerge) and are **out of
v1** — declaring such a field and using the reference engine raises
`EngineNotBound` (the slot is unbound). Validator enforces: merge ∈ {lww,counter},
scalar-only, counter⇒int.

Example doc (`ir/griplab.taut.py`):
```
Msg("Board",
    F("title", 1, STR, merge="lww"),
    F("votes", 2, INT, merge="counter"))
```

## Wire (representable from day one)

Built-in IR messages — generated as native types in every language, byte-exact in
the corpus (Python/TS/Rust + C++ `static_assert`):

- `CrdtOp { doc, actor, seq, field, value: bytes }` — one change; `value` is the
  CBOR of the field value (set for lww, delta for counter).
- `CrdtState { doc, ops: [CrdtOp], version: [VersionEntry] }` — the
  reconstructible op log + version vector (a late joiner rebuilds state from it).
- `VersionEntry { actor, seq }`.

`CrdtOp` carries the value as opaque bytes so the wire stays engine-agnostic;
`crdt/op`, `crdt/state`, `Board/materialized` are in the golden corpus.

## API surface (`Collab` service)

local-apply / merge-remote / sync, plus a snapshot:
```
board.snapshot    unary        -> CrdtState
board.local_apply unary  (actor, field, value) -> CrdtOp     # apply local change, get op to broadcast
board.merge       unary  (op: CrdtOp)           -> bool       # incorporate a remote op
board.sync        server_stream  shape=crdt, events {op}      # the op feed
```
Declared and validated; the live GripLab slice does not serve it (CRDT is
contract-only for that app — surface present, engine slot empty, as the build
prompt prescribes).

## Reference engine

`taut/crdt/engine.py`: `CrdtEngine` is the slot (Protocol); `ReferenceDoc`
implements lww+counter. Properties proven in `tests/test_crdt.py`:
- **convergence** — two replicas making concurrent ops, exchanged in different
  orders, materialize to the same state;
- **idempotent merge** — re-merging an op is a no-op (no double-count);
- **reconstructible** — a fresh replica rebuilds identical state from a snapshot's
  op log.

Binding Automerge/Yjs for `text` would implement the same `CrdtEngine` Protocol;
nothing else (wire, API, types) changes.
