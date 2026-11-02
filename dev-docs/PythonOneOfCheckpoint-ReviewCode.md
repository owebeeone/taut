# PythonOneOfCheckpoint — CODE + SURFACE-AXIS REVIEW

**Review object:** Python reference checkpoint, hash-identified working tree, frozen for review on 2026-11-02. Source inventory: `af9f2516f0dcbf45853fb6ade39d207c7a84b6b282975bffa8fdd385b59cc996`, 165 files, recorded in `D:/projects/limbo/taut-dev/taut/dev-docs/PythonOneOfCheckpoint-Snapshot.json`.

**Baseline:** taut HEAD `2cfee5d6156b0179066dc4eed70f60cde489a422`; taut-shape-py HEAD `da79bfb74376802edcd25049ed4ce29de814db44`. Current source was read directly and compared with baseline using read-only Git inspection. The operator prohibits commits; the source inventory identifies the reviewed working-tree bytes.

**Date:** 2026-11-02

**Axis:** Code architecture, interfaces, compatibility and public Surface. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — three P2 findings block. I pre-commit to GO on a revision that resolves P2-1, P2-2 and P2-3 as specified, with their closure tests and the focused conformance gates passing.

---

## 0. Evidence base

The following controlling material was read:

- `C:/Users/gianni/.codex/skills/review-loop/SKILL.md`.
- `D:/projects/limbo/taut-dev/AGENTS.md`, `AGENTS_GWZ.md`, and the component `AGENTS.md` files.
- `D:/projects/limbo/taut-dev/taut/dev-docs/PythonOneOfCheckpoint-Draft.md`.
- `D:/projects/limbo/taut-dev/taut/dev-docs/OneOf-ExplicitValidation-BuildProposal.md`, including the Python-relevant descriptor, publication, validation, distribution, compatibility and conformance requirements in sections 2–8.
- The referenced behavioral proposal, `D:/projects/limbo/taut-dev/taut/dev-docs/OneOf-ExplicitValidation-PROPOSAL.md`.
- The executable example README at `D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/README.md`.

The current-source CLI help and example README were read before implementation/design inspection. An initial plain-Python command resolved the installed baseline package; its help was discarded as checkpoint evidence. Subsequent CLI/application probes used the supplied activation script and current source.

Implementation inspection covered:

- Canonical facts, rule checks, contracts, immutable descriptors and typed publication.
- Native DSL, IR export/loading, schema validation and compatibility classification.
- Python generation, scaffold forwarding and runtime ownership planning.
- Shared validation traversal, report construction and Boolean short-circuiting.
- JSON projection and the codec fact-import changes.
- Shape-library foundation aliases, lazy imports, static schema loading, regeneration tooling and representative generated types.
- Both focused conformance test files.

Verification performed:

1. At the beginning and end, from `D:/projects/limbo`:

   ```text
   python -B taut-dev/taut/dev-docs/examples/python-oneof/review_snapshot.py --check taut-dev/taut/dev-docs/PythonOneOfCheckpoint-Snapshot.json
   ```

   Both checks returned the assigned digest and **165 files**. Command-local `safe.directory` Git inspection confirmed both assigned HEADs unchanged.

2. Current-source focused tests:

   ```text
   python -B -m pytest taut-dev/taut/src/tests/test_oneof.py taut-dev/taut/src/tests/test_python_runtime_distribution.py -q -p no:cacheprovider --basetemp D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/scratch/review-code/pytest-verified
   ```

   Result: **105 passed in 7.86s**. An earlier invocation encountered a missing parent directory for the reviewer’s scratch basetemp; after creating that scratch directory, the verified run passed. This was review harness setup, not a product defect.

3. Scratch CLI walkthrough: source generation with validation; isolated `-I -S -B` application import/use; validation disabling; source-to-package transition; restoration through `--with-runtime`. All succeeded.

4. In-memory and scratch counterexamples for all three findings below. No reviewed source was edited.

5. Existing evidence inspected:

   - Feature log: 105 passed.
   - Shape-library log: 190 passed.
   - Core regression log: 809 passed.
   - Codec parity log: all 16 variants GREEN, clean governance.
   - Wheel verification: 12 foundation files matched canonical source, isolated application behavior and actual library type identity checked.
   - `baseline-evidence.json`: unchanged-source hashes, isolated HEAD reproduction of the missing document and two Go newline failures, Java encoding reproduction/correction, and Git ownership reproduction/correction.

These counts describe separate runs and are not added into a new aggregate total.

## Problem, requirement provenance, and scope

The requested outcome is the complete Python reference batch through the existing native compiler route: native OneOf/Case facts and IR, mandatory shared immutable descriptors, optional thin instance methods, one shared report/Boolean engine, explicit validation, sparse oneof JSON, canonical runtime distribution, and shape-library integration without application-time compiler imports.

