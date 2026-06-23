# Taut Res+Ext Parity — Phase 2 Base Brief (all language ports)

Read this first. Your per-language brief (`TautResExtP2-<Lang>.md`) adds the specifics.
Companion to [TautResExtPlan.md](TautResExtPlan.md). Same playbook as FLOAT
([history/TautFloatP2-Base.md](history/TautFloatP2-Base.md)) — reuse your language's FLOAT
brief for the `Cbor` value-model idiom (enum vs struct vs tagged vs structural).

## Mission
Bring **two** forward-compat mechanisms to byte-exact parity with the Python reference in ONE
target language: (A) **residual** unknown-tag preservation (`wire_residual`), and (B) the
**extension** accessor API (`ext_set`/`ext_get`/`ext_clear`). One agent per language, isolated
worktree, only your own files. **TS runs in the `trial` repo, not the taut worktree** (see the
TS brief).

## The single oracle
Correctness == reproducing the **Python** bytes. The reference is `src/taut/wire/codec.py`
(the `__unknown__` residual path) and `src/taut/ext.py` (the extension accessors). Two
parse-free conformance corpora encode that truth:
- `corpus/residual_vectors.json` — residual round-trip vectors.
- `corpus/ext_vectors.json` — extension set/get/clear vectors.
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
   fields. A clean message (no unknowns) carries no residual field/key.
3. **Round-trip is byte-identical:** `encode(decode(wire)) == wire` for every residual vector.
4. **Flag/gate (keep intact):** `wire_residual` is **off by default**, on via the
   `--forward-compat` generator flag. A schema that declares an **extension** *requires* the
   flag — generating a compiled target without it is a **build error** (D12/D14). The `wire_`
   field-name prefix is reserved by the validator.

### B. Extension accessor semantics (mirror `ext.py` exactly)
Operate on the **top-level CBOR map** of host wire bytes, knowing only the *extension's* schema
(never the host's). Band check first: `tag >= BAND_START` (2^20), else error.
- **`ext_set(host_bytes, tag, ext_value) -> bytes`** — encode the extension message to a **nested
  CBOR map value** (the generated ext type's `to_cbor`, **NOT** pre-serialized bytes), set/replace
  it at `tag` on the decoded host map, then **encode the whole host once** so the global
  key-sort places the band tag canonically. (Pre-serializing to bytes would change the wire — a
  parity break.)
- **`ext_get(host_bytes, tag) -> ExtMsg | null`** — `null/None` if `tag` absent; else decode the
  nested map at `tag` via the ext type's `from_cbor`.
- **`ext_clear(host_bytes, tag) -> bytes`** — schema-free: decode host map, remove `tag`, re-encode.
- The host app stays oblivious: decoding the host with its own schema leaves the extension riding
  in the residual (band tag in `wire_residual`/`__unknown__`).

The per-language *surface* may be idiomatic (typed vs generic), but the **output bytes must match
`ext_vectors.json`**. The runtime `Cbor` map already gives you `get` + entry iteration + map
construction + a key-sorting `encode`; do the set/replace/remove by rebuilding the entry list
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
3. **Prove byte-exactness** where the toolchain exists: corpus parity + a **differential fuzz** vs
   the Python oracle (random schemas/values + injected unknown tags for residual; random ext
   messages + band tags for extensions). Show commands + the mismatch count.
4. Keep the suite green: `PYTHONPATH=src python3 -m pytest src/tests -q`.

## Definition of done
Residual round-trip byte-matches every residual vector; `ext_set/get/clear` byte-match every ext
vector (compiled + run where possible); per-language tests green; the flag/gate invariant intact;
no other files touched; no new deps.
