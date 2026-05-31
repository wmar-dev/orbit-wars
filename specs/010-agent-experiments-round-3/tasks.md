# Tasks: Agent Improvement Experiments — Round 6

**Input**: Design documents from `specs/010-agent-experiments-round-3/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Baseline**: `agent_v33.py` (60% vs agent_v32, 50 games) — current local best

**Candidate slots**: v34 (S), v35 (T), v36 (U), v37 (V) | **Combined slot**: v38

**Evaluation**: 50 games vs agent_v33, score = (wins + 0.5×draws) / 50 | Pass ≥55% per candidate, ≥65% for combined

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependency)
- **[Story]**: User story label (US1–US4)

---

## Phase 1: Setup

**Purpose**: Verify evaluation harness is working before writing any new agent files

- [X] T001 Run 5-game smoke test to confirm eval harness: `python eval.py --agent0 agent_v33.py --agent1 agent_v33.py --games 5 --seed 0` — expect ~50% with no crashes

---

## Phase 2: Foundational — Experiment Records (Constitution Gate)

**Purpose**: Per Constitution IV, all experiment records MUST be written before any agent file is created

**⚠️ CRITICAL**: No candidate agent file (v34–v38) can be created until all four records exist with hypothesis, change description, and pass threshold filled in

- [X] T00X [P] Write Candidate S experiment record — hypothesis, change (ANGLE_EPSILON=0.1, in_transit dict, ships_needed deduction), pass threshold (≥55% vs agent_v33) in `experiments/010-candidate-S-fleet-dedup.md`
- [X] T00X [P] Write Candidate T experiment record — hypothesis, change (projected_garrison = target.ships + target.production × travel_turns, one fixed-point iter), pass threshold in `experiments/010-candidate-T-transit-sizing.md`
- [X] T00X [P] Write Candidate U experiment record — hypothesis, change (threat dict from obs.fleets, floor = max(3×prod, incoming_enemy_ships)), pass threshold in `experiments/010-candidate-U-threat-garrison.md`
- [X] T00X [P] Write Candidate V experiment record — hypothesis, change (effective_floor_factor = 1 when own_total ≥ 2.0 × enemy_total, else 3), pass threshold in `experiments/010-candidate-V-winning-throttle.md`

**Checkpoint**: All 4 experiment records exist with hypotheses filled in → candidate implementation can begin

---

## Phase 3: User Story 1 — Run Isolated Mechanic Experiments (Priority: P1) 🎯 MVP

**Goal**: Each of the four candidate mechanics is implemented, evaluated over 50 games vs agent_v33, and its experiment record is updated with results and a conclusion.

**Independent Test**: Run `python eval.py --agent0 agent_vN.py --agent1 agent_v33.py --games 50 --seed 0` for each candidate and confirm score is recorded in the experiment file. Evaluations are independent; all four can run simultaneously.

### Candidate S — Fleet Deduplication (agent_v34)

- [X] T00X [US1] Implement `agent_v34.py` — copy agent_v33.py; add `ANGLE_EPSILON = 0.1`; parse `obs.fleets` to build `in_transit` dict (angle-match friendly fleets to targets); replace `ships_needed = best_target.ships + 1` with `ships_needed = max(1, best_target.ships + 1 - in_transit.get(best_target.id, 0))`; skip if ships_needed ≤ 0; update docstring in `agent_v34.py`
- [X] T00X [US1] Evaluate Candidate S — run `python eval.py --agent0 agent_v34.py --agent1 agent_v33.py --games 50 --seed 0`; if score is 50–55%, extend to 100 games before deciding; record score in `experiments/010-candidate-S-fleet-dedup.md`

### Candidate T — Transit-Adjusted Sizing (agent_v35)

- [X] T00X [P] [US1] Implement `agent_v35.py` — copy agent_v33.py; add `travel_turns = math.ceil(dist / fleet_speed(best_target.ships + 1))`; replace `ships_needed = best_target.ships + 1` with `ships_needed = int(best_target.ships + best_target.production * travel_turns) + 1`; update docstring in `agent_v35.py`
- [X] T00X [US1] Evaluate Candidate T — run `python eval.py --agent0 agent_v35.py --agent1 agent_v33.py --games 50 --seed 0`; extend to 100 games if 50–55%; record score in `experiments/010-candidate-T-transit-sizing.md`

### Candidate U — Threat-Aware Garrison Floor (agent_v36)

- [X] T010 [P] [US1] Implement `agent_v36.py` — copy agent_v33.py; parse `obs.fleets` to build `threat` dict (angle-match enemy fleets to owned planets using ANGLE_EPSILON=0.1, accumulate ships); replace `_garrison_floor(src)` calls with `max(src.production * GARRISON_FLOOR_FACTOR, threat.get(src.id, 0))`; update docstring in `agent_v36.py`
- [X] T011 [US1] Evaluate Candidate U — run `python eval.py --agent0 agent_v36.py --agent1 agent_v33.py --games 50 --seed 0`; extend to 100 games if 50–55%; record score in `experiments/010-candidate-U-threat-garrison.md`

### Candidate V — Winning-State Garrison Reduction (agent_v37)

- [X] T012 [P] [US1] Implement `agent_v37.py` — copy agent_v33.py; after computing `my_planets` and `planets`, add `own_total = sum(p.ships for p in my_planets)`, `enemy_total = sum(p.ships for p in planets if p.owner not in (-1, player))`, `effective_floor_factor = 1 if own_total >= 2.0 * max(enemy_total, 1) else GARRISON_FLOOR_FACTOR`; replace `GARRISON_FLOOR_FACTOR` in `_garrison_floor` call with `effective_floor_factor` (pass as argument or inline); update docstring in `agent_v37.py`
- [X] T013 [US1] Evaluate Candidate V — run `python eval.py --agent0 agent_v37.py --agent1 agent_v33.py --games 50 --seed 0`; extend to 100 games if 50–55%; record score in `experiments/010-candidate-V-winning-throttle.md`

### Finalize US1

- [X] T014 [P] [US1] Fill in conclusion for Candidate S in `experiments/010-candidate-S-fleet-dedup.md` (pass/fail, root-cause note if failed)
- [X] T015 [P] [US1] Fill in conclusion for Candidate T in `experiments/010-candidate-T-transit-sizing.md`
- [X] T016 [P] [US1] Fill in conclusion for Candidate U in `experiments/010-candidate-U-threat-garrison.md`
- [X] T017 [P] [US1] Fill in conclusion for Candidate V in `experiments/010-candidate-V-winning-throttle.md`
- [X] T018 [US1] Update `README.md` Agents table — add rows for agent_v34, v35, v36, v37 with their scores and pass/fail status

**Checkpoint**: All 4 candidates evaluated, experiment records complete, README updated → ready for combined agent

---

## Phase 4: User Story 2 — Build Combined Agent (Priority: P2)

**Goal**: Stack all passing mechanics into agent_v38, evaluate at ≥65% target, run safety audit, and promote if passing.

**Independent Test**: Run `python eval.py --agent0 agent_v38.py --agent1 agent_v33.py --games 50 --seed 0` and confirm score ≥65%, then run `python diagnose_v9.py --agent agent_v38.py --games 50` and confirm 0 sun/OOB losses.

- [X] T019 [US2] Review all four candidate results (from T014–T017); identify which candidates scored ≥55% (or ≥55% in 100-game extension); document the inclusion list for agent_v38
- [X] T020 [US2] Write combined agent experiment record in `experiments/010-combined-v38.md` — list included mechanics (all passing candidates), hypothesis (expected ≥65% combined improvement), pass threshold
- [X] T021 [US2] Implement `agent_v38.py` — build on agent_v33.py; add a single shared `obs.fleets` parse pass that builds both `in_transit` and `threat` dicts; integrate all passing mechanics in the order specified in data-model.md (fleet parse → threat floor → winning factor → transit sizing → dedup); update docstring listing all stacked mechanics in `agent_v38.py`
- [X] T022 [US2] Evaluate combined agent — run `python eval.py --agent0 agent_v38.py --agent1 agent_v33.py --games 50 --seed 0`; if score fails ≥65%, test mechanic subsets to diagnose interaction regressions
- [X] T023 [US2] Run safety audit — `python diagnose_v9.py --agent agent_v38.py --games 50 --seed 0`; verify 0 sun losses and 0 OOB losses; record total launches and capture rate
- [X] T024 [US2] Fill in combined agent results and conclusion in `experiments/010-combined-v38.md` (score, safety results, PASS/FAIL determination)
- [X] T025 [US2] If agent_v38 passes ≥65% with 0 sun/OOB losses: update `README.md` Agents table adding agent_v38 bolded as new best, and update `AGENT` and `RENDER_AGENT` variables in `Makefile` to `agent_v38.py`

**Checkpoint**: agent_v38 promoted (or failed with root-cause documented) → ready for leaderboard submission

---

## Phase 5: User Story 3 — Leaderboard Submission (Priority: P3)

**Goal**: Submit the new best agent to Kaggle to measure leaderboard performance against real opponents.

**Independent Test**: A submission ID and score appear in SUBMISSIONS.md after the manual submission step.

- [X] T026 [US3] Manually submit the promoted agent to the Kaggle leaderboard via `make submit`; confirm submission ID is returned
- [X] T027 [US3] Record submission result in `SUBMISSIONS.md` — submission ID, agent version, score, date, delta vs prior best (agent_v8: 639.0), and any regression notes

**Checkpoint**: Submission recorded → feature complete

---

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T028 [P] If agent_v38 is promoted, add its description to the "How It Works" section in `README.md` (follow the existing pattern: one paragraph per agent explaining strategy and win rate)
- [X] T029 If no candidate passes ≥55% in Round 6, write revised hypothesis set for Round 7 in `experiments/010-round6-retrospective.md` — diagnose failure modes and propose 4 new candidate mechanics; do not close feature until hypotheses are documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — run immediately
- **Phase 2 (Foundational — Records)**: Depends on Phase 1 completion; blocks all candidate implementation (Constitution IV)
- **Phase 3 (US1 — Candidates)**: Depends on Phase 2 (all records written); candidates are independent of each other
- **Phase 4 (US2 — Combined)**: Depends on Phase 3 completion (all evaluations and conclusions recorded)
- **Phase 5 (US3 — Submission)**: Depends on Phase 4 (agent_v38 promoted)
- **Final Phase**: Depends on Phase 4; Polish T028 depends on promotion outcome

### Within Phase 3 (Candidate Evaluation)

Each candidate is fully independent:

```
Candidate S: T006 → T007 → T014
Candidate T: T008 → T009 → T015
Candidate U: T010 → T011 → T016
Candidate V: T012 → T013 → T017
                              ↓
                            T018 (all four complete before README update)