The original operator authority recorded in the review prompt supersedes the build proposal’s older documentation-only authorization. Editable implementation components are taut’s Python/compiler/runtime/tests and the necessary taut-shape-py integration. Other backends are regression/reference dependencies. Releases, commits, pushes, tags, toolchain changes and application graph rules are outside scope. Virtual selection remains deliberately deferred.

The changes address observed gaps through the existing `emit` route. Extracting shared fact types and generating static shape-library facts directly supports the required compiler-free application graph; the isolated import tests exercise that route. No new dependency or infrastructure prerequisite was required by this review.

The three blockers are localized Python defects. None requires changing another backend, adding infrastructure, or expanding the authorized outcome. The missing baseline document and Windows Go newline failures have concrete unchanged-HEAD evidence and do not block this Python checkpoint.

## 1. Findings

### [P2-1] Python private-name mangling produces successfully generated bundles that cannot import

**Location:** `D:/projects/limbo/taut-dev/taut/src/taut/gen/python.py:9–11`, `:25–31`, `:79–86`, and `:106–107`; failure is detected later by `D:/projects/limbo/taut-dev/taut/src/taut/descriptors.py:147–149`.

**Violated invariant:** Generated attribute identities must match actual host slots, and unsupported host-name projections must fail before output writes. A schema accepted by generation must not produce an unusable module.

**Reproduction:**

```python
s = schema(Msg("Record", F("__private", 1, INT)))
assert validate(s) == []
emit(s, output, langs=["python"],
     runtime_mode="source", validation=True)
```

Generation succeeds and writes a 16-file source bundle. An isolated import of its `api` module fails:

```text
taut.contracts.ConfigurationError:
Record.__private: missing generated slot __private
```

Python mangles the field’s slot to `_Record__private`. `field_attribute()` records `__private`, and the collision preflight does not reject this name. The final `compile()` check succeeds because compilation does not execute descriptor publication. The same binding mismatch exists with validation disabled because descriptors are mandatory.

**Impact:** A valid native schema produces files and reports generation success, but its generated API cannot be imported in either validation mode.

**Required correction:** Account for Python mangling in the recorded generated identity, including collision checking, or explicitly reject unsupported private-name fields during generation preflight before writing anything. Preserve original schema names in descriptors and diagnostic paths.

**Closure test:** Exercise `F("__private", 1, INT)` through `emit`, with validation both off and on and source/package delivery. Either generation must reject it with a named preflight diagnostic and unchanged outputs, or isolated import and field access must succeed using the correctly recorded host identity. If supported, also verify recursive issue paths retain `__private`.

### [P2-2] The referenceable-enum API leaves metadata-colliding members without a supported qualified reference

**Location:** `D:/projects/limbo/taut-dev/taut/src/taut/facts.py:80–83`; `D:/projects/limbo/taut-dev/taut/src/taut/ir/dsl.py:108` and `:161–167`.

**Violated invariant:** The production field-local API must provide an unambiguous qualified enum-member reference or an explicit namespace policy. The behavioral proposal specifically identifies this prototype limitation and requires a production escape or policy at `D:/projects/limbo/taut-dev/taut/dev-docs/OneOf-ExplicitValidation-PROPOSAL.md:501–505`.

**Reproduction:**

```python
choice = Enum("Choice", name=0)
Case(tag=choice.name)
```

This raises:

```text
TypeError: Case requires a qualified enum member
```

`choice.name` returns the definition’s metadata string. The same failure occurs for members named `members` and `options`. `EnumDef.__getattr__` only runs after ordinary attribute lookup, so it cannot resolve these collisions. The production DSL supplies no alternate qualified member accessor or declared reservation policy.

**Impact:** Previously expressible enum member names cannot participate in the advertised OneOf/Case authoring API. The diagnostic identifies the resulting wrong value type, without explaining the namespace collision or giving a supported remedy. Manually constructing compiler-model `EnumMemberRef` objects is not the promised public authoring surface.

**Required correction:** Provide and document an unambiguous public qualified-member escape, or establish an explicit, early checked namespace policy with a clear migration diagnostic. Do not silently substitute the definition’s metadata value for a member reference.

**Closure test:** Cover `name`, `members`, and `options` through the supported production authoring API. For a supported escape, generate and run oneof validation with those choices and verify enum ownership is retained. For a reservation policy, prove declaration fails early with the member name and reason. Ordinary `Choice.payload` syntax and wrong-enum rejection must remain covered.

### [P2-3] Compatibility classification rejects unrelated compatible additions to oneof messages

