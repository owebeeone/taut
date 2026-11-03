# YIDL records patch release — controlling DRAFT

Status: DRAFT release boundary. Target versions are yidl-dataclass0.1.2 then
taut-proto0.11.2. The human said to do a point release after authorizing the
cloned YIDL change and a Python-only Taut compiler-option prototype. This
authorizes required readiness, qualification, review, Gearu tags/GitHub Releases,
OIDC publication, fresh registry consumers and final workspace receipts.

## Problem and authorized remedy

YIDL's freezable model reserves freeze, which conflicts with a legal Taut schema
field. Add a configurable YIDL freeze_method with default freeze, then centralize
Taut's choice in taut.records.taut_dataclass. Taut's Python-only --python-records
option defaults to stdlib and selects YIDL explicitly. Taut already reserves
_taut_ field names, so _taut_freeze does not remove ordinary schema names.

Scope: these two Python projects, their tests/docs/package/release machinery and
the final existing GWZ Taut member receipt. Astichi1.1.3 and YIDL0.1.2 stay public
reference dependencies; no SDK changes or rebuilds. Existing Python/Rust/TS shape
and Rust foundation0.11.0 stay unchanged. The original35 untracked artifacts,
protected5 author files, enum.case and unrelated/contract member heads stay preserved.

## Contract and compatibility

Keep ordinary stdlib generation and base Python>=3.10 support. The yidl extra
requires yidl-dataclass>=0.1.2,<0.2; YIDL supports CPython3.12–3.15 under its
existing platform boundary. Reject an explicit record option without a Python
target before writes. In mixed generation, only Python code changes. Runtime
delivery and validation remain independent. Generation never installs packages.

YIDL validates configured names, reserves the selected name only, keeps model
inheritance names consistent and uses each resolved child's configured method.
No shallow-freeze, field-callback, hashing or optimistic failure contract changes.
Taut generates schema-derived hooks for nullable/recursive children and containers;
lists become tuples and copied maps become FrozenDict. Shared child identity is
retained. Type validation accepts frozen representations only for a frozen YIDL
record; stdlib and mutable-record rules remain strict. Ownership/descriptor/codecs
stay in one nominal Taut foundation. A new records.yidl.v1 capability fails closed
against an old foundation; mixed stdlib external children require regeneration
for deep freezing. Freeze is not automatic validation and may leave partial
completion after an exception. No thread-safety, atomicity or speed claim is made.

## Required evidence and order

The prototype passed302 YIDL tests/two version-specific skips,1069 Python-facing
Taut tests/zero skips, and six installed source/package/supplied x validation
OFF/ON consumers on Windows3.13. This is not exhaustive release qualification.
Prototype commits ab148a5 (YIDL) and1e5567d (Taut) remain immutable history.

First qualify YIDL through Gearu's complete3.12–3.15/both-engine source and
installed wheel/sdist matrix. Settle exact paired source commits, run the same
two peer-blind axes using the canonical review-loop template, file reports
verbatim and merge findings. At most two reviewers and bounded remediation.
After GO and exact candidate gates, publish YIDL0.1.2 via Gearu/OIDC and verify
public bytes/provenance and a fresh configurable-name consumer.

Then Taut's configured strict Gearu gate must use that actual public dependency:
every collected required native/WSL case runs with zero skip/failure/omission,
all16x88 parity variants, canonical Rust/package checks and raw wheel smoke.
The supported hosted3.10/3.11 stdlib tests keep running; only new YIDL execution
cases skip there because the optional backend does not support those minors.
Hosted3.12/3.13/3.15 installs the yidl extra and must exercise the backend. There
is no broad test deselection or weakened strict release gate.

Publish only the qualified unchanged Taut source with Gearu's immutable0.11.2
tag/GitHub Release. Require terminal-success hosted CI/PyPI, exact public wheel/
sdist comparison, fresh public OFF/ON nested and separately generated-child
consumers, then GWZ capture/commit/push with remote dependency proof. Never
republish a tag, manufacture another foundation version or access the revoked
bootstrap credential. Neither public success nor workspace completion is
inferred from a queued workflow, local wheel or earlier prototype acceptance.
