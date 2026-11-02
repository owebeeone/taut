# C++ implementation handoff

3 November 2026. **REVIEW-READY / production HOLD.** This is preparation for the
combined C++/Go review, not a verdict, freeze, staging/commit authority or release.

The activated tooling was stable CPython 3.13.5, Clang 21.1.6, MSVC 19.33.31630
and the existing native standard-library/link environment. Existing pytest/build
packages were reused through PYTHONPATH; third-party pytest autoload was disabled.
No toolchain/dependency upgrade, installation, registry access, manifest dependency
change, lock/version change, push or tag occurred.

The complete C++ drafting gate was:

```powershell
python -m pytest src/tests/test_cpp.py src/tests/test_cpp_oneof.py src/tests/test_cpp_go_distribution.py -q --basetemp D:/projects/limbo/cpp-go-oneof-scratch/pytest-settled-cpp
```

Observed result: **87 passed in 189.13 seconds**, no failures, skips or deselections.
This contains the 22 existing C++ tests, then-current 64 feature cases and one
combined C++/Go wheel case. Included totals are not additional results. The run's
stdout was observed through the tool session; the retained target receipt is a
summary, not a fabricated raw log or a before/after source capture.

This precedes the final shared previous-owner pre-lock guard, additional state
tests and a narrow C++ prewrite naming correction. C++ runtime/codec/engine bytes
did not change afterward. The new cross-target state checks and final association
are recorded below;
87 is not relabeled as a final-current full-suite/broad result.

The native gate exercises real source/package/supplied generation and execution,
MSVC and Clang with RTTI disabled, Python-normalized reports, mandatory engine-free
metadata, owned reports, static descriptor publication, primitive/enum borrowed
reads, vectors/maps, native recursion/cycles, per-path shared children, Boolean
equivalence, local/recursive scope, virtual incompleteness, zero/false/empty,
invalid-draft dense CBOR round trips, retained native residual/nullable/missing-ok
behavior, names/collisions and metadata-like enum values through native IR.
It substitutes actual linked contract exports and an old checker, links independent
disabled children across four source/package combinations, rejects old children
and duplicate source owner definitions, and checks real external fact mismatches.
Long and i64-boundary map keys test unsigned canonical ordering and owned paths.

Allocation injection is real: the first fallback constructor, move/copy, root
issue/deferred ranges, strings and all getters execute while every allocation
fails. Successive report allocations are then individually failed. The Boolean
sink returns false on resource failure and constructs no report/diagnostic/path
containers. Fallback has one root resource-exhausted issue and one root deferred
entry, static text and empty paths, without an SSO premise or broad catch/success.

The initial legacy run exposed three new drafting failures, all corrected: the
emitter had disabled unrelated constexpr codecs when any schema used indirection,
and had rejected an existing same-name field projection. The exact three affected
tests passed, and all existing C++ tests passed in the 87-case run. None was called
a baseline failure or suppressed.

The final naming audit closed an omitted prewrite collision: a message named like
its own descriptor/binding method (or its opted-in validation methods) would have
failed native compilation, and several new helper type/concept names were missing
from the reservation inventory. The focused final naming gate passed **21 tests
in 11.46 seconds**, with no failures/skips/deselections. It includes named rejection
before any writes and real compile/run proofs that validation-named messages remain
allowed when methods are disabled. The [raw log](results/naming-final.log) and
[JUnit receipt](results/naming-final.xml) retain this final source association.
Normal conformance example API bytes still match fresh final-generator output.

The combined wheel case builds an actual compiler wheel and compares every
C++/Go canonical resource. An isolated `-I -S` process imports only that extracted
wheel, emits both source modes, builds local C++/Go foundations from wheel-owned
sources, emits package modes, then compiles and runs all four native consumers.
It preceded Go's later generator-only fingerprint/Unicode corrections; canonical
runtime resource bytes stayed unchanged. Go's final focused receipts cover those
corrections; no later full wheel/global run is claimed here.

`verify_examples.py` also built, zipped and extracted an actual native C++ archive,
then compiled/ran Example, Conformance and AllocationFault in source/package/
supplied modes. All three normalized streams matched. The result was:

```text
source: draft issues=2; repaired=1; virtual valid=1 complete=0
package: draft issues=2; repaired=1; virtual valid=1 complete=0
supplied: draft issues=2; repaired=1; virtual valid=1 complete=0
```

Artifacts remained under `D:/projects/limbo/cpp-go-oneof-scratch/cpp-examples-gx6sfg7z`.
The retained report stream, package provenance and fresh-final-generator API-byte
association are in this directory's `results/` receipts. No Python, Taut compiler,
authoring loader or delivery/shape engine is imported by those native executables.

## Final shared correction and preservation

The shared driver now checks the previous ownership manifest and original raw
recorded root before taking any locks. A previous manifest alias/non-file or root/
ancestor reparse/symlink/non-directory obstruction fails with a named diagnostic.
This prevents a previous root's junction from being resolved into a new mutation
location before the planner gets to reject it.

The exact reproducer in `test_cpp_go_distribution.py` changes a recorded previous
source root to a real Windows junction, spies generation-lock opens, and requires
ZERO attempts plus unchanged bytes. It runs for Python, Rust, Java, Kotlin, JS,
TS, C++ and Go. The paired all-output preflight test also confirms that Go's
handwritten collision leaves C++ output untouched.

The final affected run passed **88 tests, one skipped in 6.91 seconds**. The skip
is the existing JS symlink case without Windows symlink privilege; real junction
tests passed. It covers accepted Python/Rust/JVM/ECMA ownership/transitions,
raw namespace ambiguity, overlap and the eight-target previous-root reproducer.
It requests no new native target compilation. The raw
[log](results/shared-affected.log), exact [command/receipt](results/shared-affected-receipt.json),
[before](results/shared-affected-before.json) and
[after](results/shared-affected-after.json) prove unchanged protected authoring/
facts/tests, all 35 excluded old Python artifacts, indices, locks and shared/C++
source. Counts overlap other gates and must not be added. Earlier two- and four-case
state receipts are intermediate subsets of this affected evidence. Its snapshots
precede only the later C++ naming correction; the shared driver bytes are final.

The final exact C++/shared owned manifest and combined Preparation reconcile Go's
separate 22-file manifest. User-owned Python Enum.case work, old Python bundles/
wheel, all unrelated member repositories and locks are excluded. The root owns
the single future settled broad/full-16-parity gate and any checkpoint/review.
No final global success, full nine-language completion or stable arbitrary stale
C++ object-file ABI is claimed; independently built C++ units must use the same
actual public headers/ODR definitions and chosen foundation.
