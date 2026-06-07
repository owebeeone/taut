# taut

Cross-language data + service protocol mechanism under the Glade declarative surface. See [dev-docs/TautPlan.md](dev-docs/TautPlan.md).

- `src/` — the builder (Python): IR model, validator, generators, corpus.
- `ir/` — authored IR modules (the only governed artifact).
- `corpus/` — generated golden vectors (the oracle).
- `trial/{py,ts,rs,cpp}` — generated + hand-wired target slices.
