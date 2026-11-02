# Java/Kotlin OneOf checkpoint — verdict ledger

Status: **NO-GO at the initial frozen tuple** Taut92c6894d /
workspace07b5853c / shape-Pythonc08c2a1b / shape-Rust8e92b89e.
Both original reports are filed verbatim beside this ledger. No acceptance
or originating closure is claimed. Remediation1 is in progress under
JvmOneOfCheckpoint-RemPlan-1.md; maximum2 remediation rounds remain controlling.

| Axis / finding | Root | Current disposition |
| --- | --- | --- |
| Code P2-1 | R1: raw Java field/Case declaration ordering in fingerprints | Accepted; blocking; one normalization correction shared with State finding. Pending originating closure. |
| State P2-1 | Same R1, independently reproduced | Accepted; blocking. Blind convergence recorded; pending originating State verification. |
| Code P2-2 | R2: Java enum constructor literals lack long suffix | Accepted; blocking required native OneOf inputs despite inherited baseline spelling. Pending originating Code verification. |
| Code P3-1 | CLI/helper help omissions/default descriptions | Accepted; nonblocking, included in merged correction. Kotlin owns its help-only contribution. Pending Code verification. |

The sole global gate on that initial tuple completed all16 codec variants
GREEN and broad1620 passed/3 established baseline failures/4 skipped/8
deselected. Its source and tuple remained unchanged and new_failures is empty.
Those results are recorded at their real revision; they do not close the two
reviewer counterexamples or claim to have run on remediation1.

Both reviewers independently checked the whole Java/Kotlin object, source/
package/typed/runtime/public surfaces and durable guards. Code executed144
feature tests and14 shared/wheel/CLI checks plus all12 first-day combinations.
State executed66 state/mode checks and19 runtime checks plus separate filesystem/
lock probes. Counts overlap and are not added. The historical-root probes passed
in both independent reviews; no new ownership or Kotlin runtime blocker was
reported.

Next action: complete the ONE scoped remediation patch and focused gates,
commit/refreeze its exact tuple locally through GWZ, then continue the same two
originating reviewers if the localized correction retains the reviewed
architecture/interface/mutation/compatibility contract. Reports must contain
prior-finding closure tables and original-counterexample verification. The
implementer cannot self-close any blocker. No third axis, unrelated backend,
user Enum.case edit, push, tag, release or publication is authorized.
