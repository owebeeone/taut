# taut — Decisions Log

Pinned design rulings from the refinement pass, so the next build is unambiguous.
Status tags: **BUILT** (in code + tested) · **DECIDED** (agreed, not yet built) ·
**SPEC** (designed in another doc, not built) · **DEFERRED** (intentionally later)
· **OPEN** (still needs a call).

Cross-refs: module system → [TautModules.md](TautModules.md); CRDT →
[TautCrdt.md](TautCrdt.md); orchestration → [TautOrchestration.md](TautOrchestration.md);
distribution/gate → [TautDistribution.md](TautDistribution.md); code shape →
[CodeShape.md](CodeShape.md).

---

## Scope & direction

- **D1. taut is the substrate under Glade, not a product.** Optimize for "the
  smallest thing that lets Glade/Glial be built on the GripLab golden path," not
  feature-completeness. *(DECIDED, lean)*
- **D2. Name = `taut`** everywhere in-code (brand, CLI, **import** package, Rust
  crate, C++ namespace, IR file extension `.taut.py`). The codename "prism" is
  fully retired: no `prism` string remains in either repo's source (build artifacts
  excepted), all suites green post-rename.
  - **PyPI distribution name = `taut-proto`.** PyPI **rejects `taut`** at
    registration ("This project name isn't allowed" — Warehouse's prohibited/
    reserved path, *not* its "too similar" wording; a sibling project `tau` also
    exists). **Correction of an earlier error:** the availability scan read
    `pypi.org/pypi/taut/json` → 404 as "free," but a 404 only means *no released
    project by that exact name* — it is **not** proof of registerability (reserved-
    with-zero-releases also 404s). The only definitive test is an actual upload.
  - Dist ≠ import: `pip install taut-proto` → `import taut` → CLI `taut` (the
    Pillow→PIL pattern). Only `[project].name` carries `taut-proto`; nothing in
    code changes. `taut_proto`/`taut-proto` also covers npm/Go/GitHub-org, where
    `taut` is likewise taken.
  *(BUILT — in-code rename done; dist name `taut-proto` set in pyproject, pending
  the user's registration confirmation)*

## Field model

- **D3. `required` + `optional`, both kept.** `required` is a **governance
  assertion only** — a missing required field decodes to `None`/null, it does **not**
  error at decode. The breaking-change gate makes "add required" and
  "optional→required" breaking. (proto3's lesson, encoded at the gate rather than
  by removing `required`; presence is clean for free: optional→null, required→
  always present.) *(BUILT: optional + gate; required-decode-error explicitly NOT done)*
- **D4. No custom wire defaults.** proto3 removed them for good reasons (default
  not on the wire → versions disagree; changing it reinterprets old data). Native
  *construction* defaults are a per-language binding convenience only. *(DECIDED)*
- **D5. Lists** cover repetition; no separate `repeated`. *(BUILT)*
- **D6. `reserved` (retired tags + names) and `next_id`** are first-class,
  validated message features (not comments). *(BUILT)*
- **D7. Field-name casing**: emitted **verbatim** (snake_case in every language)
  today; idiomatic per-language transform (snake→camel for Go/TS) is a possible
  later uniform generator policy. *(OPEN)*

## Wire & forward-compat

- **D8. Frozen deterministic CBOR** as the wire (hand-rolled, byte-exact, corpus-
  pinned). A canonical-**JSON profile** for near-free language onboarding is a
  possible future. *(BUILT: CBOR; JSON profile DEFERRED)*
- **D9. Forward-compat = unknown-field preservation.** A decoder captures
  unrecognized tags as raw CBOR and re-emits them (canonical order); nested
  preserved; clean messages are byte-identical. *(BUILT in the runtime/dict-level
  codec; NOT yet in the generators)*
- **D10. Residual field = `wire_residual`** (single underscore — C++ reserves any
  identifier containing `__`; no leading underscore). **Reserve the `wire_`
  prefix** in the validator so app fields can't collide. *(DECIDED)*
- **D11. Lazy bag, per-language idiomatic field, no base class.** Rust
  `Option<Vec<(i64,Cbor)>>`; C++ `std::unique_ptr<…>` member (constexpr-null at
  compile time → corpus oracle unaffected); Go plain nil-able field (no embedding,
  same name); Python `dict | None`; TS optional. One shared `collect` helper;
  composition not inheritance (§M3). Same logical name in all languages. *(DECIDED)*
- **D12. Forward-compat is opt-in via an explicit build flag; OFF by default.**
  Declaring an extension **without** the flag is a **build error** (no magic
  auto-on; you enable it eyes-open). The runtime reference codec preserves
  unconditionally (truth-definer); generated code is gated by the flag. *(DECIDED
  — reverses the earlier "emit only sees the schema / no param" idea, deliberately)*

## Extensions (side-channels)

- **D13. Declared, typed extensions** — `extension("Msg", tag)`; tag in the band
  (`BAND_START = 2^20`). Validator: app field tags `< BAND_START`, extension tags
  `>= BAND_START`, unique, message exists. Generic accessors `ext_set/ext_get/
  ext_clear` operate on host **wire bytes** knowing only the extension schema.
  *(BUILT)*
- **D14. Extensions require forward-compat** (they ride the residual space) — see
  D12's build-error rule. *(DECIDED)*
- **D15. Cross-extension tag coordination**: convention + per-build uniqueness
  check now; a registry later if needed. *(DEFERRED)*

## Presence / sentinel

- **D16. No sentinel; use `None`. No field-presence in v1.** We always emit
  fields, so there's no unset-vs-null ambiguity to resolve. If presence is ever
  wanted, the yidl PEP-661 sentinel is the drop-in pattern. *(DECIDED / DEFERRED)*

## RPC surface

- **D22. Method = `(name, in, out, shape)`; `shape` is the sole discriminator.**
  Dropped `kind` — it was redundant with `shape` and only kept consistent by a
  prose rule, so the `kind=unary`+`shape=set` illegal state was representable.
  Now `unary` is a registered shape (the degenerate "delivered once" member) and
  `out` is a uniform slot→type binding over the shape's slots (`output`+`events`
  merged: unary binds `value`, swmr binds `{snapshot, delta}`, …). `kind`/
  `output`/`events` survive only as **derived views** (computed from `shape`+`out`),
  so they can never disagree — illegal states are unrepresentable, not policed.
  Consequence: since shape *is* method-kind, the shape set must stay an **open
  registry** (`register_shape`), never a sealed enum, or taut reinherits
  protobuf's closed-taxonomy problem; the honest caveat is that a shape carries
  behaviour + per-target impl, so it's open to *implemented* shapes only. Applied
  across model/dsl/validate/export/load + the IR + the generic TS client + docs;
  all suites green. *(BUILT)*
