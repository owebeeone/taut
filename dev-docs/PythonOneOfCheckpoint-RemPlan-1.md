# Python checkpoint remediation 1

Review object: source digest `af9f2516f0dcbf45853fb6ade39d207c7a84b6b282975bffa8fdd385b59cc996`.
Both read-only reviews are filed verbatim as ReviewCode and ReviewState. Their IDs
are prefixed C/S below to disambiguate the independently assigned numbering.
All six findings are accepted. One merged patch is authorized within the original
Python batch; no backend implementation, commit or release is added.

Additional operator decision, 2 November 2026: **"Double underscores are out."**
The coordinator explicitly scopes this to leading double underscores in Python
schema field names. C/P2-1 therefore rejects that prefix early in source, package
and supplied-runtime modes, with validation off/on. Ordinary internal substrings
such as `part__name` and other targets are not newly prohibited.

| Finding | One disposition | Closure test |
| --- | --- | --- |
| C/P2-1 private-name mangling | Reject unsupported double-underscore private field names in Python generation preflight, in both validation modes. | `__private` through source/package with validation off/on must fail by named path before output mutation. |
| C/P2-2 enum authoring namespace | Declare and check the existing EnumDef metadata namespace (`name`, `members`, `options`) as reserved in the production DSL, with an early migration diagnostic. This uses the review's permitted reservation-policy remedy and adds no alternate authoring API. | Every reserved name fails at Enum declaration with its name/reason; ordinary dot members and wrong ownership remain tested. |
| C/P2-3 false compatibility breaks | Compare normalized constraint-bearing facts by stable field name, independent of ordinary fields, declaration order and Case ordering. | Unrelated MISSING_OK addition/reordering remains compatible; case/controller/policy/removal changes remain breaking. |
| S/P2-1 unrecorded consumer-first use | Reject an explicitly named source-owner consumer if the owner is not materialized. Package default without a source-root override still does not inspect installed packages. Register every accepted explicit consumer. | Package/supplied consumer-first attempts leave output unchanged; owner-first composition followed by producer disabling/detachment preserves the registered consumer's engine and imports. |
| S/P2-2 obstructed write ancestors | Preflight the kind and suitability of every output target and ancestor before applying any writes, including linked/reparse directory components. Unknown directory aliases must not redirect emission outside the intended owner. | Handwritten file at default/external runtime package directory yields named unchanged-snapshot failure; an empty directory junction/symlink at a required component is rejected before emission. |
| S/P2-3 ignored known-rule parameters | Require exact supported oneof constraint parameters and a one-to-one match to normalized groups; reject missing/duplicate/dangling/unsupported configurations at SchemaBinding construction. | Original synthetic malformed declaration and additional parameter/group mismatches fail as ConfigurationError; valid publication and shared report/Boolean paths still pass. |

The changes repair the already-required boundaries; they do not introduce a new
runtime owner, interface family, persistence format or compatibility policy.
The reservation remedy makes the previously required name policy explicit, and
the source-consumer remedy makes unavailable configuration fail before writes.
Continue the same two reviewers for focused re-verdicts on their original
counterexamples; they retain the authority to identify a material architectural
change requiring fresh review. This is remediation round 1 of at most 2.

After patching: run new closure tests and focused feature/core/shape gates,
regenerate examples and shape facts, rebuild/verify the local wheel, refresh the
source inventory, and re-review. Full-suite green remains unclaimed; unchanged
baseline evidence and count-overlap disclosures remain controlling.
