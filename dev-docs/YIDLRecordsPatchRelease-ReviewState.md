# YIDLRecordsPatchRelease — STATE-AXIS REVIEW

**Review object:** Paired patch-release sources: YIDL dataclass `48ba94efd26ff300345f3bdca38987b90a13f79b`; Taut `f81a206d64b58d705d9cc853e5bea69550fb9e98`. Controlling documents: Taut `dev-docs/YIDLRecordsPatchRelease-DRAFT.md`; YIDL `dev-docs/ConfigurableFreezeRelease.md` and `dev-docs/CurrentProgramCheckpoint.md`.

**Baseline:** Published YIDL v0.1.1 `a71917a2a146433e7ceb9309865e99759fcf1d3b`; published Taut v0.11.1 `0258b49e92c8b4ccd95027b4b10ad0b2f3992c52`. Prototype baselines: YIDL `6c39c45ec31aca46665c29eaf69d2033cb4fe594`; Taut `fcfbe0cfface9241c2b68542973936a166a0c8bc`. Sources were read using immutable `git show <SHA>:<path>` and corresponding baseline diffs.

**Date:** 2026-11-03

**Axis:** State transitions, partial failure, ownership, recovery and publication ordering. Independent, adversarial, read-only. Nothing here relies on the parallel reviewer. Filed verbatim by the lane owner.

**Verdict: GO** — zero findings. These exact sources are fit to enter the mandatory remaining qualification and dependency-first publication gates. This does not certify completed releases or accept a later candidate’s metadata without verification.

---

## 0. Evidence base

Both named source commits resolved correctly with `rev-parse <SHA>^{commit}` at the start and end of review.

Read both repositories’ `AGENTS.md` and `RELEASE.md`, the controlling documents, and the review-loop instructions. Inspected the full published-baseline ranges, distinguishing:

- YIDL’s previously public-main documentation/site work: the published-to-prototype range changes no `src` files.
- Taut’s previously public-main addition of Python 3.15 CI.
- The new configurable-freeze implementation, generated base and golden updates, optional Taut backend, tests, packaging and release configuration.

State-critical inspection included YIDL’s decorator/options, policy and inheritance planning, inferred child hooks, authored `dataclass_core.yidl`, `dataclass_freeze.yidl` and copy resources, generated base, configurable-name tests and freezing documentation. The authored freeze transition is at `dataclass_freeze.yidl:39–48`; selected-name binding is at lines 136–139.

Taut inspection included `records.py:1–140`, generation and scaffold changes, runtime source closure, capabilities, binding recognition, validation traversal, CLI, optional dependency, workflows, Gearu configuration and all new backend tests.

Read `PROTOTYPE_RESULTS.json`, installed-probe results and release plans/current YIDL candidate log. Prototype results—YIDL 302 passed/2 version skips, Taut 1069 passed/0 skips and six installed cases—are preliminary evidence for their recorded prototype commits. The observed YIDL candidate log was incomplete; neither it nor the earlier Taut plan establishes exact-source release completion.

No tests, builds, installations, writes, Git mutations or credential access were performed.

## Problem, requirement provenance, and scope

The authorized outcome is dependency-first patch releases supporting configurable YIDL freezing names and Taut’s Python-only optional YIDL record backend. The human explicitly selected a Taut-owned configured decorator and `--python-records yidl`, then authorized a point release.

The concrete integration problem is a legal Taut field named `freeze` colliding with YIDL’s default generated method. Configuring the name through YIDL’s authored generation model, then centralizing `_taut_freeze` in Taut’s decorator, addresses that problem without an imperative post-generation rename. Existing stdlib generation remains the supported default and a viable alternative.

The prototype supplies concrete feasibility evidence for the selected route. No SDK modification, rebuilt dependency, performance claim or foundation/shape release is necessary. Changes remain within the two authorized Python projects and their tests, documentation and release setup. Astichi 1.1.3 and YIDL 0.1.2 remain published reference dependencies. No unsupported prerequisite or unauthorized expansion was identified.

## 2. Invariant analysis

**Naming and generation.** Exact-string identifier checks reject keywords, internal names and double-underscore names. Collision checks cover fields and non-generated bases. Freezable model inheritance requires a consistent selected name, while independently typed children dispatch through their own configured names. Explicit hooks retain precedence. Authored resources and generated metadata carry the name directly; the default remains `freeze`.

**Completion and recovery.** Freezing marks completion only after field processing succeeds and clears the in-progress flag in `finally`. Reentry terminates cyclic traversal. Exceptions leave the parent incomplete and retryable, while earlier transformations or frozen children can remain. That optimistic partial-failure behavior is disclosed; atomicity and concurrent freezing are not promised.

**Ownership and containers.** Taut preserves child record identity, recursively projects nullable/container shapes, detaches mutable list/map aliases and accepts its transformed containers on retry. Regular `FrozenDict` mutation paths are blocked; shallow copy shares the immutable mapping, and deep copy memoizes before traversal. Copy/pickle construction does not use blocked mutation operations. Deliberate base-class mutation bypasses are disclosed rather than presented as a security boundary.

**Validation and nominal boundaries.** Frozen container acceptance is conditional on the owning record’s completed frozen state. Exact message/enum binding identity and ownership-cycle checks remain. Freezing does not claim validation. Mixed stdlib children fail deep freezing explicitly rather than silently claiming success.

**Defaults and delivery.** Backend selection is checked before generation writes. Default stdlib emission remains unchanged; non-Python targets are unaffected. The stdlib path does not import the optional SDK. Runtime capability negotiation rejects unsupported runtimes before optional record construction, and source delivery includes the new runtime module.

**Release ordering.** The optional dependency requires public `yidl-dataclass>=0.1.2,<0.2`; no compiler auto-install or prototype wheel substitutes for publication. Existing older-Python stdlib coverage remains, while the strict qualified Taut gate includes the optional dependency and must exercise the new backend without skips.

## 3. Risks and next action

Source inspection cannot establish the remaining supported-host matrices, installed artifacts or public registry behavior. Prototype results must not be relabelled as exact-candidate acceptance.

Proceed through the configured gates: complete YIDL qualification, verify its exact version-only candidate/tag delta, publish and verify public 0.1.2, then qualify Taut against that public dependency before its own candidate verification and publication. Hosted results, artifact provenance, fresh nested public consumers and final preservation receipts remain required. Failures at those gates remain release blockers.
