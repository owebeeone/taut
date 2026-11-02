# C++ descriptors and explicit validation

Run from the saved Limbo project after activating its existing toolchains:

```powershell
. D:\projects\limbo\toolchain-readiness-2026-11-02\Activate-TautToolchains.ps1
python D:\projects\limbo\taut-dev\taut\dev-docs\examples\cpp-oneof\verify_examples.py
```

The script builds a local foundation archive, packages/extracts it, then compiles
and runs source, package and supplied-runtime applications with RTTI disabled.
It checks identical normalized reports and runs real allocation-fault injection.
Artifacts stay under `Limbo/cpp-go-oneof-scratch`. It installs and publishes nothing.
[Example.cpp](Example.cpp) shows an invalid mutable draft, dense CBOR round-trip,
repair, an owned earlier report, and intentionally incomplete virtual validation.

The baseline remains C++20. Scalars, enums, `std::optional`, vectors and maps keep
their native projection. Text/bytes retain the existing borrowed `std::string_view`
codec lifetime: keep encoded input storage alive while decoded views are used.
Acyclic message fields remain values. Direct recursive ownership cycles use
`std::shared_ptr` for references to the cyclic message types; recursive container
value types retain the existing representation. There is no common message base,
RTTI, reflective factory, live-field heap wrapper, or implicit semantic validation.

Every message publishes `static const taut::MessageDescriptor& descriptor() noexcept`
and `taut_binding()`, including disabled output. Metadata queries are allocation-free
read-only ranges over compiler-owned static tables. Immediate (`consteval`)
publication reads all backing facts, rejecting mutable/temporary backing storage
at native compile time. Fields include logical virtual fields, types, presence,
options, reservations, `next_id`, normalized groups and constraints. The schema
registry is available through the binding. Enum traits publish complete inventories.
Primitive reads borrow native values; enum access uses the native enum owner.
Message links are lazy accessors and terminate publication on recursive schemas.
An empty payload name in a group mapping represents a payload-free enum choice.

`--with-validation` independently adds these methods on every message:

```cpp
taut::validation::ValidationReport validate(bool recursive = true) const noexcept;
bool is_valid(bool recursive = true) const noexcept;
```

One shared engine uses the same predicates for reports and Boolean checks. Reports
own their strings, paths and diagnostic collections; getters borrow the report.
`is_valid()` requires both validity and completeness. Virtual groups contribute
deferred checks while supported children continue. Recursive mode traverses every
populated owned child, including nonselected payloads, lists and maps. Map paths
sort canonical Taut CBOR key bytes as unsigned bytes, with padded base64. Shared
children are checked at each path; active ancestor cycles produce located issues.

Only allocation failure is translated at the public C++ boundary. Boolean mode
returns false without building a report. Report mode returns one root
`validation.resource_exhausted` issue and one root deferred entry. The fallback
uses static text and empty root paths; construction, copying/moving and range
getters allocate nothing, without relying on small-string optimization.
`AllocationFault.cpp` verifies this while every allocation fails, then injects
failure at successive report allocations. Configuration errors are checked before
validation is usable and produce named regeneration/rebinding diagnostics.

## Runtime and independent dependencies

Canonical sources are `src/taut/gen/runtime/{cbor,ext,foundation,descriptors,reports,
validation}.hpp` plus `foundation.cpp`. `cpp_runtime.build_foundation(destination)`
builds a local include/link package from those exact files. Source mode emits the
same closure. Validation-off closure omits `validation.hpp`; basic applications
need no Taut compiler, authoring loader, shape engine or transport. C++ has no
existing language-library repository here; no package registry name is invented.

All schemas use namespace `taut`, include `taut/*.hpp`, and link exactly one
foundation definition. Source mode shares one include root; package mode supplies
that same surface as `include/` plus `taut-foundation.lib`. The archive uses the
selected platform's native object format. MSVC and Clang execution are tested.
The generated guard reads the selected compiled owner's actual contract export,
including its defined ABI guard, rather than trusting a stale checker or binding
label. Compatible unequal build labels are allowed. Duplicating source owner
definitions fails native linking.

Example bindings:

```json
{"cpp":{"source_root":"D:/projects/limbo/my-app/foundation"}}
```

```json
{"cpp":{"artifact":"D:/projects/limbo/my-app/local-foundation"}}
```

`source_root` is the selected physical source owner and uses shared-user accounting.
An explicit `artifact` verifies local package provenance before writes. The
application explicitly supplies the chosen include/link flags. Omission retains
the supplied-runtime route; `--with-runtime` aliases `--runtime source` and does
not enable validation. No discovery, installation, fallback or dependency
regeneration occurs. Raw Windows namespace spellings are checked before `Path`
conversion; ownership checks reject aliases, obstructions, modifications and
unavailable previous owners before mutation. Interrupted writes leave either the
old usable generation or a fail-closed state requiring inspection/fresh output.

Independent child mappings are passed through `cpp_external_types` or
`--cpp-external-types JSON_FILE`. For each dependency message/enum:

```json
{"Content":{"header":"child.hpp","type":"taut::Content",
  "owner":"taut.cpp.foundation","descriptor_contract":1,"codec_contract":1,
  "capabilities":["codec.v1","descriptors.v1","oneof.v1"]}}
```

The full dependency schema and all referenced type mappings are required. The
current native namespace is `taut`; mappings select its actual public header and
type. Parent traversal uses the child's descriptor/adapters even if child methods
are disabled. It never adds methods or regenerates children. Native compile guards
reject old children; actual descriptor fingerprints reject incompatible enum,
effective codec or ownership facts while normalizing field/Case/enum-map order.

Internal generator provenance is `cpp-oneof-reference.1`, descriptor/codec contract
1, constrained IR 3, unconstrained IR 2, readers 1–3. No release version changes.
There is no existing C++ JSON codec route to extend, so no new JSON parser is added.
Dense CBOR, borrowed decode views, existing fixed `Buf` capacity, structural errors,
nullable/missing-ok handling and forward-compatible residuals retain their codec
contracts. A cyclic in-memory ownership graph must be repaired before serialization.
