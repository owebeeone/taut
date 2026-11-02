# C++ merged-pair remediation 1 — focused evidence

Status: implementation checks pass; original-reviewer closure and pair acceptance
remain pending. This records new checks of the authorized correction, not a
replacement for the original results or the complete r0 integration receipt.

The private active-message identity now combines the native binding and address.
An enclosing object and its first value child can share an address without being
the same typed message. Real pointer recursion continues to use the same active
ancestor path and predicates. No public generated layout, descriptor/codec ABI,
allocation behavior, native binding interface or dependency changed.

The new regression covers required and optional first children, scalar and
constrained OneOf children, and source/package/supplied modes. Child bindings are
generated independently with validation methods disabled. Valid input yields an
empty complete report and true predicate; the invalid child keeps its real
`child/text` diagnostic, and repair does not mutate the prior report snapshot.

Checks use activated stable CPython 3.13.5 and native Clang 21.1.6/MSVC 19.33;
all outputs stay under
`D:/projects/limbo/cpp-go-oneof-scratch/remediation-r1`.

- `cpp-counterexamples.log` / `.xml`: **18 passed**, 31.97 seconds. The twelve
  new cases plus native reference behavior, genuine recursion and allocation
  faults. These overlap the next run and are not additive totals.
- `cpp-contracts.log` / `.xml`: **109 passed, one deselected**, 148.61 seconds;
  all `test_cpp_oneof.py` and `test_cpp.py` cases except the duplicated parity
  wrapper (`-m 'not gate'`). No failures or skips.
- `cpp-original-counterexample.json`: the original review probe copied without
  changes, freshly emitted canonical source and a C++20/no-RTTI compile yield
  `same_address=1 valid=1 complete=1 fast=1 issues=0`. Original failed probe and
  reports remain preserved under `review-r0`.

The shared integration corrections and fresh compiler wheel check have separate
pair-level R1 receipts. The original complete all-16 parity/broad result remains
the r0 result at its recorded source tuple. No duplicate global gate or standalone
reference-library gate is claimed here. No blocking finding is self-closed.
