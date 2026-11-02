# C++/Go OneOf checkpoint — controlling DRAFT

Status: **both implementations frozen by root; one scoped local checkpoint and
combined two-axis review authorized; acceptance pending**.
[Authority](CppGoOneOfCheckpoint-Authority.md) records the operator directive.
Preparation will record exact current bytes, exclusions and pending checkpoint
tuple. This DRAFT supplies no additional product requirements or git authority.

## Problem, necessity and scope

The accepted Python/Rust/JVM/ECMAScript implementations already provide native
OneOf/Case facts, rule/IR legality checks and common output helpers. C++ and Go
lacked complete mandatory metadata, optional instance validation, shared reports,
typed traversal and explicit source/package foundation delivery. Their old raw
runtime copying also lacked the required owner/user transition lifecycle.

The remedy extends existing `emit`/`emit_all`, CLI and native codecs. It retains
IR 3/2 output policy and readers 1–3. Source and package derive from each target's
single canonical runtime. No second compiler, dynamic factory, automatic semantic
validation, arbitrary-object reflection or new language-library repository is used.
Foundation consumers need native build tools and standard libraries, without a
Taut compiler, authoring loader, shape/delivery engine or unrelated transport.

## C++ projection and actual owner

C++ keeps C++20, namespace `taut`, native enums/value structs, borrowed
`std::string_view` text/bytes, optional payloads, vectors/maps, structural errors,
dense CBOR, missing-ok/null behavior and residual state. Acyclic messages retain
value ownership. Direct ownership cycles use shared pointers for references to
cyclic message types; recursive container value types retain their existing
projection. Cyclic codecs are defined after struct declarations so mutual
recursive types compile normally. Borrowed decoded views keep their existing
input-storage lifetime. No JSON codec/parser route is invented.

