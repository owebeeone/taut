# taut v0.10.0: options, checked decode and the legacy codec's removal

**Status:** PLAN, 2026-09-30, on the owner's "All 14 as recco. Go". It builds two decisions, every
question ruled (a):
- D26, checked decode ([TautCheckedDecode.md](TautCheckedDecode.md));
- D27, options ([TautOptions.md](TautOptions.md)).

It also removes the legacy codec (D1's sunset, [TautCodecParityPlan.md](TautCodecParityPlan.md)).
It ends with a tree ready to tag. The tag, the shape packages' 0.10 train and the clients' moves are
the owner's to start (§4).

## 0. What v0.10.0 contains

**Options (D27).**
- `taut/src/taut/ir/options.py` holds the definitions, the `option` namespace, `effective()` and
  the floor checks.
- The DSL takes option values at file, message, field and enum level; the model stores them.
- `validate` gains a `lint` channel for warnings.
- IR version 2: raw `options` at all seven levels, and `effective` at file and message.
- The compatibility gate, plus a generator refusal for unimplemented wire options.
- The first two options are `max_depth` (default 32, ceiling 128) and `max_encoded_len` (no default,
  declared values at most 2^31 − 1).

**Bounds (D26 §3), in all nine languages.**
- New tags `TooDeep{limit}` and `TooLarge{len, limit}`.
- A raw decode that counts depth and takes an optional depth, capped at 128, and an optional length.
- Per root, a typed decode from bytes that applies the root's effective bounds. Generated targets
  emit `MAX_DEPTH`, `MAX_ENCODED_LEN` and `decode` per message. Python and TypeScript read the
  schema's or the IR's `effective`.

**The rest of D26:**
- Question 9: `DuplicateMapKey.key` is the key as text: an int in decimal, a str as itself, a bool
  as `true` or `false`.
- Question 10: the gate also runs the seven generated targets built with `--forward-compat`, and
  pins the unknown-field round trip.
- CD-E4: the extension helpers are fail-closed. A host that is not a map is `WrongType{map}`. A host
  is decoded at the depth ceiling with no length bound (TautOptions.md G3).
- CD-E3: TypeScript lets nothing but `DecodeError` escape, and `taut_client.ts` catches it.
- Rust gains `DecodeError::tag()`, reads lengths with `usize::try_from`, and keeps duplicate keys in
  a set.

**The legacy codec goes (question 5).**
- Removed: `--legacy-codec`, `fail_closed=False`, the legacy `cbor.rs` template and its banner.
- Rust's panicking `decode()` and accessors go.
- Every language's panicking or aborting decode entry point goes: Go's `Decode`, `Get`, the
  panicking `XFromCbor` wrappers and `ext.go`; Swift's `fatalError` accessor.
- The corpus emitter and `glade_build` move to the fail-closed path. `glade_build` writes into
  glade only when `run_tests.py` runs it, which no step does.

**Found on the way, fixed here:**
- A field named like a generated local breaks generated code (a Java field `m`). A fixture message,
  `Names`, makes every generator compile such fields.
- Kotlin cannot generate a field-less message with `--forward-compat`.

**Governance:**
- `CodecContract.md` (the parity plan's Phase 5.1).
- Parity contract `taut-codec-parity/i64/v1`.
- The documents.

**Not in v0.10.0:**
- G2, question 7: a follow-up with its own rows.
- client-ts, question 8.
- Providers (OPT-F5): no provider code exists; the rule binds the first one.
- The version needs no bump: setuptools-scm takes it from the tag.

## 1. Phases and steps

Each step is one goal, aimed below 500 lines. A→B→C are foundations; D's steps run in parallel,
one agent per language.

### Phase A: the rulings (done with this plan)
Both notes mark their questions ruled, and `TautDecisions.md` gains D26 and D27.

### Phase B: options, in Python
| Step | Goal | After |
|---|---|---|
| B1 | `options.py` (OPT-D1-D6, L1), the model's `options` (L3), the DSL's positional option values with rebuilds through `dataclasses.replace` (L2); unit tests | A |
| B2 | `validate` (L4): registered name, level, type and range; per-root floors and ceilings, roots including method slots; `lint` for the two warnings (OPT-D4, D5) | B1 |
| B3 | IR version 2 (I1-I3, F4): export and load, all seven levels, `effective`, unknown version or name refused, `effective` recomputed and checked; the four committed `.ir.json` re-exported; TypeScript's `schema.ts` reads version 2 and refuses an unknown version or wire option | B1 |
| B4 | compatibility (K1-K4) and the generator refusal (F2): each target's implemented wire options beside `_LANGS` | B1 |

### Phase C: the gate
| Step | Goal | After |
|---|---|---|
| C1 | Python's bounds, the reference: `cbor.loads(data, *, max_depth=32, max_encoded_len=None)`, the two tags, `codec.decode` resolving through `effective()`, `ext.py` fail-closed | B |
| C2 | The bounds rows (CD-C1-C4): `bounds.vectors.json` B1-B30 and its six fixture messages; segmented `bytes`, `len`, `limits`; header constants; typed rows through the typed entry point, with each runner reporting its constants and the row's resolved bounds; contract v1. Python GREEN, the other eight allowlisted. | B, with C1 |
| C3 | Question 10's forward-compat variants (`<target>/fc`) and rows that apply by whether a codec keeps unknown fields; question 9's rows pinning the key as text; the `Names` fixture | C2 |

### Phase D: one step per language per wave (parallel)
| Wave | Goal per language | Done when |
|---|---|---|
| D1 | the two tags; raw depth and length bounds with the caller's limits; typed decode from bytes (generated: constants and `decode` per message; typescript: from the IR's `effective`); the runner speaks C2's protocol | GREEN on the B rows |
| D2 | question 9's payload; the fc variant GREEN; fail-closed extension helpers; no panicking or aborting decode entry point (rust: the whole legacy path, the corpus emitter, `glade_build`); `Names` compiles | GREEN everywhere, de-listed |

The languages are rust, python (C1 covers D1), typescript, js, cpp, swift, go, kotlin and java.

### Phase E: close
| Step | Goal |
|---|---|
| E1 | `CodecContract.md`, `Reference.md`, `TYPESCRIPT_API.md`, `RustFailClosed.md`; the two notes and D26/D27 marked built; `docs/examples/tasks/generated/` regenerated |
| E2 | The final gate: nine targets and seven fc variants GREEN, allowlist empty, full suite; a release-readiness report for the owner |

## 2. How it lands
As in the parity pass:
- Each step works in a scratch export of taut with a throwaway git, and hands back a patch.
- The lane owner applies the patches with `git apply --3way` and resolves the expected shared-file
  conflicts by rule.
- The lane owner then runs the full suite and the gate on a copy of the working tree, and commits
  each step through gwz.
- Nothing is pushed or tagged without the owner's word.

## 3. What each step must keep
- Encode is byte-identical for everything that encoded before. Every golden corpus stays unchanged.
- Every control-flow body a step writes is braced.
- `run_tests.py` is never run: it writes into glade.

## 4. After this plan: the owner's to start
1. The v0.10.0 tag, and PyPI.
2. The shape packages' 0.10 train (CD-V3):
   - taut-shape raises its pin;
   - taut-shape-rs re-vendors `cbor.rs`, its generated files and `parity_vectors.rs`, and caps its
     frame length;
   - taut-shape-ts re-copies its runtime and fixes `framing.ts`.
3. glade's node step and client-rs (CD-G1-G4). They regenerate `wire-rs` at the tag and drop
   `checked.rs` and `wellformed.rs`. glade's schema declares `max_encoded_len`, and `frame_len` takes
   its limit from it.
4. gwz-dev regenerates in its own lane; client-ts follows the node step (question 8).
