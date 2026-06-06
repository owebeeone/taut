# Prism Orchestration — execution spec (P4)

Status: working draft. Normative (`MUST`/`SHOULD`/`MAY`).
Reference impl: `trial/py/griplab_slice/scheduler.py` (sdax-style, asyncio).

Per-endpoint control flow is a **declarative task DAG**: a set of tasks, each with
dependencies and a per-task **error policy**. The scheduler derives parallel
waves and executes them with the semantics below. The policy + structure are the
portable declarative part; the task body (`run`) and `teardown` are code bound per
language. Sagas / compensation are explicitly deferred.

## Model

- **Task** = `key`, `deps` (keys), `run` (the work), `policy`.
- **ErrorPolicy** (v1 vocabulary — resolves PrismPlan §10.3):
  - `retries: int` — extra attempts on failure/timeout (total attempts = retries+1).
  - `timeout: float | None` — per-attempt deadline in seconds.
  - `on_error: "isolate" | "fail" | "fallback"`.
  - `fallback` — value used when `on_error="fallback"` and attempts are exhausted.
  - `teardown` — cleanup hook, run for every started task.

## Execution semantics

1. **Waves.** The scheduler `MUST` derive waves as topological levels: a task is
   in the earliest wave after all its deps. Tasks within a wave `MUST` run
   concurrently. A cycle or missing dep `MUST` be an error before execution.
2. **Dependencies.** A task's `run` `MUST` receive the `TaskOutcome`s of its deps.
3. **Retry.** On failure or timeout the scheduler `MUST` re-run up to `retries`
   additional times before applying `on_error`. Each attempt `MUST` get a fresh
   `run` invocation.
4. **Timeout.** If `timeout` is set, an attempt exceeding it `MUST` be cancelled
   and treated as a failed attempt.
5. **on_error:**
   - `isolate` — the failed task is recorded as a failed outcome; siblings and
     downstream waves `MUST` continue. (Default.)
   - `fail` — the scheduler `MUST` cancel in-flight siblings in the same wave and
     `MUST` mark all not-yet-started downstream tasks `cancelled` (structured
     cancellation); the graph is aborted.
   - `fallback` — on exhaustion the task `MUST` succeed with `fallback`.
6. **Teardown.** After the DAG settles (success, isolate, or abort), `teardown`
   `MUST` run for every task that started, in **reverse start order**. A teardown
   error `MUST NOT` mask the task outcomes.
7. **Outcomes.** `run_dag` `MUST` return a `TaskOutcome` for every declared task,
   including `cancelled` ones.

## Reference use

`cmd.run` fans out one task per repo (single wave, no deps) under
`ErrorPolicy(timeout=30.0, on_error="isolate")`, then a gather task assembles the
session — so one repo's failure is isolated by *policy*, not hand-coded control
flow. See `trial/py/griplab_slice/service.py`.

## Deferred

- Cross-language portable serialization of the task graph (today the structure +
  policy are declarative data in Python; a Rust tokio binding to the same spec is
  the P5 orchestration step).
- Sagas / compensation; dynamic re-planning; priority/fairness within a wave.
