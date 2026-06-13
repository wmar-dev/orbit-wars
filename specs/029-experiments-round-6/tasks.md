---
description: "Task list for experiments round 6 implementation"
---

# Tasks: Experiments Round 6

**Input**: Design documents from `/specs/029-experiments-round-6/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not applicable — this round's "tests" are the head-to-head evals and replay analysis specified by the acceptance scenarios themselves; no separate unit/contract tests are requested.

**Organization**: Unlike prior rounds (e.g., Round 5, where all 3 candidates were independent and pre-specified), Round 6's user stories are **sequentially dependent**: US1 determines the fork point (`<BASELINE>`) that US2 analyzes, and US2 produces the 2 candidates that US3 implements. Each story is still independently *checkpointable* — its output is a concrete artifact (a documented decision, a replay-analysis report, an evaluated agent) — but US2 cannot start until US1's checkpoint is reached, and US3 cannot start until US2's checkpoint is reached.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files/processes, no dependencies)
- **[Story]**: Which user story this task belongs to (US1=P1, US2=P2, US3=P3)
- `<BASELINE>` denotes whichever of `agent_v58.py` / `agent_v60.py` / `agent_v64.py` is selected in T007

## Path Conventions

- **Existing baselines (read-only)**: `agent_v58.py`, `agent_v60.py`, `agent_v64.py`, `opponent_agents/slawekbiel_agent.py`
- **New agent**: `agent_v67.py` (next available version number after `agent_v66.py`)
- **Replay captures**: `replays/replay_round6_*.json`
- **Experiment logs**: `experiments/2026-06-13-round6-baseline-matrix.md`, `experiments/YYYY-MM-DD-replay-analysis.md`, `experiments/YYYY-MM-DD-experiments-round6.md`
- **Config**: `README.md` (Agents table), `Makefile` (`AGENT`/`RENDER_AGENT`)

---

## Phase 1: Setup

**Purpose**: Confirm prerequisites and reserve the experiment log / agent file slot before any evals run

- [X] T001 Verify `agent_v58.py`, `agent_v60.py`, `agent_v64.py`, and `opponent_agents/slawekbiel_agent.py` all exist and run (`uv run python -c "import importlib; [importlib.import_module(m.replace('.py','').replace('/','.')) for m in ['agent_v58','agent_v60','agent_v64']]"`); confirm `agent_v67.py` does not yet exist
- [X] T002 [P] Read `SUBMISSIONS.md` and record the current Kaggle scores for `agent_v58`, `agent_v60`, and `agent_v64` — needed for the US1 cycle tiebreak rule (research.md R1)
- [X] T003 [P] Create `experiments/2026-06-13-round6-baseline-matrix.md` with the `WinRateMatrixEntry`/`Round6Baseline` table skeleton from data-model.md, pre-filled with the T002 Kaggle scores

---

## Phase 2: Foundational

**Purpose**: None beyond Phase 1 — this round has no shared infrastructure to build. The "foundational" relationship in this round is expressed through the US1 → US2 → US3 sequencing itself (see Dependencies below), not through a separate blocking phase.

---

## Phase 3: User Story 1 — Resolve Baseline Ambiguity (Priority: P1)

**Goal**: Determine a single "Round 6 baseline" agent among `agent_v58`, `agent_v60`, and `agent_v64` via a 150-game round-robin, resolving the Round 5 non-transitivity finding.

**Independent Test**: Run the 3 pairings below (50 `--swap` games each) and confirm a win-rate matrix with all 3 pairings is produced and a single baseline is documented with rationale.

### Implementation for User Story 1

- [X] T004 [P] [US1] Run `uv run python eval.py h2h --agent0 agent_v58.py --agent1 agent_v60.py --games 50 --jobs 4 --swap`; record the win rate in `experiments/2026-06-13-round6-baseline-matrix.md`
- [X] T005 [P] [US1] Run `uv run python eval.py h2h --agent0 agent_v58.py --agent1 agent_v64.py --games 50 --jobs 4 --swap`; record the win rate in `experiments/2026-06-13-round6-baseline-matrix.md`
- [X] T006 [P] [US1] Run `uv run python eval.py h2h --agent0 agent_v60.py --agent1 agent_v64.py --games 50 --jobs 4 --swap`; record the win rate in `experiments/2026-06-13-round6-baseline-matrix.md`
- [X] T007 [US1] From the T004-T006 matrix (and T002's Kaggle scores as tiebreaker if the matrix is non-transitive, per research.md R1 and spec.md Edge Cases), determine `<BASELINE>` and document the `Round6Baseline` decision (agent file, aggregate record, rationale, and any cycle found) in `experiments/2026-06-13-round6-baseline-matrix.md`

**Checkpoint**: `<BASELINE>` is determined and documented. This is the required input for Phase 4 (US2).

---

## Phase 4: User Story 2 — Replay-Informed Gap Analysis vs Top Local Opponent (Priority: P2)

**Goal**: Generate fresh replays of `<BASELINE>` vs `opponent_agents/slawekbiel_agent.py` and identify exactly 2 new candidate tactical improvements.

**Independent Test**: Given `<BASELINE>` from T007, produce a replay-analysis report covering ≥5 games with win rate, median divergence turn, ≥3 behavioral differences, and exactly 2 candidate directions.

### Implementation for User Story 2

- [X] T008 [US2] Generate 5 local replay JSON files of `<BASELINE>` vs `opponent_agents/slawekbiel_agent.py` (seeds 0–4) and save to `replays/replay_round6_0.json` through `replays/replay_round6_4.json`, per quickstart.md Phase B script
- [X] T009 [US2] Invoke the `analyze-replay` skill on `replays/replay_round6_*.json` to produce `experiments/YYYY-MM-DD-replay-analysis.md` with win rate, median divergence turn, and ≥3 behavioral differences (depends on T008)
- [X] T010 [US2] From the T009 report, select exactly 2 candidate directions and confirm each is distinct from mechanics already implemented or discarded in `agent_v57.py`–`agent_v66.py` (cf. README "How It Works" section and `experiments/` history); record the `distinct_from_prior` rationale for each in `experiments/YYYY-MM-DD-replay-analysis.md` (depends on T009)

**Checkpoint**: 2 candidate directions are identified and confirmed novel. This is the required input for Phase 5 (US3).

---

## Phase 5: User Story 3 — Independently Test and Combine New Candidates (Priority: P3)

**Goal**: Fork `<BASELINE>` into `agent_v67.py`, implement the 2 candidates from T010 behind independent toggles, evaluate each independently, and combine any that pass.

**Independent Test**: Each candidate, toggled on alone, evaluated over 50 `--swap` games vs `<BASELINE>`, with results recorded regardless of pass/fail; passing candidates combined and re-confirmed.

### Implementation for User Story 3

- [X] T011 [US3] Create `agent_v67.py` as a copy of `<BASELINE>.py`; update its module docstring to describe Round 6 and reference the 2 candidate directions from T010 (depends on T010)
- [X] T012 [US3] Add toggle constant `CANDIDATE_1_ENABLED` to `agent_v67.py` and implement Candidate 1's logic (per its T010 hypothesis), gated by the toggle (depends on T011)
- [X] T013 [US3] Add toggle constant `CANDIDATE_2_ENABLED` to `agent_v67.py` and implement Candidate 2's logic (per its T010 hypothesis), gated by the toggle (depends on T011; coordinate with T012 if both touch the same function)
- [X] T014 [US3] With `CANDIDATE_1_ENABLED=True, CANDIDATE_2_ENABLED=False`, run `uv run python eval.py h2h --agent0 agent_v67.py --agent1 <BASELINE>.py --games 50 --jobs 4 --swap`; record Candidate 1's win rate (depends on T012, T013) — **Result: 6.0% (3/50) — FAIL**
- [X] T015 [US3] With `CANDIDATE_1_ENABLED=False, CANDIDATE_2_ENABLED=True`, run `uv run python eval.py h2h --agent0 agent_v67.py --agent1 <BASELINE>.py --games 50 --jobs 4 --swap`; record Candidate 2's win rate (depends on T014) — **Result: 48.0% (24/50) — FAIL**
- [X] T016 [US3] Set all toggles that scored ≥52% in T014/T015 to `True` (others `False`); if at least one passed, run `uv run python eval.py h2h --agent0 agent_v67.py --agent1 <BASELINE>.py --games 50 --jobs 4 --swap --timing`; record combined win rate, p99 per-turn timing, and sun/OOB loss count (depends on T015) — **N/A: neither candidate passed; both toggles left `False` (agent_v67.py ≡ agent_v64.py)**
- [X] T017 [US3] Write `experiments/YYYY-MM-DD-experiments-round6.md` documenting hypothesis, change, self-play result, and conclusion for Candidate 1, Candidate 2, and the combination, per Constitution Principle IV (depends on T016)

**Checkpoint**: All candidates evaluated; combined (or best single) agent's result confirmed.

---

## Phase 6: Finalization & Documentation

**Purpose**: Apply FR-009/FR-010/FR-011 — update project pointers to reflect this round's outcome

- [X] T018 N/A — Phase 5 result did not pass (≥52% vs `<BASELINE>`); this branch does not apply
- [X] T019 No candidate passed: updated `README.md`'s Agents table to reflect the `<BASELINE>` determination from T007 (`agent_v64.py`, since `<BASELINE> != agent_v58.py`) — un-bolded `agent_v58.py`, bolded `agent_v64.py` as current best with the round 6 baseline-matrix result, corrected `agent_v65.py`'s row, added a new `agent_v67.py` row documenting both discarded candidates, and removed the stale "(current best)" tag from `agent_v58.py`'s prose entry. `Makefile`'s `AGENT`/`RENDER_AGENT` already updated to `agent_v64.py` (FR-011)
- [X] T020 [P] Ran `uv run python -m py_compile agent_v67.py` — OK, no syntax errors

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Empty — see Organization note above
- **US1 (Phase 3)**: Depends on Phase 1 (needs T002's Kaggle scores and T003's log skeleton)
- **US2 (Phase 4)**: Depends on US1's checkpoint (T007 — needs `<BASELINE>`)
- **US3 (Phase 5)**: Depends on US2's checkpoint (T010 — needs the 2 candidates)
- **Finalization (Phase 6)**: Depends on US3's checkpoint (T017)

### Within Each Phase

- **Phase 3**: T004, T005, T006 are independent evals (can run in parallel as separate processes) → T007 consumes all three
- **Phase 4**: T008 → T009 → T010 strictly sequential (each consumes the prior's output)
- **Phase 5**: T011 → {T012, T013} → T014 → T015 → T016 → T017. T014/T015 are sequential because they require different toggle states of the *same* `agent_v67.py` file (cannot coexist)
- **Phase 6**: T018/T019 are mutually exclusive (one or the other, based on T016's result); T020 is independent

### Parallel Opportunities

- T002 and T003 (Phase 1) can run in parallel
- T004, T005, T006 (Phase 3) can run in parallel — three independent `eval.py` invocations against different agent pairs
- T020 (Phase 6) can run in parallel with T018/T019

---

## Parallel Example: Phase 3 (User Story 1)

```bash
# All three pairings are independent and can run concurrently:
uv run python eval.py h2h --agent0 agent_v58.py --agent1 agent_v60.py --games 50 --jobs 4 --swap &
uv run python eval.py h2h --agent0 agent_v58.py --agent1 agent_v64.py --games 50 --jobs 4 --swap &
uv run python eval.py h2h --agent0 agent_v60.py --agent1 agent_v64.py --games 50 --jobs 4 --swap &
wait
```

---

## Implementation Strategy

### Sequential by Necessity

This round cannot follow the "implement all stories in parallel" pattern used in Round 5, because each story's output is the next story's required input:

1. **US1 (T004-T007)**: Run the 150-game matrix → determine `<BASELINE>`. **STOP and VALIDATE** the baseline decision before proceeding — if `<BASELINE>` differs from `agent_v58.py`, the rest of the round forks from a different file than the README currently implies.
2. **US2 (T008-T010)**: Generate replays of `<BASELINE>` → run `analyze-replay` → get 2 candidates. **STOP and VALIDATE** that both candidates are novel (not already in `agent_v57`-`agent_v66`) before writing any code.
3. **US3 (T011-T017)**: Fork, implement, eval each candidate independently, combine.
4. **Finalization (T018-T020)**: Update README/Makefile per the outcome.

### Checkpoints

- After T007: `<BASELINE>` chosen and documented — go/no-go to start US2
- After T010: 2 novel candidates identified — go/no-go to start US3
- After T016: pass/fail known for each candidate and the combination — proceed to T017/T018/T019
