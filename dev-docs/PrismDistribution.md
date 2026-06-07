# Prism Distribution & Governance (P7)

Status: breaking-change gate DONE; OCI publish deferred.

The IR is the unit of governance. Because it is **declarative** (flat, versioned,
not Turing-complete), a structural diff between versions is well-defined — so we
can mechanically gate breaking changes, which is the hard part of distribution.

## Breaking-change gate (done)

[../src/prism/ir/compat.py](../src/prism/ir/compat.py) diffs a new IR against the
prior version and classifies each change. Under the same major, breaking changes
are rejected.

```
python3 -m prism.ir.compat <baseline.ir.json> <new.ir.json>   # exit 1 on breaking
```

Compatibility model (frozen wire = CBOR maps keyed by field tag):

| Compatible | Breaking |
| --- | --- |
| add message / enum / method | remove or rename(at tag) a field |
| add enum member | change a field's tag or wire-type |
| add an **optional** field | tighten optional→required; add a **required** field |
| add a stream event | remove/renumber an enum member |
| relax required→optional | remove message / enum / method |
| | change a method's kind / shape / param types / output / event types |

DoD met: rejects an incompatible change (e.g. `PeerPresence.name str→int` →
exit 1) and accepts a compatible one (e.g. add optional `ChatMessage.edited` →
exit 0). 9 tests in [../src/tests/test_compat.py](../src/tests/test_compat.py).

Mechanics this relies on: the neutral IR JSON round-trips losslessly
(`schema_from_json(schema_json(s)) == s`), so two published versions can be
compared field-for-field.

## OCI publish (deferred)

The remaining P7 piece: publish each IR version + its golden corpus as a
content-addressed **OCI artifact**; consumers pin by digest, fetch, and generate
locally. This also severs the cross-repo filesystem coupling (the deferred #1) —
`trial` would pin a prism IR digest instead of reading a sibling checkout. It
needs `oras`/a registry (network), so it is out of scope for the offline trials;
the gate above is the governance logic it would run in CI at publish time.