**Location:** `D:/projects/limbo/taut-dev/taut/src/taut/ir/compat.py:102–104`.

**Violated invariant:** The compatibility gate must distinguish actual constraint/projection changes from unrelated field changes. Its existing contract explicitly permits adding an ordinary `optional=MISSING_OK` field.

**Reproduction:**

```python
choice = Enum("Choice", payload=0, empty=1)

old = schema(
    choice,
    Record=Msg(
        kind=F(1, OneOf(choice)),
        data=F(2, STR, Case(kind=choice.payload)),
    ),
)

new = schema(
    choice,
    Record=Msg(
        kind=F(1, OneOf(choice)),
        data=F(2, STR, Case(kind=choice.payload)),
        later=F(3, INT, optional=MISSING_OK),
    ),
)
```

Both schemas validate without errors. `diff(old, new)` returns:

```text
breaking: Record oneof constraints/projection changed
compatible: Record.later (tag 3) added (missing_ok)
```

Consequently, `check_or_raise(old, new)` rejects the compatible addition. Merely reversing the declaration order of the original fields also produces the breaking oneof diagnostic, despite unchanged tags, normalized descriptors and rule associations.

The new comparison includes **every field name and declaration position**, even fields with neither `oneof` nor `cases`.

**Impact:** Existing compatible schema evolution is incorrectly blocked whenever the containing message has a oneof group. The error falsely attributes ordinary additions or declaration reordering to a semantic/projection change.

**Required correction:** Compare normalized constraint-bearing facts keyed by stable field identity, independently of unrelated fields and declaration order. Keep genuine OneOf/Case changes and virtual wire-field changes visible to compatibility classification.

**Closure test:** Verify that adding an unrelated `MISSING_OK` field and reordering declarations produce no breaking constraint change. Also verify that changing case ownership, controlling field, virtual/exhaustive policy, or removing a rule still produces the intended breaking result.

## 2. Invariant analysis

The following attacks did not refute the implementation:

- **Native retention:** OneOf/Case facts survive version-3 export/loading. Older versions cannot carry these keys silently. Unconstrained exports retain version 2.
- **Publication and immutability:** Generated messages share frozen descriptor values and immutable registries. Type links and typed class bindings are checked before public attachment. Recursive references use registry identities rather than expanding nested graphs.
- **Independent dependencies:** The focused matrix imports independently generated parents/children, including enabled parents and disabled children, through source/source, package/package, mixed modes and supplied runtime. Missing/old child metadata and split runtime ownership are rejected.
- **Shared validation:** Report and fast methods use the same event generator. Focused cases cover independent groups, wrong discriminators, nonselected children, virtual deferrals, shared child paths, cycles, list/map traversal, canonical key paths and immutable report snapshots.
- **Serialization:** Sparse JSON omits absent Case payloads while preserving zero, false, empty text and empty lists. Invalid combinations remain serializable. Dense CBOR policy remains separate.
- **Application graph:** Source runtime files come from canonical sources. Import-blocking tests exercise codecs, descriptors, validation and actual shape-library wire use without compiler/authoring/build imports. Foundation aliases preserve nominal report, descriptor and codec identities.
- **Contracts:** Contract compatibility is separated from exact generator patch labels; incompatible owner/contracts/capabilities and missing runtime exports fail explicitly.

### Surface walkthrough

The current-source help places generation under `gen` and explains runtime omission, source/package selection, the legacy alias, validation default off, mandatory descriptors and dependency mappings. Runtime selection and validation selection are independent.

Using the existing example schema and only scratch outputs, the walkthrough produced:

| Action | Observed result |
| --- | --- |
| `--runtime source --with-validation` | Generated 16 files; isolated application returned valid and complete |
| Regenerate with `--runtime source` | Methods removed; validation engine removed |
| Regenerate with `--runtime package` | Unused source descriptor runtime removed; manifest records package |
| Regenerate with `--with-runtime` | Source runtime restored |

Focused tests additionally cover repeated agreeing flags, conflicting/unknown flags, programmatic forwarding, shared runtime users and modified/handwritten file protection.

There is no install lifecycle to complete: this generator installs no package. The remaining public API shape blockers are P2-1 and P2-2.

## 3. Risks and next action

This verdict covers the assigned Python checkpoint only. Virtual selection remains intentionally incomplete. Other backend feature implementation and releases remain outside scope.

The inspected broad regression evidence does not establish an entirely green repository suite; it explicitly retains the unrelated baseline failures. The 105-test focused pass likewise does not cover the three counterexamples above.

The next action is one merged remediation patch resolving P2-1, P2-2 and P2-3, followed by their closure tests and focused re-review against a newly recorded source inventory. The reviewed source digest and both repository HEADs remained unchanged through the final verification.
