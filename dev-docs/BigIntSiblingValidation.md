# Bigint sibling-package validation

The compiler's nine-language parity gate is supplemented by the package suites
and live interoperability checks below. These results validate the development
sources, not a tagged or published release candidate. Validation used Linux
x86_64 on WSL/Ubuntu 26.04; compiler/toolchain versions are recorded in
[TautBigInt.md](TautBigInt.md). No native Windows, macOS or ARM run is claimed.

## Package results

| Package or check | Result |
| --- | --- |
| Python shape library | 197 tests passed, no skips |
| TypeScript shape library | 316 tests passed, no skips; type checking and build passed |
| Rust shape workspace | 109 tests passed with all features; Clippy with warnings denied passed |
| Rust default workspace | 109 tests passed; no-default-features library build passed |
| Shared live matrix | All 315 node/client/scenario cells passed across Rust, TypeScript and Python |
| Process-harness regressions | Three tests passed |
| Python distributions | Compiler and shape wheels built; isolated installed-wheel bigint smoke test passed |
| TypeScript distribution | Packed package installed into an isolated consumer; bigint round trip and CJS/ESM constructor identity passed |
| Rust foundation crate | All-features build/test command passed; standalone package verification passed |

The Rust workspace ran from a disposable source copy with a temporary Cargo
patch selecting the changed canonical foundation. This avoids accidentally
testing the older registry foundation, and leaves package dependency versions
and repository lockfiles unchanged. The Python suite used the changed compiler
source. The TypeScript suite used its refreshed, hash-recorded foundation.
The installed Python wheel pair was selected explicitly without registry
dependency resolution; this is a development artifact smoke test, not proof
of future release coordinates or registry availability.

A new Rust error variant initially broke an exhaustive error formatter in the
shape package's parity test. The formatter now handles that variant explicitly.
Each shape package also has a regression proving bigint wire identity, values
beyond 8,000 bits and rejection of a redundant leading zero through its public
foundation entry point.

The first parallel live-matrix run reported one malformed transcript in the
Rust-client/TypeScript-node sequential text-CRDT case. That isolated case passed
on rerun, and the full matrix passed sequentially after concurrent builds ended.
The original failure is retained as an observation; its precise cause was not
established. Treat it as a concurrency investigation item if it recurs.

An additional workspace-wide formatting check reports an existing long
attribute in the Rust CRDT text implementation. The modified Rust parity test
is formatted; unrelated production formatting was left unchanged.

## Initial release metadata drift and 0.12 preparation

The initial validation found four mismatches in the previously unchanged
release metadata:

- Rust package version is `0.11.0`; the manifest expects `0.10.0`.
- TypeScript package version is `0.11.0`; the manifest expects `0.10.0`.
- Python requires `taut-proto>=0.11.0,<0.12`; the manifest expects the older
  `>=0.10.0,<0.11` range.
- The Glial development consumer uses a sibling file dependency; the manifest
  expects its earlier registry pin.

Those mismatches initially caused three release-metadata tests to fail. The
subsequent authorized 0.12 preparation updates the manifest, package declarations,
Python/Rust dependency ranges and Glial's registry pin. Normal compatibility now
passes for all eight contracts. Ten checker regression tests pass, including new
foundation version/dependency drift checks and rejection of candidate release
status. Python (197), TypeScript (316) and Rust (109) suites pass with the new
version declarations; Rust selects the unpublished 0.12 foundation through a
local patch in a disposable checkout.

The manifest is deliberately marked `candidate`, not `released`. Registry
resolution cannot complete until the new foundation and npm shape versions are
published. Existing registry locks remain prior-release records pending that
step; local patched locks are not substituted into release sources. See the
[release preparation notes](../../taut-shape/release/README.md).

Release preparation still needs an agreed new minor-train manifest, matching
package versions and dependency bounds, refreshed immutable release inputs,
clean tagged candidates and the strict release gates. This validation does not
replace the compiler's required native-Windows/POSIX release partition, and its
prior conditional skips are not a zero-skip release receipt. No tag, push or
registry publication was performed.
