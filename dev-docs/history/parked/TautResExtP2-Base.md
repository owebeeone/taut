# Taut Res+Ext Parity — Phase 2 Base Brief (all language ports)

Read this first. Your per-language brief (`TautResExtP2-<Lang>.md`) adds the specifics.
Companion to [TautResExtPlan.md](TautResExtPlan.md). Same playbook as FLOAT
([history/TautFloatP2-Base.md](history/TautFloatP2-Base.md)) — reuse your language's FLOAT
brief for the `Cbor` value-model idiom (enum vs struct vs tagged vs structural).

## Mission
Bring **two** forward-compat mechanisms to byte-exact parity with the Python reference in ONE
target language: (A) **residual** unknown-tag preservation (`wire_residual`), and (B) the
**extension** accessor API (`ext_set`/`ext_get`/`ext_clear`). One agent per language, isolated
worktree, only your own files. TypeScript is now an in-repo runtime-resource target under
`src/taut/gen/runtime/typescript/`.

## The single oracle
Correctness == reproducing the **Python** bytes. The reference is `src/taut/wire/codec.py`
(the `__unknown__` residual path) and `src/taut/ext.py` (the extension accessors). Two
parse-free conformance corpora encode that truth. Phase 1 has landed the shared surface (✅):
- **`ir/resext.taut.py`** — the shared fixture (`Host` + extension `Decision` + band-tag
  extension). **`tautc gen` your types from THIS schema** so all 8 languages are byte-comparable.
  (Where the per-language briefs say `ExtMsg` / `to_cbor` / `from_cbor`, that's the fixture's generated
  `Decision` type.)
- `corpus/residual_vectors.json` — residual round-trip vectors (`encode(decode(wire)) == wire`,
  incl. an interleaved unknown tag and a band-tag extension riding as residual).
- `corpus/ext_vectors.json` — extension set/get/clear vectors (`{op, host, value, expect}` hex).
- Your `ext.<lang>` runtime slot is already wired in `_RUNTIMES`/`emit()` — drop your file into
  `gen/runtime/` and `tautc gen --with-runtime` vendors it (you still do NOT edit `scaffold.py`).
Raw CBOR **hex** in/out, keyed on bytes (never on parsed values). For every row your codec /
accessors must reproduce the exact `expect` hex.

---

## PARITY PARAMETERS (the contract — obey exactly)

### A. Residual semantics (`wire_residual`)
1. **Decode captures every unknown tag** — any wire tag the schema doesn't name, *including
   band tags (≥ `BAND_START = 2^20`)* — into the language-idiomatic residual field
   (`wire_residual`, a list of `(tag, Cbor)` pairs; `__unknown__` in the Py/TS interpreters).
2. **Encode re-emits known fields + residual in a SINGLE canonical ascending-tag order.** This
   is the #1 byte trap: a residual tag that sorts *between* two known tags (e.g. unknown `2`
   between known `1` and `3`) must interleave correctly — not be appended after the known
   fields. A clean message (no unknowns) carries no residual field/key. (Residual verification is
   specifically **wire decode → re-encode**; the merge assumes `wire_residual` is already in ascending
   tag order, which decode guarantees. If a test/accessor ever *constructs or mutates* `wire_residual`
   directly, it must sort by tag before emitting, or the merge can produce non-canonical bytes.)
3. **Round-trip is byte-identical:** `encode(decode(wire)) == wire` for every residual vector.
4. **Flag/gate (keep intact):** `wire_residual` is **off by default**, on via the
   `--forward-compat` generator flag. A schema that declares an **extension** *requires* the
   flag — generating a compiled target without it is a **build error** (D12/D14). The `wire_`
   field-name prefix is reserved by the validator.

