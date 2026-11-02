# Rust OneOf checkpoint — operator authority and boundaries

Date: 2 November 2026 (Australia/Sydney). This records the operative task
directives for review; it is not a new agent-defined prerequisite or release plan.

The root coordinator chat `01a19add-ce78-7941-a091-8f3ebddba3d2` delegated this
Rust implementation and relayed the user's subsequent coordination decisions.
The original implementation direction was to implement the Rust backend of
`OneOf-ExplicitValidation-BuildProposal.md` against the saved Python reference,
directly in `D:\projects\limbo`, without a worktree or work in another project.
The user explicitly superseded the earlier stop-at-Python/documentation-only
instructions: get Python and Rust working and committed; defer the other seven.

Production was held read-only while Python's final review ran. Rust requirement,
ABI/lifetime, engine and composition probes were developed in a separate Limbo
scratch area. The coordinator cleared production writes after both Python
reviewers reported GO and its scoped commits completed:

- Taut Python checkpoint: `7182764c4a3da372557deb6fc6f8f4b7d5f90a05`.
- Python shape integration: `c08c2a1b5197f761c5b0b835c588da512130ceda`.
- Managed Python workspace receipt: `2183e4bc89f08837bc2a497e9f2680292ed8ba85`.
- Rust shape baseline: `959f0f048a671347c0940962c5299ae117d92f8a`.

The later user direction explicitly authorizes a committed and pushed GitHub
**checkpoint after Python and Rust are done**. The user corrected themselves:
this is **not a release**. No tags, registry publication or release operations are
authorized. After the verified combined checkpoint, the root coordinator owns
continuation of the other seven targets, two at a time. This Rust chat must not
start those targets. These directives supersede earlier no-commit/no-push stops.

The Rust implementation must retain the proposal's behavior and the detailed
delegation constraints, particularly:

- Mandatory public `Message::descriptor() -> &'static MessageDescriptor` and
  metadata/adapters in both generation modes. Optional instance methods are
  exactly validate, validate_with_options, is_valid and is_valid_with_options;
  `ValidationOptions` has public `recursive: bool`, Default true.
- Shared immutable descriptor/report foundation, static recursive links, owned
  report snapshots/read-only getters, original paths, open string codes and usize
  indices. Boolean success requires validity and completeness without a report.
  Local/recursive behavior, supported-child continuation, canonical CBOR key paths,
  virtual deferral and native OneOf/Case rules must match Python.
- Mutable invalid drafts remain serializable/repairable. Codecs retain structural
  checks independently; dense CBOR/ordinary nullable policies stay intact. Use
  Rust's actual supported JSON route rather than inventing an assumed parser.
- Probe the concrete safe typed/lifetime ABI before backend integration. Include
  primitive/enum reads and owned child/list/map traversal. No common message
  base/discovery trait, reflection, unsafe casts, per-field heap wrappers,
  per-instance metadata graph or fabricated Rust ownership cycle.
- Canonical codec/descriptor/report/validation sources belong in base Taut once
  per language. The existing `taut-shape-rs` library owns higher-level behavior;
  preserve its no_std+alloc core and re-export one actual nominal runtime owner.
  No fictional pre-existing `taut-rs` repository/package is assumed.
- Implement real source, package and legacy application-supplied delivery;
  distribution is independent of optional methods. External Rust types require
  the actual owner's metadata/bindings; no foreign message inherent impls or
  forced dependency regeneration. Old/version/owner/capability failures must be
  explicit. Prove Cbor/error/descriptor/issue/report identity with the actual
  library and independently generated enabled-parent/disabled-child builds.
- Preserve the finalized Python preflight/ownership/shared-use protections.
  Protect handwritten, modified, unknown and incompatible files, preflight the
  complete output set and retain shared components. Target-specific naming must
  reject actual Rust collisions rather than copy Python private-name rules.
- Reuse the verified Windows toolchains and existing native model/IR/corpus;
  install no tools/packages at generation time. Run executable Rust conformance,
  existing Rust/no_std/library checks, relevant shared/Python regressions, both
  distributions and compatibility cases. Disclose baseline limits honestly.
- Use GWZ for workspace status, staging, commits and managed receipts. Stage only
  an explicit Rust/shared/library/documentation allowlist; preserve Python's
  excluded generated bundles/wheel and unrelated work. Review the final checkpoint
  using the applicable review loop and file its evidence before the combined push.

Concrete crate/module names, adapter layout, local Cargo binding and output
inventory are implementation choices within that mandate. Their feasibility and
the final interfaces are recorded in the draft and runnable examples; those
choices are reviewable and are not treated as additional operator requirements.