Every message has `static const MessageDescriptor& descriptor() noexcept` and
`taut_binding()`. Enabled output adds the proposal's exact `validate(bool = true)
const noexcept` and `is_valid(bool = true) const noexcept`. Both are thin shared
engine calls. Complete const-owned static metadata tables contain logical virtual
fields, primitive/container/message/enum types, options, presence, reservations,
next-id, normalized groups/constraints and immutable schema registries. Immediate
publication constructors read every backing fact and reject mutable/temporary
storage at compile time. Descriptor queries do not allocate.

Typed `ValueRef::borrow<T>` selects one static operations table from the actual
native type. Its constructor is private; generated captureless field readers
receive the current value. Primitive reads borrow native storage, enum traits
identify actual enum owners, and child/list/map access stays paired with the
correct descriptor/binding. There is no RTTI, captured live instance, generic
factory, `std::function` or live-field heap wrapper. Lazy accessor links terminate
recursive publication; publication checks category/version/rule grammar before use.

The foundation owner is `taut.cpp.foundation`, descriptor/codec/adapter contract 1,
capabilities codec.v1/descriptors.v1/oneof.v1 and a defined ABI guard. Generated
guards read the selected compiled `foundation_contract()` export directly, so an
actual old checker that ignores requirements cannot claim success. Incompatibility
prints a named regeneration/rebinding diagnostic. Unequal compatible build labels
are accepted. Source mode shares one include root and foundation definition;
package mode supplies that same include/link surface. Duplicate source owner
definitions fail native linking. No C++ library repository is fabricated.

Canonical closure: `cbor.hpp`, `ext.hpp`, `foundation.hpp`, `descriptors.hpp`,
`reports.hpp`, optional `validation.hpp` under `taut/`, plus `foundation.cpp`.
`cpp_runtime.build_foundation` compiles a local native archive from those exact
sources and records payload/source hashes. Extracted package consumers link the
actual archive. Validation-off omits the engine header. Generated provenance is
`cpp-oneof-reference.1`; no release version changes. External mappings name the
actual `taut::Type` and header plus owner/contracts/capabilities; the full dependency
graph is required. Independently compiled disabled children keep their native
identity and expose mandatory adapters without child validation methods. Actual
fingerprints include effective codec and forward-compat facts while normalizing
irrelevant field/Case/enum-map ordering.

Reports live in `taut::validation`, own diagnostic strings/paths/collections and
expose read-only ranges. The report sink and Boolean sink use the same predicates;
Boolean mode constructs no diagnostics or report containers. Allocation failure
returns false, or a bounded report containing one root
`validation.resource_exhausted` issue and one root deferred entry. Static fallback
text and empty paths do not depend on SSO. Native injection covers first fallback
construction, move/copy and every getter under fail-all allocation, then successive
report allocation failures. Only allocation failure crosses this report boundary;
configuration is checked separately before validation is usable.

## Go projection and actual owner

Go's executor owns the final target contract and evidence in
[the Go example documentation](examples/go-oneof/README.md) and its owned manifest.
The agreed shared interface is `go_api(..., *, validation, external_types, identity,
runtime_import)`, with target binding returning import path/source root/consumer
status and the common planner shape. `go_external_types` is forwarded through
emit/emit_all/CLI. Runtime import paths come explicitly from the application;
package mode does not invent a registry/module path. Source/package consume the
same canonical cbor/ext/descriptors/paths and optional reports/validation files.

The native projection retains structs, tags, enums, pointers and options. Go's
mandatory `DescribeName()`/nil-safe receiver `Descriptor()` share one immutable
descriptor pointer through sealed reader interfaces; exposed containers are
defensive copies. Enabled pointer receiver methods follow Validate/IsValid and
WithOptions, with no-argument recursive defaults and explicit zero-value options
selecting local scope. A nil root is a located type-mismatch result. Generated
typed readers/traversal pair metadata with actual native fields. Active ancestor
tracking includes native map/slice identities, covering ownership cycles caused
by Go map-value copies while preserving repeated shared children at separate paths.

The actual foundation owner is `taut.go.foundation`, contract 1 and the same named
capabilities. Explicit local module artifacts have complete owned provenance;
generation checks that inventory without executing Go. Actual compiled init guards
check defined ContractGuard and selected owner/contracts/capabilities. Explicit
package builders/tests compile and execute actual exports. Missing/stale/split
artifacts do not trigger installation, fallback or dependency regeneration. The
final Go handoff supplies exact correction/source association for forward-compat
fingerprints and supplementary Unicode literals. Its source manifest is
`examples/go-oneof/results/owned-source.json`, with 21 hashed files plus itself.

## Semantics and durable boundary

Both engines follow native normalized Python semantics: non-null presence includes
zero/false/empty; payload-free choices are allowed only when unmatched; wrong tags
skip only dependent group selection; ordinary/nonselected owned children continue;
local mode excludes descendants; virtual rules remain explicitly deferred; Boolean
equals report validity AND completeness. Group/field/child order uses field numbers,
lists ascend by index and map paths use unsigned-byte canonical Taut CBOR keys,
typed str/int/bool with standard padded base64. Shared children are checked per
path and only active ancestor cycles are rejected. Draft mutation and structural
codecs never invoke these semantic engines.

The shared driver plans all target output before mutation and uses existing locks,
physical identity, ownership hashes and source-user registries. Source/package and
validation transitions remove only positively identified unmodified stale files,
keeping components needed by other schemas. Unknown, handwritten, modified,
incompatible, unavailable-owner, obstruction, alias and physical-overlap states fail
closed. Raw namespace spelling is validated before Path coercion.

The final shared drafting correction closes an observed pre-lock mutation boundary:
before `output_locks`, `emit` rejects an aliased/non-file previous ownership
manifest, validates the original recorded root spelling, then checks that root and
all parents for reparse/symlink or non-directory obstruction before locking. The
reproducer rewrites a recorded previous root to a real Windows junction and spies
all generation-lock opens: rejection must attempt ZERO locks and preserve bytes.
The regression spans Python/Rust/Java/Kotlin/JS/TS/C++/Go. Focused existing accepted
physical/ownership/transition checks accompany it; those receipts are distinct from
the earlier 87-case native gate. Interrupted multi-file writes remain fail-closed
and may require inspection/fresh output; no unowned adoption/deletion is claimed.

## Evidence and limits

C++'s observed native run passed **87 tests** from existing test_cpp, new
test_cpp_oneof and the combined compiler-wheel distribution test. It used stable
CPython 3.13.5 and activated Clang 21/MSVC 19.33, compiled and executed with RTTI
disabled. This precedes the final shared guard and narrow C++ naming correction;
it is not relabeled as
a final broad gate. Subsequent focused state receipts cover the exact shared guard
and added regressions. Counts overlap and are not added. The earlier native run's
three new drafting regressions were fixed; the exact three affected tests passed,
and all existing native tests passed in the 87-case run. No baseline suppression.

The final shared affected gate passed **88 tests, one skipped** in 6.91s. The
single existing JS symlink-privilege case is skipped on this Windows account;
actual junction coverage, including all eight targets' previous-owner pre-lock
rejection, passed. Exact commands, raw log and before/after preservation hashes
are under `examples/cpp-oneof/results/shared-affected*`. Protected authoring/facts/
tests, all 35 excluded old Python artifacts, indices, locks and shared/C++ source
were unchanged. This is a focused state/transition gate, not another native/global
compilation gate, and its total overlaps other receipts.

A final narrow C++ preflight audit added missing own-method/helper-type collision
rejections. Its **21-case naming gate passed** with no skips/deselections, including
real disabled validation-named message builds. Native runtime/codec/engine bytes
remain unchanged since the 87-case run, and fresh final normal example API bytes
match all tested modes. The 88-case shared snapshot precedes this metadata-helper
preflight-only correction; its shared driver association remains exact.

The standalone C++ script passed source, extracted compiled package and supplied
modes, with identical normalized report streams and real allocation-fault fallback.
MSVC source/package conformance execution passed. Tests compare the actual Python
code/rule/path/deferred/scope/valid/complete projection, actual replaced compiled
exports, independently compiled disabled children, native naming, metadata-like
enum members through IR, long/boundary map keys, owned reports and immutable facts.
The combined wheel test built a real compiler wheel, checked all C++/Go canonical
resources, generated both targets in isolated `-I -S` wheel-only Python, built local
foundation artifacts from that wheel and compiled/ran source/package consumers.

Go's r0 target+legacy receipt is **104 passed, two exact original Windows CRLF/gofmt
failures**, with no skips/deselections and all then-new 80 feature cases passing.
It precedes the localized forward-compat fingerprint and supplementary Unicode
literal corrections, and is not relabeled as a final-source full run. The final
fingerprint gate passed **19 tests, 65 deselected**; the final Unicode/golden/format
gate passed **three, 82 deselected**. Those totals overlap. The final Go feature
file has 85 cases; no all-85 run is claimed here. Six current-generator native
source/package/supplied × off/on examples compiled/executed with Python/Go absent
from application PATH, and fresh final API bytes match the tested examples.
Neither this DRAFT nor earlier global ECMAScript receipts claims a current final
all-language/full-suite/all-16-parity success. Root owns that settled broad gate.

Deliberate limits: virtual selection remains incomplete; no invented native JSON
route; existing C++ fixed Buf capacity and borrowed decode lifetimes remain;
configuration errors are not successful/deferred validation. Runtime/source ABI,
package helper shape, static tables/sealed Go interfaces and internal build labels
are implementation choices. The required behavior, exact methods, owner identity,
safe lifecycle and fault boundary come from operator authority. Review must assess
these choices against that authority, not accept this DRAFT as authority itself.