```

### Within Phase 4 (Combined)

```
T019 (review results) → T020 (write record) → T021 (implement v38) → T022 (eval) → T023 (safety) → T024 (record) → T025 (promote)
```

---

## Parallel Opportunities

### Phase 2 (Foundational Records)

All four experiment records can be written simultaneously:

```bash
# All four in parallel:
Task: "Write Candidate S record in experiments/010-candidate-S-fleet-dedup.md" (T002)
Task: "Write Candidate T record in experiments/010-candidate-T-transit-sizing.md" (T003)
Task: "Write Candidate U record in experiments/010-candidate-U-threat-garrison.md" (T004)
Task: "Write Candidate V record in experiments/010-candidate-V-winning-throttle.md" (T005)
```

### Phase 3 (Candidate Implementation)

All four candidate implementations can run simultaneously (different files):

```bash
# All four in parallel:
Task: "Implement agent_v34.py (Candidate S)" (T006)
Task: "Implement agent_v35.py (Candidate T)" (T008)
Task: "Implement agent_v36.py (Candidate U)" (T010)
Task: "Implement agent_v37.py (Candidate V)" (T012)
```

All four eval runs can be launched simultaneously after their respective implementations:

```bash
Task: "Evaluate Candidate S — eval.py agent_v34 vs agent_v33 --games 50" (T007)
Task: "Evaluate Candidate T — eval.py agent_v35 vs agent_v33 --games 50" (T009)
Task: "Evaluate Candidate U — eval.py agent_v36 vs agent_v33 --games 50" (T011)
Task: "Evaluate Candidate V — eval.py agent_v37 vs agent_v33 --games 50" (T013)
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Write all 4 experiment records (T002–T005)
3. Complete Phase 3: Implement and evaluate all 4 candidates (T006–T018)
4. **STOP and VALIDATE**: At least one mechanic passes ≥55%
5. Proceed to combined agent only if at least one candidate passes

### Incremental Delivery

1. Setup → experiment records → candidate evaluation → combined evaluation → submission
2. Each evaluation is a discrete result; stop early if 0 candidates pass
3. If combined agent fails 65%, test mechanic subsets before abandoning

### Parallel Strategy (single agent mode)

With a single implementer, work one candidate at a time, writing the experiment record immediately before the implementation. Run all four eval.py jobs in separate terminal tabs simultaneously (they are independent processes). Write README updates only after all four eval jobs complete.

---

## Notes

- [P] tasks = different files, no dependencies on each other
- [Story] label maps each task to its user story for traceability
- Constitution IV requires experiment record to exist BEFORE the agent file is created — do not skip Phase 2
- Borderline candidates (50–55%): extend to 100 games; do not fail based on 50-game result alone
- Draws count as 0.5 in score calculation: `(wins + 0.5 × draws) / total_games`
- If agent_v38 fails the 65% gate, test mechanic subsets (e.g., S+T only, V only) to find the best subset to promote instead
- Record everything — even failing candidates teach us which mechanics are incompatible with production² ROI + no-range-limit