- **D17. What we unify = the contract (IR) + the wire protocol** (envelope +
  codec + delivery-shape dispatch). **Not** a per-service class. *(DECIDED)*
- **D18. Floor (always, every language):** a generic IR-driven **client**
  (`call(method, in) -> out`, `subscribe(method, in) -> stream`) and **server**
  (`serve(ir, name→fn)`). The client is **fully JSON-instantiable** (dict args,
  zero codegen). The server is **JSON dispatch + a `name→fn` handler map**; the
  handlers (and stream shape-producers) are the one irreducibly-code piece.
  *(DECIDED; generic client/server exist in trial, currently GripLab-bound)*
- **D19. Opt-in (implementor's choice):** generated **types** (round-trip the
  wire) + a generated **`Handlers` interface** for compile-time endpoint
  verification + optional typed client wrappers. Two verification levels: runtime
  drift check (floor) and compile-time conformance (opt-in interface). Drop the
  per-service `XxxClient`/`XxxHandlers` as *mandatory* — demote to opt-in. *(DECIDED)*
- **D20. `$describe` reflection endpoint** — a well-known method returning the IR,
  so clients learn how to talk to a server dynamically (connect → describe →
  call). Near-free (the server already holds the IR). *(DEFERRED — post-V1)*

## Modules / namespaces

- **D21. Module model** — `module(name, version, langs, imports, decls)`;
  per-language namespaces **declared** (Go/TS not derivable); refs **qualified by
  import handle** (`org.Ref("Address")`), resolved to `{module, name}` at export;
  one JSON artifact per module; workspace lock pins digests; the breaking-change
  gate runs per module. "multi-inheritance" = import DAG (fan-in), not OO
  inheritance. *(SPEC — [TautModules.md](TautModules.md); the next big build)*

## Roadmap

- **D23. v0.2.0 = platform hardening + JSON profile (together), then languages
  (0.3+).** Driven by razel's real integration, which had to *hand-port* `cbor.rs`
  from `wire/cbor.py` and *hand-roll* a corpus/parity kit (`wire/corpus.py` +
  `vectors.rs` + a `corpus_byte_parity` test it labels "Gap 1"), and whose
  generated Rust drops unknown fields. So before fanning out to 5 languages, make
  codegen self-contained and verifiable:
  - **Emit the per-language CBOR runtime** alongside the types (kills the hand-port).
  - **Conformance kit** — `tautc corpus` emits golden vectors + a per-language
    parity test, so no consumer rewrites `vectors.rs`. *(BUILT: auto-synth values
    [`corpus/synth.py`] → neutral `golden.json` + Rust `vectors.rs` harness +
    `--check` drift gate; `corpus/build.py` now routes GripLab through the kit,
    golden byte-identical. C++/other harnesses ride their generators in 0.3+.)*
  - **Forward-compat residual in the generators** (D10–D12: `wire_residual` +
    flag/gate + `wire_` reservation) so compiled targets stop dropping unknowns.
  - **JSON profile** — *(BUILT in 0.2.0 dev)* IR-driven CBOR↔JSON (`taut.wire.
    jsoncodec`: proto3-style int64→string, bytes→base64, enum→name, canonical
    sorted-key JSON; CBOR→JSON→CBOR byte-identical for residual-free values). The
    onboarding enabler ("JSON is ubiquitous") + debug/gateway format. (D8's
    deferred JSON profile, now started.)
  - **Then 0.3+: language generators** — **Go**, **JS/TS**, **Java** and **Kotlin
    as *distinct* generators** (Kotlin uses data classes / null-safety / sealed
    types Java can't express), **Swift**. Each becomes "codec emitter + shipped
    runtime + shipped corpus kit"; JSON-capable langs get a lighter path.
  *(DECIDED — sequencing locked with the user; JSON profile already BUILT)*

## Already-built foundation (for reference)

Delivery shapes (atom/log/stream/swmr/snapshot_delta/crdt) + validator;
deterministic CBOR + golden corpus (Py/TS/Rust runtime, C++ compile-time);
orchestration spec (sdax waves + error policy, tokio binding); CRDT lww/counter
reference engine + pluggable slot; breaking-change gate; generators (Rust/C++
types, Python/TS/scaffold). All **BUILT** and green.

---

## Open questions (decision needed)

1. **Casing policy** (D7) — verbatim vs idiomatic per language. Becomes concrete
   with the 0.3+ language generators (Go/JVM/Swift want idiomatic casing).

*(Resolved: **D2** rename done · **build order** locked as **D23** (platform +
JSON profile, then languages) · **JSON profile** built.)*