### B. Extension accessor semantics (mirror `ext.py` exactly)
Operate on the **top-level CBOR map** of host wire bytes, knowing only the *extension's* schema
(never the host's). **Band check FIRST, before decoding the host** (matches `ext.py`'s `_check`): a
**below-band tag (`tag < BAND_START` = 2^20) is a hard error** — the reference raises `ValueError`;
each port raises its language-idiomatic equivalent (panic / throw / `IllegalArgumentException` /
`Result::Err` — match the convention your `Cbor` accessors already use, and state it in your brief).
These error paths are **not in the corpus** (all vectors are valid + above-band) — cover them with a
per-language unit assertion, not a corpus row.
- **`ext_set(host_bytes, tag, ext_value) -> bytes`** — encode the extension message to a **nested
  CBOR map value** (the generated ext type's `to_cbor`, **NOT** pre-serialized bytes), set/replace
  it at `tag` on the decoded host map, then **encode the whole host once** so the global
  key-sort places the band tag canonically. (Pre-serializing to bytes would change the wire — a
  parity break.)
- **`ext_get(host_bytes, tag) -> ExtMsg | null`** — `null/None` if `tag` absent; else decode the
  nested map at `tag` via the ext type's `from_cbor`.
- **`ext_clear(host_bytes, tag) -> bytes`** — schema-free: decode host map, remove `tag`, re-encode.
- **Host must decode to a top-level CBOR map.** A non-map host is an error — mirror the reference's
  natural failure (Python raises when indexing/popping a non-dict); do NOT silently coerce a
  scalar/array host into a map carrying only the extension. Not in the corpus; don't invent recovery.
- The host app stays oblivious: decoding the host with its own schema leaves the extension riding
  in the residual (band tag in `wire_residual`/`__unknown__`).

The per-language *surface* may be idiomatic (typed vs generic), but the **output bytes must match
`ext_vectors.json`** AND the verification harness MUST exercise the **generated ext type's
`to_cbor`/`from_cbor`** — build the `ext_set` value by calling the generated type's `to_cbor` (never
a hand-rolled or pre-serialized byte blob), and reconstruct on `ext_get` via `from_cbor`. A
generic-`Cbor`-only helper that byte-matches the corpus *without* round-tripping the generated type
does not prove parity — the point is the typed path, not just map surgery. For the `get` vectors the
harness compares **bytes**: re-encode whatever `ext_get` returns and compare to `expect` (the `absent`
row's `expect` is the literal string `null`). The runtime `Cbor` map gives you `get` + entry iteration
+ map construction + a key-sorting `encode`; do set/replace/remove by rebuilding the entry list
(filter out `tag`, append the new pair) and letting `encode` sort.

---

## Scope — touch ONLY your files
Your brief names them: the runtime (`cbor.<lang>` — residual accessor already exists), the
generator (`gen/<lang>.py` — `wire_residual` emission already exists), a **new `ext.<lang>`**
accessor module, and tests. **Do NOT edit** `ir/*`, `wire/cbor.py` / `codec.py`, `ext.py`,
`gen/scaffold.py`, the corpus generators, or another language's files — Phase 1 lands the shared
surface. **No new dependencies. Do NOT touch the FLOAT/encode byte path** the differential fuzz
already proved.

## Workflow (AGENTS.md Rule 0 — TDD)
1. **Residual first (verify):** generate the fixture types `--forward-compat`; run the residual
   vectors decode→re-encode; byte-diff vs the corpus. If green, residual is done — fix only a
   real divergence (almost always the merge-interleave order). Write a failing test, fix, green.
2. **Extensions (implement):** TDD the `ext.<lang>` module against `ext_vectors.json` (set/get/clear).
3. **Prove byte-exactness.** (a) **Corpus parity is the HARD, checked-in gate** — every residual + ext
   vector byte-matches. (b) A **differential fuzz** is *supporting evidence*, not a checked-in gate:
   - A **deterministic, fixed-seed** loop you hand-write in plain stdlib (NO fuzzing framework — "no new
     deps" means a plain RNG/loop). State the seed.
   - **≥1000 iterations:** random known/unknown int tags in `[0, 2^21)` over scalar/text/bytes/small-array
     values; include at least one **interleaved** unknown (sorts between two known tags) and one **band**
     tag (≥ 2^20). For each: assert your codec round-trips byte-identical to the oracle, and
     `ext_set/get/clear` match `ext.py`. On any divergence print the input hex, both output hexes, and the seed.
   - **The oracle is the installed Python package.** Compiled, stdlib-only targets have no JSON parser, so
     **the pytest side owns corpus/fuzz I/O**: Python loads the JSON (or generates seeded rows), emits a
     generated vector table into a temp harness source alongside the vendored `cbor.<lang>` + generated
     `api.<lang>` + `ext.<lang>`, then compiles + runs it (the FLOAT shape). The compiled harness only
     decodes hex, runs the op, and prints pass/fail + the mismatch count (must be 0).
   - **If the toolchain is absent**, mark the fuzz "not run" and report it — corpus parity still gates the phase.
4. Keep the suite green: `PYTHONPATH=src python -m pytest src/tests -q` (or `python run_tests.py`). Use
   whichever `python`/`python3` on your machine has pytest.

## Definition of done
Residual round-trip byte-matches every residual vector; `ext_set/get/clear` byte-match every ext
vector (compiled + run where possible); per-language tests green; the flag/gate invariant intact;
no other files touched; no new deps.
