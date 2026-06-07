# Prism Modules, Compatibility & Extensions — design

Status: **forward-compat + extensions are built** (pre-alpha+); the **module /
namespace system is specified here for the next build** — it's deferred as its
own pass because it ripples through every language consumer and the regen gate,
and shouldn't be rushed into the byte-exact path.

What we're optimizing for (recap): Prism is the **substrate under Glade**, not a
product. So this takes the genuinely-useful protobuf features (packages/imports,
forward-compat, extensions) at a fraction of the weight, keeps the IR small, and
stays wire-neutral where it can.

---

## 1. Modules & namespaces (SPEC — next build)

A module is `(logical namespace, version, per-language namespaces, imports,
decls)`. One artifact per module (→ a content digest for distribution).

```python
common = use("acme.common", "1.0.0")           # import handle (pins a version)
MODULE = module("acme.orders", version="1.0.0",
    imports=[common, geo, org, catalog],
    langs={"python": "acme.orders", "rust": "acme_orders", "cpp": "acme::orders",
           "go": "github.com/acme/proto/orders", "ts": "@acme/orders"},
    decls=[
        Msg("Order",
            F("id",      1, common.Ref("Id")),     # cross-module ref via handle
            F("ship_to", 2, geo.Ref("Address")),   # acme.geo.Address
            F("bill_to", 3, org.Ref("Address"))),  # acme.org.Address — same name, no clash
    ])
```

- **Per-language namespaces are declared**, because Go import paths / TS packages
  / crate names are *not* derivable from the logical name (Python/Rust/C++ can
  default; Go/TS must be explicit).
- **Refs are qualified by import handle** (`org.Ref("Address")`); unqualified
  `Ref` = local. Name collisions resolve by namespace, in every target
  (`acme_geo::Address` vs `acme_org::Address`, etc.).
- **Wire-neutral**: names/modules aren't on the wire (tags are). This is purely
  IR resolution + codegen namespace mapping; the CBOR corpus is untouched.

### Per-module JSON

```jsonc
{
  "prism": 1, "module": "acme.orders", "version": "1.0.0",
  "langs": { /* per target */ },
  "imports": [ {"module": "acme.geo", "version": "1.0.0"}, /* … */ ],
  "enums": [], "messages": [
    { "name": "Order", "fields": [
      {"name":"ship_to","tag":2,"type":{"k":"msg","module":"acme.geo","name":"Address"}, /* … */},
      {"name":"bill_to","tag":3,"type":{"k":"msg","module":"acme.org","name":"Address"}, /* … */}
    ]}
  ],
  "services": [], "extensions": []
}
```
Refs are **fully resolved at export** (`{module, name}`), so a consumer never
re-resolves aliases — the collision is already disambiguated in the bytes. The
shape registry is a Prism built-in, not embedded per module.

### Workspace lock (reproducible build / distribution)

```jsonc
{ "prism": 1, "modules": {
    "acme.geo":    {"version": "1.0.0", "digest": "sha256:…"},
    "acme.orders": {"version": "1.0.0", "digest": "sha256:…"} } }
```
Imports resolve by digest, not sibling path — this is what kills the cross-repo
coupling and grounds OCI distribution. The breaking-change gate runs per module.

### Delta vs today's flat schema (the next build)

Two changes only: the **envelope** gains `module/version/langs/imports`; **enum/
msg refs gain `"module"`**. Everything else (fields, reserved/next_id, merge,
services, extensions) is unchanged. The work is in resolution + per-language
namespace mapping across all consumers (TS reader, Rust/C++ generators, regen
gate) — hence a dedicated pass.

---

## 2. Field model decisions (settled)

- **required vs optional**: kept both. `required` is a *governance assertion*, not
  a decode-time check (a missing required field decodes to `null`, doesn't error).
  The breaking-change gate makes "add required" / "optional→required" breaking —
  which is the protobuf lesson (proto3 removed `required` because it can't evolve)
  encoded at the gate instead of by amputation. We also get clean **presence** for
  free (optional → explicit null; required → always present).
- **No custom wire defaults.** proto3 removed them for good reasons (the default
  isn't on the wire, so versions disagree; changing it reinterprets old data).
  Native *construction* defaults are a binding convenience, never the contract.
- **Lists** cover repetition; no separate `repeated`.

---

## 3. Forward compatibility (BUILT, default-on)

Unknown-field preservation: a decoder captures tags it doesn't recognize as raw
CBOR (`__unknown__`), and re-emits them on encode (merged, canonical order). So an
old node that **decodes → touches → re-encodes** a newer message doesn't destroy
the fields it doesn't understand. (Pure pass-through of raw bytes preserves
everything trivially; this covers the decode-reencode middlebox.)

- Nested unknowns preserved for free (raw subtree kept).
- Corpus-safe: messages with no unknowns produce identical bytes.
- Mirrors protobuf's own history (proto3 dropped unknowns in 3.0, restored in 3.5
  because it broke proxies).

`prism/src/prism/wire/codec.py`; tests in `test_forward_compat.py`.

> Note: the *core codec* (neutral dict/struct) preserves unknowns. Carrying them
> through a language's *typed binding* (a dataclass/struct field) is a per-binding
> enhancement, not yet wired in the trial slices.

---

## 4. Extensions / side-channels (BUILT)

Infra piggybacks metadata (load-balancing, tracing, routing) on any message
without the app knowing — proto2's genuinely-useful "extensions", made minimal.

- **Tag-space partition**: app field tags `< BAND_START` (= `2^20`); extensions
  sit at/above it. The validator enforces the partition, so app evolution and
  infra piggybacking never collide.
- **Declared, typed**: `extension("Decision", tag=0x100001)` binds a message to a
  band tag. Validator checks band + uniqueness + message exists.
- **Generic accessors** (`prism/ext.py`) operate on the host's **wire bytes**
  knowing only the extension schema, never the host's:
  ```python
  raw = ext_set(schema, raw, "Decision", tag, {"backend": "b7", "hops": 1})
  d   = ext_get(schema, raw, "Decision", tag)   # -> dict | None
  raw = ext_clear(raw, tag)                      # strip before delivery
  ```
- The host app decodes/handles/re-encodes obliviously; the extension rides in
  `__unknown__` and survives — so this is **almost free given forward-compat**.

`test_forward_compat.py` covers attach/read/clear + host-obliviousness + the band.

This is the right *layer*: load-balancing/routing are infra (Glial-tier) concerns
riding the Prism wire, decoupled from the app schema and handler.

---

## Build status

| feature | status |
| --- | --- |
| forward-compat (unknown-field preservation, default-on) | ✅ built |
| declared extensions + band + accessors | ✅ built |
| required/optional/defaults decisions | ✅ settled |
| modules / namespaces / per-language ns / imports / qualified refs | spec — next build |
| per-module JSON + workspace lock + per-module gate | spec — next build |
| typed-binding unknown carry-through (Rust/C++/TS structs) | spec — next build |
