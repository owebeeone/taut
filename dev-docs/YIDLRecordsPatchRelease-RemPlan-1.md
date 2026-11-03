# YIDL record release — bounded naming correction

The Code+Surface report at Tautf81a206 returned NO-GO for P2-1; State returned
GO with no findings on the same source. No YIDL source blocker was identified.
Both reports are filed verbatim. This is remediation round1, confined to a
backend preflight omission, not an architectural change.

P2-1 disposition: fixed by rejecting the selected YIDL backend's unsupported
stored names before any output writes. The human explicitly selected this
approach: leave the names unchanged and make them illegal only with YIDL,
rather than project safe Python attributes. The stdlib backend stays unchanged.
Existing general checks already reject dunder names and escape Python keywords;
the added check covers self, cls and the _y_dc_ prefix.

Closure:12 parametrized regressions cover all3 counterexamples x validation
OFF/ON x programmatic/CLI paths, each with absent output and an existing
handwritten output file. Each rejects before creation/modification. The same
schemas import and construct with stdlib records. The legal freeze field is
now tested with validation OFF/ON. All30 focused backend cases pass in
taut-name-fix-tests.log. An initial test-edit syntax error was corrected before
that passing run; it is not counted as a pass.

Next: same Code originator verifies P2-1's original counterexamples and records
the bounded closure; no new broad implementation review. State's unchanged
runtime/ownership proof remains applicable; its only added behavior is earlier
fail-closed rejection. User quota steering explicitly requests no unnecessary
additional testing or review rounds. All configured release gates still run.
