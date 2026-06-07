# Tasks: Experiments Round 4

**Input**: Design documents from `specs/024-experiments-round-4/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create experimental platform from existing baseline

- [ ] T001 Create `agent_v64.py` as a copy of `agent_v63.py` with all round 4 experiment toggles added (OPPONENT_MODEL_V3_ENABLED=False, MULTI_TURN_PLAN_ENABLED=False, PHASE_DETECTION_ENABLED=False), all existing toggles preserved, WEIGHTED_EVAL_FIXED_ENABLED=True

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure for all experiments — experiment log, eval config, doc references

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 Create experiment log `experiments/2026-06-06-experiments-round4.md` with round 4 template: hypothesis table for 3 experiments, baseline (v63), per-experiment sections for results (PASS/DISCARD with win rate), combined config section, and slawekbiel sweep section
- [ ] T003 [P] Update `Makefile` AGENT variable to `agent_v64.py` (temporary — will revert if no experiments pass)

**Checkpoint**: Foundation ready — all three experiments can now proceed in parallel

---

## Phase 3: User Story 1 — Opponent Model v3 (Priority: P1) 🎯 MVP

**Goal**: Replace `_sim_opponent_step_v2` with a production-weighted/ROI-based opponent model (`_sim_opponent_step_v3`) that more closely matches real opponent behavior in forward simulation, making beam search evaluations more accurate against strong opponents like slawekbiel.

**Independent Test**: Run `python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing` with `OPPONENT_MODEL_V3_ENABLED=True` and all other round-4 toggles False. Target: ≥52% win rate vs v63.

### Implementation for User Story 1

- [ ] T004 [US1] Add `_sim_opponent_step_v3` in `agent_v64.py` that iterates enemy planets, computes surplus with garrison floor (gff ramp), selects targets by ROI (`_roi`-style production/distance scoring), computes fleet speed and ETA, and dispatches path-safe fleets — replaces the current nearest-target surplus-only model
- [ ] T005 [US1] Wire `_sim_opponent_step_v3` into `_SimState.step()` — when `OPPONENT_MODEL_V3_ENABLED=True`, call v3 instead of v2; when False, fall back to existing v2 behavior
- [ ] T006 [US1] Run independent eval vs v63: `python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing` — log win rate and timing to experiment log

**Checkpoint**: Opponent model v3 evaluated and logged. ≥52% → KEEP into combined config. If <50% → DISCARD.

---

## Phase 4: User Story 2 — Multi-Turn Plan Generation (Priority: P2)

**Goal**: Extend `_gen_beam_candidates` to include "skip" candidates where one or more source planets send 0 ships this turn, allowing beam search to evaluate waiting-to-build vs immediate dispatch.

**Independent Test**: Run `python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing` with `MULTI_TURN_PLAN_ENABLED=True` and all other round-4 toggles False. Target: ≥52% win rate vs v63.

### Implementation for User Story 2

- [ ] T007 [US2] Add skip-candidate generation in `_gen_beam_candidates` in `agent_v64.py`: for each mine, produce an alternative candidate where that mine sends no fleet (zero dispatch). The skip candidate's dispatches list excludes the mine; its moves list excludes that mine's move. Surrounding mines still dispatch normally.
- [ ] T008 [US2] Wire `MULTI_TURN_PLAN_ENABLED` toggle into `_gen_beam_candidates`: when True, append skip candidates to the candidate list; when False, behavior unchanged
- [ ] T009 [US2] Run independent eval vs v63: `python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing` — log win rate and timing to experiment log

**Checkpoint**: Multi-turn planning evaluated and logged. ≥52% → KEEP into combined config. If <50% → DISCARD.

---

## Phase 5: User Story 3 — Phase-Detection Dispatch (Priority: P3)

**Goal**: Add game-phase detection to `_greedy_moves` that adjusts GARRISON_FLOOR_FACTOR ramp, splinter window, and target selection based on the percentage of non-neutral planets owned and number of surviving opponents.

**Independent Test**: Run `python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing` with `PHASE_DETECTION_ENABLED=True` and all other round-4 toggles False. Target: ≥52% win rate vs v63.

### Implementation for User Story 3

- [ ] T010 [US3] Add `_detect_phase()` helper in `agent_v64.py` that computes `pct_owned = own_planets / max(1, non_neutral_count)` and detects three phases: Expansion (<40%), Mid-game (40-80%), Elimination (>80% or ≤1 opponent alive)
- [ ] T011 [US3] Integrate phase detection into `_greedy_moves` garrison floor computation: Expansion uses normal 1.5× ramp to 400; Mid-game reduces ramp ceiling; Elimination further reduces and disables splinter dispatch — respect `PHASE_DETECTION_ENABLED` toggle
- [ ] T012 [US3] Run independent eval vs v63: `python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing` — log win rate and timing to experiment log

**Checkpoint**: Phase detection evaluated and logged. ≥52% → KEEP into combined config. If <50% → DISCARD.

---

## Phase 6: Combined Configuration & Opponent Sweep

**Purpose**: Evaluate combined config with all passing experiments, run opponent sweep including slawekbiel, and prepare results

- [ ] T013 Enable all passing experiment toggles (from T006, T009, T012) in `agent_v64.py`, run combined eval vs v63: `python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing` — log combined win rate
- [ ] T014 [P] Run opponent sweep for combined config: 20 games each vs slawekbiel, sigmaborov, dylanxue04, yusufmurtaza — log win rates for each in experiment log
- [ ] T015 If combined win rate >52%, update `Makefile` AGENT to `agent_v64.py` (permanent) and `README.md` with v64 row in agent table; otherwise revert Makefile from T003
- [ ] T016 Update `AGENTS.md` SPECKIT block with results summary

**Checkpoint**: All experiments evaluated. Results in experiment log. README and Makefile reflect final state.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1, US2, US3 are INDEPENDENT — can run in parallel
- **Combined (Phase 6)**: Depends on all 3 user stories being evaluated

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — No dependencies on US2 or US3
- **US2 (P2)**: Can start after Phase 2 — No dependencies on US1 or US3
- **US3 (P3)**: Can start after Phase 2 — No dependencies on US1 or US2

### Within Each User Story

- Implementation before evaluation
- Evaluation logged before proceeding to next story
- Story complete before Phase 6

### Parallel Opportunities

- T003 [P] (foundational Makefile update) can run alongside T004-T012
- T014 [P] (opponent sweep) can run in parallel per opponent
- US1, US2, US3 share the SAME file (`agent_v64.py`) — MUST run sequentially within each story (T004→T005→T006, T007→T008→T009, T010→T011→T012)

---

## Parallel Example: User Story 1

```bash
# T004: Add _sim_opponent_step_v3 in agent_v64.py
# T005: Wire v3 into _SimState.step() in agent_v64.py
# T006: Run eval vs v63
# Sequential (same file): T004 → T005 → T006
```

## Parallel Example: All Three Stories

```bash
# US1 (P1): agent_v64.py — _sim_opponent_step_v3 section
# US2 (P2): agent_v64.py — _gen_beam_candidates section  
# US3 (P3): agent_v64.py — _detect_phase / _greedy_moves section
# All three modify DIFFERENT functions in the same file — careful merge required
# Execute sequentially: T004-T006, then T007-T009, then T010-T012 (merge order matters)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002, T003)
3. Complete Phase 3: US1 — Opponent Model v3 (T004-T006)
4. **STOP and VALIDATE**: Run opponent sweep including slawekbiel
5. If slawekbiel win rate >0%, this is the best single improvement this round

### Incremental Delivery

1. Setup + Foundational → ready
2. Add US1 (Opponent Model v3) → Test → Evaluate
3. Add US2 (Multi-Turn Planning) → Test → Evaluate (may stack on US1 if both pass)
4. Add US3 (Phase Detection) → Test → Evaluate (may stack on passing experiments)
5. Combined config with all passing experiments → final sweep
