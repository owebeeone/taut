# Taut — Forward-Compat Residual + OOB Extension Parity

**Status:** Plan — ready to execute.
**Date:** 2026-06-23
**Related:** the FLOAT precedent — [history/TautFloatPlan.md](history/TautFloatPlan.md) (+ `history/TautFloatP2-*`); decisions **D10–D15** in [TautDecisions.md](TautDecisions.md).

## 1. Why

Two forward-compat mechanisms are **not at parity** across taut's 9 targets:

- **Residuals (`wire_residual` / `__unknown__`)** — the code exists in all 7 compiled
  generators, and Python/TS interpreters preserve unknown tags default-on — but
  byte-exactness is gated in-repo **only at the Python reference**; the rest is
  shape-tested with byte parity *verified out-of-band*. Same gap FLOAT had before its
  differential fuzz.
- **OOB extensions (`ext_set` / `ext_get` / `ext_clear`, D13)** — the accessor API exists
  **only in Python** (`src/taut/ext.py`). The other 8 targets get *passive* preservation
  (extensions ride the residual space, D14) but no *active* read/write; non-Python infra
  must hand-roll it.

Goal: bring both to **true byte-exact parity across all 9, proven in-repo** — same
strategy as FLOAT (one reference, parse-free conformance oracle, one agent per language,
a cross-language byte gate).

## 2. The two deliverables differ in shape

- **Residuals = VERIFY (+ fix).** The generated code is already present in all 7 compiled
  langs; the work is to **prove** byte-exact decode→re-encode against a conformance corpus
  and fix any merge-order divergence the gate surfaces. Low effort where already green.
- **Extensions = IMPLEMENT.** Port `ext_set/ext_get/ext_clear` to the 8 non-Python targets
  (a small per-language module over the runtime `Cbor` + the generated extension-message
  type). Net-new code — the bulk of the effort.

## 3. Parity parameters → [TautResExtP2-Base.md](TautResExtP2-Base.md)

The base brief is the contract every Phase-2 agent obeys: the single Python oracle, the two
parse-free conformance corpora, the exact residual + extension semantics (including the
byte-parity traps), and the verification ladder. **Read it first.**

## 4. Plan (phases & steps)

Foundational Phase 0–1 are sequential; **Phase 2 is an 8-way fan-out**; Phase 3 converges.
LOC budgets aspirational (< 500/step).

### Phase 0 — Contract & corpora design *(milestone: locked parity parameters)*
- **0.1** Ratify the residual + extension conformance contract (§ base). Fix the **fixture
  schemas**: a host message + an extension message + a band tag; a residual fixture whose
  vectors carry an **interleaved unknown tag** (a residual tag *between* two known tags) and
  a **band-tag unknown**. Pin the per-language `ext_*` API shape (mirrors `ext.py`). *(~docs)*

### Phase 1 — Python reference + shared surface *(milestone: the fork gate)* — single-threaded
- **1.1** Reference: `ext.py` is the extension oracle; the codec `__unknown__` path is the
  residual oracle. Add reference tests for band-tag-as-residual and the interleaved-unknown
  merge if not already covered. *(~80 LOC)*
- **1.2** Emit + commit the two **parse-free corpora**: `corpus/residual_vectors.json`
  (`encode(decode(wire)) == wire`, incl. interleaved + band-tag unknowns) and
  `corpus/ext_vectors.json` (set/get/clear vs `ext.py`). Wire both into `run_tests.py` regen
  with lockstep gates. *(~180 LOC, mostly data)*
- **1.3** Shared surface: extend the conformance kit (`corpus/kit.py`) to emit per-language
  residual + extension harnesses (like `rust_vectors`); add a vendored `ext.<lang>` runtime
  slot to `_RUNTIMES`/scaffold so Phase-2 agents only drop in their module. Commit the fixture
  schema(s) as IR. *(~150 LOC)*

### Phase 2 — language fan-out *(milestone: all 9 byte-match, residual + extensions)* — 8 worktree-isolated agents
One agent per language (Rust, C++, Swift, Go, Kotlin, JS, Java, **TS — in the `trial` repo**).
Each: (a) **residual** — generate the fixture types `--forward-compat`, run `residual_vectors.json`
decode→re-encode, byte-diff vs the oracle, fix any merge-order divergence; (b) **extensions** —
implement `ext_set/get/clear` (a new `ext.<lang>` over the runtime `Cbor` + the generated ext
type), verify against `ext_vectors.json`; (c) per-language tests; compile + run + differential
fuzz where the toolchain exists. *(~150–350 LOC each.)*

### Phase 3 — convergence & gate *(milestone: parity gated in-repo)*
- **3.1** Cross-language byte gate: drive both corpora through every codec/accessor in-repo —
  closes the out-of-band gap for residuals AND extensions. *(~300 LOC)*
- **3.2** Docs + ratify: `TautDecisions.md` (D13 now all-language; residual byte-gate); README;
  mark this plan done. *(~60 LOC)*

## 5. Risks

1. **Residual merge-interleave** — the #1 byte trap: a residual tag *between* two known tags
   must emit in a single canonical ascending order. The corpus's interleaved + band-tag rows
   are the gate.
2. **Extension nested-map, not bytes** — `ext_set` rides the ext message as a *nested CBOR map*
   (`encode_struct`, not pre-serialized bytes) so the host re-encodes once and the band tag
   sorts canonically. Pre-serializing to bytes would change the wire — a parity break.
3. **TS cross-repo** — the TS codec lives in the `trial` repo (interpreter-style), not the
   taut worktree; oracle corpora must be copied in (as FLOAT did).
4. **C++ ext at runtime** — the C++ codec is constexpr-centric, but `ext_*` operates on runtime
   byte buffers; implement it as a normal (non-constexpr) runtime path over `parse`/`encode_value`.
5. **The flag gate** — `wire_residual` is off by default; a schema with extensions *requires*
   `--forward-compat` (D14, build error otherwise). Keep that invariant intact in every target.
