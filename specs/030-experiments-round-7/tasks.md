---
description: "Task list for experiments round 7 implementation"
---

# Tasks: Experiments Round 7

**Input**: Design documents from `/specs/030-experiments-round-7/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not applicable — this round's "tests" are the head-to-head evals and replay analysis specified by the acceptance scenarios themselves; no separate unit/contract tests are requested.

**Organization**: Like Round 6, this round's user stories are **sequentially dependent**: US1 selects the benchmark opponent (`<BENCHMARK>`) that US2 analyzes; US2 produces the 2-3 candidates that US3 implements, evaluates, and benchmark-checks. Each story is independently *checkpointable* — its output is a concrete artifact (a documented opponent choice, a replay-analysis report, an evaluated/combined agent) — but US2 cannot start until US1's checkpoint is reached, and US3 cannot start until US2's checkpoint is reached.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files/processes, no dependencies)
- **[Story]**: Which user story this task belongs to (US1=P1, US2=P2, US3=P3)
- `<BENCHMARK>` denotes the opponent selected in T007 (e.g., `opponent_agents/<slug>_agent.py`, or `agent_v58.py`/`agent_v60.py` if external opponents are saturated)
- `<N>` denotes the number of candidates (2 or 3) selected in T010

## Path Conventions

- **Existing baseline (read-only, fork point)**: `agent_v64.py`
- **Sparring agents (read-only)**: `agent_v58.py`, `agent_v60.py`
- **Opponent pool**: `opponent_agents/*.py` (7 downloaded opponents incl. `slawekbiel_agent.py`)
- **New agent**: `agent_v68.py` (next available version number after `agent_v67.py`)
- **Replay captures**: `replays/replay_<benchmark-slug>_*.json` (written by `record_replays.py`)
- **Experiment logs**: `experiments/2026-06-1X-round7-opponent-matrix.md`, `experiments/YYYY-MM-DD-replay-analysis.md`, `experiments/YYYY-MM-DD-experiments-round7.md`
- **Config**: `README.md` (Agents table), `Makefile` (`AGENT`/`RENDER_AGENT`)

---

## Phase 1: Setup

**Purpose**: Confirm prerequisites, make the one-time `slawekbiel`/`torch` unlock attempt, and reserve the experiment log before any evals run

- [X] T001 Verify `agent_v64.py`, `agent_v58.py`, and `agent_v60.py` exist and import cleanly (`uv run python -c "import importlib; [importlib.import_module(m) for m in ['agent_v64','agent_v58','agent_v60']]"`); confirm `agent_v68.py` does not yet exist; list `opponent_agents/*.py` as the candidate pool for T004
- [X] T002 [P] Make the one-time `slawekbiel`/`torch` unlock attempt per research.md R1 (`uv pip install torch`); record success/failure (expected: failure on Python 3.14, no wheel) — this result feeds the "loadable" column of T003's table
- [X] T003 [P] Create `experiments/2026-06-1X-round7-opponent-matrix.md` with the `OpponentWinRateEntry`/`BenchmarkOpponent` table skeleton from data-model.md, pre-filled with all 7 `opponent_agents/` entries plus `agent_v58`/`agent_v60` sparring rows and T002's `slawekbiel` loadability result

---

## Phase 2: Foundational

**Purpose**: None beyond Phase 1 — this round has no shared infrastructure to build. The "foundational" relationship is expressed through the US1 → US2 → US3 sequencing itself (see Dependencies below), not a separate blocking phase.

---

## Phase 3: User Story 1 — Establish a Strong, Loadable Benchmark Opponent (Priority: P1)

**Goal**: Determine the "Round 7 benchmark opponent" — the loadable opponent against which `agent_v64` has the lowest win rate — via an opponent sweep plus intra-lineage sparring.

**Independent Test**: Run the sweep below (≥20 `--swap`/`opponents`-mode games per opponent) and confirm a win-rate table covering every loadable opponent plus `agent_v58`/`agent_v60` is produced, with a single benchmark opponent selected and documented.

### Implementation for User Story 1

- [X] T004 [US1] Run `uv run python eval.py opponents --agent agent_v64.py --games 20`; for each loadable opponent record `agent_v64`'s win rate (and for any opponent that fails to import, record `loadable=false` with the error) in `experiments/2026-06-1X-round7-opponent-matrix.md` (depends on T001-T003)
- [X] T005 [P] [US1] Run `uv run python eval.py h2h --agent0 agent_v64.py --agent1 agent_v58.py --games 20 --jobs 4 --swap`; record `agent_v64`'s win rate vs `agent_v58` in `experiments/2026-06-1X-round7-opponent-matrix.md`
- [X] T006 [P] [US1] Run `uv run python eval.py h2h --agent0 agent_v64.py --agent1 agent_v60.py --games 20 --jobs 4 --swap`; record `agent_v64`'s win rate vs `agent_v60` in `experiments/2026-06-1X-round7-opponent-matrix.md`
- [X] T007 [US1] From the T004-T006 table, select `<BENCHMARK>` = the loadable opponent (or sparring agent) against which `agent_v64` has the lowest win rate; if that win rate is ≥65%, note local-opponent saturation per the spec's acceptance scenario 3; document the `BenchmarkOpponent` decision (opponent file, `agent_v64_win_rate`, `is_saturated`, rationale) in `experiments/2026-06-1X-round7-opponent-matrix.md` (depends on T004-T006)

**Checkpoint**: `<BENCHMARK>` is determined and documented, with `agent_v64`'s baseline win rate vs it recorded. This is the required input for Phase 4 (US2) and Phase 5's benchmark re-check (T017).

---

## Phase 4: User Story 2 — Replay-Informed Gap Analysis vs the Benchmark Opponent (Priority: P2)

**Goal**: Generate fresh replays of `agent_v64` vs `<BENCHMARK>` and identify 2-3 new candidate tactical improvements, distinct from `agent_v57`-`agent_v67` and respecting Round 6's documented failure traps.

**Independent Test**: Given `<BENCHMARK>` from T007, produce a replay-analysis report covering ≥5 games with win rate, median divergence turn, decisive divergence window, ≥3 behavioral differences, and 2-3 candidate directions (hypothesis, predicted effect, risk, novelty check).

### Implementation for User Story 2

- [X] T008 [US2] Run `uv run python record_replays.py --our-agent agent_v64.py --opponent <BENCHMARK> --games 5 --out-dir replays` to produce `replays/replay_<benchmark-slug>_*.json` (depends on T007; if `<BENCHMARK>` fails to load at record time, fall back to the next-lowest-win-rate loadable opponent from T004-T006 per research.md R2 fallback)
- [X] T009 [US2] Invoke the `analyze-replay` skill on `replays/replay_<benchmark-slug>_*.json` to produce `experiments/YYYY-MM-DD-replay-analysis.md` with win rate, median divergence turn, decisive divergence window, and ≥3 behavioral differences (depends on T008)
- [X] T010 [US2] From the T009 report, select 2-3 candidate directions (each with hypothesis, predicted effect, risk); confirm each is distinct from mechanics already implemented or discarded in `agent_v57.py`-`agent_v67.py` (cf. README "Agents" table and `experiments/` history); for any candidate adjacent to a Round 6 discard (affordable fallback / global relative-strength garrison scaling), document `avoids_prior_failure` per data-model.md and research.md R2's guardrails; record all of this in `experiments/YYYY-MM-DD-replay-analysis.md` (depends on T009)

**Checkpoint**: 2-3 candidate directions are identified, confirmed novel, and (where adjacent to Round 6 discards) shown to avoid the prior failure mode. This is the required input for Phase 5 (US3).

---

## Phase 5: User Story 3 — Independently Test and Combine New Candidates (Priority: P3)

**Goal**: Fork `agent_v64` into `agent_v68.py`, implement the `<N>` candidates from T010 behind independent toggles, evaluate each independently vs `agent_v64`, combine any that pass, and re-check the resulting best config against `<BENCHMARK>`.

**Independent Test**: Each candidate, toggled on alone, evaluated over 50 `--swap` games vs `agent_v64`, with results recorded regardless of pass/fail; passing candidates combined and re-confirmed; resulting best config checked vs `<BENCHMARK>` for regression.

### Implementation for User Story 3

- [X] T011 [US3] Create `agent_v68.py` as a copy of `agent_v64.py`; update its module docstring to describe Round 7 and reference the `<N>` candidate directions from T010 (depends on T010)
- [X] T012 [US3] Add toggle constant `CANDIDATE_1_ENABLED = False` to `agent_v68.py` and implement Candidate 1's logic (per its T010 hypothesis), gated by the toggle, in an independent code region (depends on T011)
- [X] T013 [US3] Add toggle constant `CANDIDATE_2_ENABLED = False` to `agent_v68.py` and implement Candidate 2's logic (per its T010 hypothesis), gated by the toggle, in an independent code region (depends on T011; coordinate with T012 if both touch the same function)
- [x] T013a [US3] N/A — T010 selected only 2 candidates (Candidate 1: opening rush, Candidate 2: established-game rush); no 3rd candidate
- [X] T014 [US3] With `CANDIDATE_1_ENABLED=True` and all other candidate toggles `False`, run `uv run python eval.py h2h --agent0 agent_v68.py --agent1 agent_v64.py --games 50 --jobs 4 --swap --timing`; record Candidate 1's win rate (and p99 timing) in `experiments/YYYY-MM-DD-experiments-round7.md` (depends on T012, T013[, T013a])
- [X] T015 [US3] With `CANDIDATE_2_ENABLED=True` and all other candidate toggles `False`, run `uv run python eval.py h2h --agent0 agent_v68.py --agent1 agent_v64.py --games 50 --jobs 4 --swap --timing`; record Candidate 2's win rate (and p99 timing) (depends on T014)
- [x] T015a [US3] N/A — T013a is N/A (no 3rd candidate); skipped
- [X] T016 [US3] Set every candidate toggle that scored ≥52% in T014/T015[/T015a] to `True` (others `False`); if at least one candidate passed, run `uv run python eval.py h2h --agent0 agent_v68.py --agent1 agent_v64.py --games 50 --jobs 4 --swap --timing` and record the combined win rate, p99 per-turn timing, and sun/OOB loss count; if zero candidates passed, leave all toggles `False` (`agent_v68 ≡ agent_v64`) and record "N/A — no combination run" (depends on T015[/T015a])
- [X] T017 [US3] Benchmark re-check (FR-009/SC-005): if T016 produced a passing combined/single-best config, run both (a) `uv run python eval.py h2h --agent0 agent_v68.py --agent1 <BENCHMARK> --games 30 --jobs 4 --swap` and (b) `uv run python eval.py h2h --agent0 agent_v64.py --agent1 <BENCHMARK> --games 30 --jobs 4 --swap` for an apples-to-apples comparison; record both win rates and whether (a) ≥ (b) (`no_benchmark_regression`) in `experiments/YYYY-MM-DD-experiments-round7.md`. If T016 found zero passing candidates, `agent_v68 ≡ agent_v64`, so this check is trivially satisfied — record "N/A — agent_v68 ≡ agent_v64, no regression possible" and skip the eval runs (depends on T016)
- [X] T018 [US3] Write `experiments/YYYY-MM-DD-experiments-round7.md` documenting hypothesis, change, self-play result, and conclusion for each candidate (T014/T015[/T015a]), the combination (T016), and the benchmark re-check (T017), per Constitution Principle IV (depends on T017)

**Checkpoint**: All candidates evaluated; combined (or best single, or `agent_v64` if none pass) config's self-play and benchmark results are confirmed.

---

## Phase 6: Finalization & Documentation

**Purpose**: Apply FR-012/FR-013 — update project pointers to reflect this round's outcome

- [X] T019 If T016/T017 produced a passing, non-regressing config: update `README.md`'s Agents table (bold `agent_v68.py` as current best with its win rates vs `agent_v64` and `<BENCHMARK>`, un-bold `agent_v64.py`) and set `Makefile`'s `AGENT`/`RENDER_AGENT` to `agent_v68.py`. If nothing passed: add an `agent_v68.py` row documenting the discarded candidates (toggles default `False`, `agent_v68 ≡ agent_v64`), keep `agent_v64.py` bolded as current best, and leave `Makefile`'s `AGENT`/`RENDER_AGENT` at `agent_v64.py` (depends on T018)
- [X] T020 [P] Run `uv run python -m py_compile agent_v68.py` to confirm no syntax errors (depends on T011)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Empty — see Organization note above
- **US1 (Phase 3)**: Depends on Phase 1 (needs T001's prerequisite check and T003's log skeleton)
- **US2 (Phase 4)**: Depends on US1's checkpoint (T007 — needs `<BENCHMARK>`)
- **US3 (Phase 5)**: Depends on US2's checkpoint (T010 — needs the 2-3 candidates)
- **Finalization (Phase 6)**: Depends on US3's checkpoint (T018)

### Within Each Phase

- **Phase 1**: T002 and T003 are independent and can run in parallel; T001 is independent of both
- **Phase 3**: T005 and T006 are independent evals (different agent pairs) and can run in parallel with each other and with T004; T007 consumes all three
- **Phase 4**: T008 → T009 → T010 strictly sequential (each consumes the prior's output)
- **Phase 5**: T011 → {T012, T013[, T013a]} → T014 → T015[ → T015a] → T016 → T017 → T018. The per-candidate evals (T014/T015[/T015a]) are sequential because they require different toggle states of the *same* `agent_v68.py` file (cannot coexist)
- **Phase 6**: T019 and T020 are independent and can run in parallel

### Parallel Opportunities

- T002 and T003 (Phase 1) can run in parallel
- T004, T005, T006 (Phase 3) can run as three concurrent `eval.py` invocations
- T020 (Phase 6) can run in parallel with T019

---

## Parallel Example: Phase 3 (User Story 1)

```bash
# The opponent sweep and both sparring pairings are independent and can run concurrently:
uv run python eval.py opponents --agent agent_v64.py --games 20 &
uv run python eval.py h2h --agent0 agent_v64.py --agent1 agent_v58.py --games 20 --jobs 4 --swap &
uv run python eval.py h2h --agent0 agent_v64.py --agent1 agent_v60.py --games 20 --jobs 4 --swap &
wait
```

---

## Implementation Strategy

### Sequential by Necessity

Like Round 6, this round cannot follow a "parallel independent candidates" pattern (cf. Round 5), because each story's output is the next story's required input:

1. **US1 (T004-T007)**: Sweep `agent_v64` vs all loadable opponents + `agent_v58`/`agent_v60` → select `<BENCHMARK>`. **STOP and VALIDATE** the benchmark choice before proceeding — if every opponent yields ≥65%, flag saturation per T007's note before US2 relies on it for signal.
2. **US2 (T008-T010)**: Record replays of `agent_v64` vs `<BENCHMARK>` → run `analyze-replay` → get 2-3 candidates. **STOP and VALIDATE** that each candidate is novel and (if adjacent to a Round 6 discard) demonstrably avoids that discard's failure mode before writing any code.
3. **US3 (T011-T018)**: Fork, implement, eval each candidate independently, combine, benchmark-recheck.
4. **Finalization (T019-T020)**: Update README/Makefile per the outcome.

### Checkpoints

- After T007: `<BENCHMARK>` chosen and documented — go/no-go to start US2
- After T010: 2-3 novel candidates identified (with failure-mode guardrails satisfied) — go/no-go to start US3
- After T017: pass/fail and benchmark-regression status known — proceed to T018/T019
