# Java/Kotlin OneOf checkpoint — final verdict

Status: **accepted at the exact corrected tuple below after both original
Code+Surface and State reviewers reported GO**. This accepts the Java/Kotlin
pair only, after one merged remediation round. No push, tag, release, registry
publication/installation or next-backend continuation is authorized here.

| Repository | Accepted review revision |
| --- | --- |
| Taut implementation | `8682555a66e61659c465092b461d3b2cb4c58ff4` |
| GWZ workspace receipt | `183359cdefae3921d65c208eec85ca048da58db8` |
| Python shape reference | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| Rust shape reference | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |

The full implementation range is1607b6e0..8682555a; remediation range is
92c6894d..8682555a. The authoritative corrected109-file inventory is
[Inventory-1](JvmOneOfCheckpoint-Inventory-1.json) at the accepted source commit.
Subsequent local review-evidence commits may record these verdicts but must
preserve implementation/test/example/golden bytes from that reviewed source.

Verbatim final reports:

- [Code+Surface GO](JvmOneOfCheckpoint-ReviewCode-1.md).
- [State GO](JvmOneOfCheckpoint-ReviewState-1.md).

Both reviewers independently verified all four HEADs at start/end, all108
non-self hashes/sizes against committed objects and immutable snapshots,
the full109-file scope and exact11-changed/32-added remediation range.
They classify the correction as localized restoration of intended equivalence/
literal spelling/help, with unchanged APIs, runtime owner/contracts, engine
semantics, mutation boundaries and platform assumptions. No replacement
reviewers, third axis, new architectural root or second remediation was needed.

## Findings and originating closure

| Finding | Root / correction | Final originating disposition |
| --- | --- | --- |
| Code P2-1 | R1: Java fields/Case arrays were hashed in authoring order. Normalize portable per-message arrays without mutating exports. | CLOSED by Code's original separately compiled child/parent probe and positive/negative matrix. |
| State P2-1 | Same R1, independently discovered. | CLOSED by State's original two-field engine-free composition probe and positive/negative matrix. |
| Code P2-2 | R2: inherited unsuffixed Java enum arguments prevented accepted signed-i64 OneOf inputs compiling. Emit long suffixes, preserving values/wire facts. | CLOSED by original extrema reproduction and source/package × validation-mode i64 execution matrix. |
| Code P3-1 | Existing shared/helper help omitted JVM support, JSON-file/default details. Help-only corrections, with Kotlin ownership respected. | CLOSED by originating cold-help reads, actual help assertions and first-day walkthrough. |

The two axes converged blindly on R1 before receiving each other's findings.
It was corrected once in the merged patch. All blockers and the nonblocking
help issue are reviewer-closed; no open findings remain. See the immutable
[initial Code](JvmOneOfCheckpoint-ReviewCode.md),
[initial State](JvmOneOfCheckpoint-ReviewState.md) and
[merged remediation plan](JvmOneOfCheckpoint-RemPlan-1.md) for the audit trail.

## Verification and evidence limits

The sole global gate ran on ORIGINAL Taut92c6894d/root07b5853c, with unchanged
source/tuple: all16 codec variants GREEN; broad1620 passed,3 established
baseline failures,4 skipped,8 deselected; new_failures empty. Its verbatim
receipts are under examples/jvm-oneof/global-r0. The failures are only the
historical missing document and two Windows Go CRLF/gofmt cases; preserved
baseline-source proof establishes their provenance. That global matrix was not
rerun or relabeled as corrected-source evidence.

Corrected-source implementation evidence:17 new closure cases pass; affected
Java/codec/CLI/scaffold/wheel command141 pass plus one obsolete literal-shape
assertion updated and passing its isolated rerun;865 preservation cases pass.
This is142 distinct passing target cases across141+1 runs, not one clean142
run. The failed-first log is preserved. Both reviewers judged those focused
gates and unchanged boundaries sufficient for the localized patch, as root
directed; no automatic duplicate global run occurred.

On corrected source, Code independently re-ran original probes, the17-case
matrix,15 wheel/scaffold/CLI/literal tests, all12 language×runtime-mode×validation
walkthrough combinations and historical physical-root probes. State independently
re-ran its original probe, the17-case matrix,66 state checks and namespace/
junction/overlap/shared-user/lock probes. Overlapping counts are not added.
Source/package examples and engine-free typed descriptor/adaptor probes pass.

## Scope retained

The accepted pair provides mandatory immutable shared metadata, opt-in thin
instance validation, canonical foundation source/local-package/supplied routes,
actual independent-child nominal identity, semantic parity and protected
output ownership. Java keeps package-private messages and same-package external
projection. Neither existing standalone target has a native JSON route; none
was invented. No Java/Kotlin shape-library repo is claimed. Virtual selection
remains intentionally deferred/incomplete. Java8 means --release8 compilation
with execution tested on JDK17, not a separately tested Java8 VM.

User Enum.case authoring work remains parallel and excluded; its monitored
source hashes were preserved. This acceptance does not make the old Python
metadata reservation policy permanent. Later user integration/testing is
coordinator-owned. Only scoped local checkpoint/review-evidence/managed receipt
commits are authorized; production remains identical after evidence landing.
