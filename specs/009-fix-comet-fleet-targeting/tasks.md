# Tasks: Comet Evacuation Fix, Fleet Targeting Accuracy, and Agent Improvement Experiments

**Input**: Design documents from `specs/009-fix-comet-fleet-targeting/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/eval-cli.md ✅

**Format**: `[ID] [P?] [Story?] Description with file path`
- **[P]**: Parallelizable (independent file/scope, no blocking dependencies)
- **[Story]**: Which user story this belongs to (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Create working draft and experiment output directory

- [X] T001 Create `experiments/` directory at repo root if it does not already exist (`mkdir -p experiments`)
- [X] T002 Copy `agent_v31.py` → `agent_v32.py` as the working draft for all bug fixes in this feature

---

## Phase 2: Foundational — Constants and Shared Helpers

**Purpose**: New constants and helper functions that BOTH US1 (comet evacuation) and US2 (fleet targeting) depend on. Complete this phase before either user story.

**⚠️ CRITICAL**: US1 Phase 4 (`_converged_orbit_lead` call in evacuation) and US2 Phase 3 both depend on T003–T005 being present in agent_v32.py.

- [X] T003 Add `EVACUATE_THRESHOLD = 3`, `ORBIT_LEAD_EPS = 0.1`, and `ORBIT_LEAD_MAX_ITER = 10` as module-level constants in `agent_v32.py` (place after existing constants section near `GARRISON_FLOOR_FACTOR`)
- [X] T004 [P] Implement `_converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed, max_iter=ORBIT_LEAD_MAX_ITER, eps=ORBIT_LEAD_EPS) -> (float, float)` in `agent_v32.py` — fixed-point loop: start at `(t.x, t.y)`; each iteration computes `travel = hypot(x-mine.x, y-mine.y)/speed`, then `(nx, ny) = _predict_planet_pos(t, initial_planets_map, angular_velocity, travel)`; exit early if `hypot(nx-x, ny-y) < eps`; return last estimate after `max_iter` cap. This replaces `_refined_orbit_lead`.
- [X] T005 [P] Implement `_comet_two_pass(comet_planet, mine_x, mine_y, comet_path_lookup, speed) -> (float, float, bool)` in `agent_v32.py` — Pass 1: `t0 = hypot(comet.x-mine_x, comet.y-mine_y)/speed`, get `(x1, y1, valid1)` from `_comet_predicted_pos`; if not valid1 return `(comet.x, comet.y, False)`. Pass 2: `t1 = hypot(x1-mine_x, y1-mine_y)/speed`, get `(x2, y2, valid2)`; return `(x2, y2, True)` if valid2 else `(x1, y1, True)`.

**Checkpoint**: `_converged_orbit_lead` and `_comet_two_pass` present in agent_v32.py. US1 and US2 phases can now proceed.

---

## Phase 3: US2 — Fleet Targeting Accuracy (Priority: P1)

**Goal**: Fleets aimed at orbiting planets and comets reliably intercept their target rather than flying past into empty space.

**Independent Test**: Run `uv run python eval.py --verbose --agent0 agent_v32.py --agent1 agent_v31.py --games 5` and observe fleet-to-planet pairings; confirm fleets land rather than fly out-of-bounds.

- [X] T006 [US2] In `agent_v32.py` main targeting block (inside the `for mine in my_planets` loop, `candidates` construction): replace the call to `_refined_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed_for_lead)` with `_converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed_for_lead)`. Update the comet branch to call `_comet_two_pass(t, mine.x, mine.y, comet_path_lookup, speed_for_lead)` instead of `_comet_predicted_pos(t, comet_path_lookup, travel_turns)`.
- [X] T007 [US2] Remove the `_refined_orbit_lead` function from `agent_v32.py` (it is fully replaced by `_converged_orbit_lead`)
- [X] T008 [US2] Validate targeting: run `uv run python eval.py --verbose --agent0 agent_v32.py --agent1 agent_v31.py --games 5` and visually confirm from the verbose move log that fleet-target pairings correspond to orbiting planets, not just stale positions

**Checkpoint**: Fleet targeting uses convergent orbit-lead; no more systematic misses on fast-rotating targets.

---

## Phase 4: US1 — Comet Evacuation Fix (Priority: P1)

**Goal**: Ships garrisoned on agent-owned comets are always evacuated before the comet exits the board — zero ships lost to comet boundary expiry.

**Independent Test**: Run a 20-game eval; use `--verbose` to observe comet-owned planets; confirm they dispatch ships before disappearing.

**⚠️ Depends on**: T004 (`_converged_orbit_lead`) and T005 (`_comet_two_pass`) from Phase 2 must exist before T011.

- [X] T009 [US1] In `_build_comet_path_lookup` in `agent_v32.py`: remove the `remaining_steps = group.get("remaining_steps", 0)` (or `getattr(group, "remaining_steps", 0)`) read. In the per-planet loop, compute `remaining_turns = max(0, len(path) - path_index)` after setting `path` and `path_index`. Store `remaining_turns` in the lookup tuple as the 3rd element (replace `remaining_steps`). Update the tuple to `(path, path_index, remaining_turns)`.
- [X] T010 [US1] Update the comet departure/evacuation detection block in `agent_v32.py` (the loop that builds `departing_this_turn` and `evacuate_next_turn`): unpack `remaining_turns` from the lookup (was `remaining_steps`); set `departing_this_turn` when `remaining_turns == 0`; set `evacuate_next_turn` when `0 < remaining_turns <= EVACUATE_THRESHOLD`.
- [X] T011 [US1] Rewrite the evacuation dispatch block in `agent_v32.py` (the `if mine.id in evacuate_next_turn` branch): replace the `safe = [t for t in targets if _path_safe(...)]` filter with a pool of ALL planets except `mine` — both owned (`p.owner == player`) and non-owned. For each candidate planet, compute predicted position using `_converged_orbit_lead` (if orbiting), `_comet_two_pass` (if comet), or static position (if neither). Filter by `_path_safe(mine.x, mine.y, x_pred, y_pred, ...)`. Score owned planets as `p.production / (hypot(mine.x-p.x, mine.y-p.y) + EPSILON)` and non-owned as `_roi(p, x_pred, y_pred, mine)`. Select the highest-score planet; dispatch all `mine.ships` to its predicted position.
- [X] T012 [US1] Validate: run `uv run python eval.py --agent0 agent_v32.py --agent1 agent_v31.py --games 20 --verbose 2>&1 | grep -i comet` and confirm no comet-related ship losses appear in verbose output

**Checkpoint**: Comet evacuation fires correctly; ships are dispatched to the best destination before boundary expiry.

---

## Phase 5: agent_v32 Combined Validation

**Purpose**: Confirm both bugs are fixed, record as the new fixed baseline, and update project artifacts.

- [X] T013 Run 50-game evaluation of agent_v32 vs agent_v31 with reward logging: `uv run python eval.py --agent0 agent_v32.py --agent1 agent_v31.py --games 50 --jobs 4 --reward-log experiments/009-v32-baseline.jsonl`; confirm agent_v32 win rate > 50% and mean reward delta is positive
- [X] T014 Run reward analysis on v32 baseline: `uv run python reward_analysis.py experiments/009-v32-baseline.jsonl` and record mean per-turn reward delta in agent_v32.py docstring
- [X] T015 [P] Update agent_v32.py docstring (top of file) to document: both bugs fixed (comet remaining_turns from path, converged orbit-lead), what was inherited unchanged from agent_v31, and the baseline eval result vs agent_v31
- [X] T016 [P] Update `README.md` Agents table: add agent_v32 row with win rate vs agent_v31; bold agent_v32 as current best

**Checkpoint**: agent_v32 is the verified fixed baseline. Experiment round can begin.

---

## Phase 6: US3 — Experiment Round on Fixed Baseline (Priority: P2)

**Goal**: Retest all previously-failed candidates (P → J → K → R → L → I) against agent_v32; promote any candidate that achieves ≥ 55% win rate. Incorporate mid-game reward signal as secondary evaluation data.

**Independent Test**: At least one complete experiment record written per candidate; win-rate gate applied; best agent (v32 or v33) ready for Kaggle submission.

**Evaluation command template** (run for each candidate):
```bash
uv run python eval.py \
  --agent0 <candidate_file>.py \
  --agent1 agent_v32.py \
  --games 50 --jobs 4 \
  --reward-log experiments/009-candidate-<X>-retest.jsonl
uv run python reward_analysis.py experiments/009-candidate-<X>-retest.jsonl
```

### Candidate P — 3-Iteration Orbit Lead

- [X] T017 [US3] Document Candidate P as superseded: write `experiments/009-candidate-P-retest.md` recording that Candidate P (3-iteration orbit lead, 20% vs v20) is fully incorporated into agent_v32's converged `_converged_orbit_lead` function. Mechanic: fixed-point convergence supersedes 3 explicit iterations. Conclusion: no separate retest needed; functionality is the bug fix itself.

### Candidate J — Smooth Adaptive Range

- [X] T018 [US3] Implement Candidate J retest: copy `agent_v32.py` → `agent_v32_cand_J.py`. Candidate J (50% vs v20, 20 draws) used a smooth adaptive range cap that scaled the attack radius based on the ratio of surplus ships to distance. Inspect `agent_v20.py`–`agent_v29.py` commit history or range-cap comments to reconstruct the mechanic; apply to `agent_v32_cand_J.py`. Run the evaluation template above with this file.
- [X] T019 [US3] Write `experiments/009-candidate-J-retest.md` with hypothesis, mechanic description, win-rate result, mean reward delta, and pass/fail conclusion

### Candidate K — Enemy-Territory Priority

- [X] T020 [US3] Implement Candidate K retest: copy `agent_v32.py` → `agent_v32_cand_K.py`. Candidate K (50% vs v20, 20 draws) added a priority multiplier to ROI for targets in enemy-held quadrants (planets already owned by the opponent score higher than neutral planets of equal production). Apply this multiplier to the `_roi` scoring in `agent_v32_cand_K.py`. Run the evaluation template.
- [X] T021 [US3] Write `experiments/009-candidate-K-retest.md` with hypothesis, mechanic description, win-rate result, mean reward delta, and pass/fail conclusion

### Candidate R — Production-Squared ROI

- [X] T022 [US3] Implement Candidate R retest: copy `agent_v32.py` → `agent_v32_cand_R.py`. Candidate R (45% vs v20) replaced `t.production` with `t.production ** 2` in the ROI numerator to amplify preference for high-production planets. Apply this change to `_roi` in `agent_v32_cand_R.py`. Run the evaluation template.
- [X] T023 [US3] Write `experiments/009-candidate-R-retest.md` with hypothesis, mechanic description, win-rate result, mean reward delta, and pass/fail conclusion

### Candidate L — Two-Source Coordinated Attack

- [X] T024 [US3] Implement Candidate L retest: copy `agent_v32.py` → `agent_v32_cand_L.py`. Candidate L (40% vs v20) allowed a second sender to co-attack the same target in the same turn when the primary sender lacked sufficient ships. Specifically: if `best_sender[t.id]` can't field enough ships, find the next-closest sender and allow it to also send a fleet to the same target in the same turn. Apply to `agent_v32_cand_L.py`. Run the evaluation template.
- [X] T025 [US3] Write `experiments/009-candidate-L-retest.md` with hypothesis, mechanic description, win-rate result, mean reward delta, and pass/fail conclusion

### Candidate I — Reactive Defense Dispatch

- [X] T026 [US3] Implement Candidate I retest: copy `agent_v32.py` → `agent_v32_cand_I.py`. Candidate I (5% vs v20) sent a defensive reinforcement fleet from the nearest friendly planet when an enemy fleet was detected within `DEFENSE_RADIUS` of an owned planet. Apply this logic to `agent_v32_cand_I.py` with `DEFENSE_RADIUS = 20`. Run the evaluation template.
- [X] T027 [US3] Write `experiments/009-candidate-I-retest.md` with hypothesis, mechanic description, win-rate result, mean reward delta, and pass/fail conclusion

### Promotion Decision

- [X] T028 [US3] Review all 5 retest results (J, K, R, L, I). If any candidate achieved ≥ 55% win rate vs agent_v32: create `agent_v33.py` by applying that candidate's mechanic on top of `agent_v32.py`; run a 50-game confirm eval with reward-log to verify the result holds; record in `experiments/009-v33-promotion.md`. If multiple candidates passed, select the one with highest score; note any secondary candidates for future stacking.
- [X] T029 [US3] If no candidate passed and experiment scope warrants it: implement and evaluate Candidates T (weighted multi-fleet attack), U (comet opportunism v2), or V (dynamic garrison floor) per `research.md` R-007. Each requires its own candidate file and experiment record following the same template.
- [X] T030 [US3] Delete all temporary candidate agent files (`agent_v32_cand_*.py`) that failed the gate. Keep only `agent_v32.py`, `agent_v33.py` (if created), and experiment `.jsonl` logs.
- [X] T031 [US3] Update `README.md` Agents table: add agent_v33 (or confirm agent_v32 as best if no candidate passed); bold the current best agent
- [X] T032 [US3] Update `SUBMISSIONS.md` after the Kaggle submission is made manually (record agent version, date, and score once available)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final quality gates before submission.

- [X] T033 [P] Verify all required experiment records in `experiments/` are complete per constitution: each must have Hypothesis, Change, Self-play result, and Conclusion sections. File any incomplete records before submitting.
- [X] T034 [P] Confirm `SUBMISSIONS.md` references the correct agent version being submitted
- [X] T035 Review agent_v32.py (or v33.py) docstring: ensure it lists all candidates tested this round and their results, consistent with the pattern in agent_v30.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (T002 must create agent_v32.py first)
- **Phase 3 (US2) and Phase 4 (US1)**: Both depend on Phase 2 (T003–T005). US2 and US1 can proceed in parallel once Phase 2 is complete (different functions in the same file; coordinate edits)
- **Phase 5 (Validation)**: Depends on both Phase 3 AND Phase 4 complete
- **Phase 6 (US3)**: Depends on Phase 5 (agent_v32 validated)
- **Phase 7 (Polish)**: Depends on Phase 6 experiments complete

### User Story Dependencies

- **US2 (Fleet targeting)**: Depends on Foundational (T003–T005)
- **US1 (Comet evacuation)**: Depends on Foundational (T003–T005); T011 specifically needs `_converged_orbit_lead` (T004) for evacuation aim point
- **US3 (Experiments)**: Depends on US1 + US2 both complete and agent_v32 validated

### Within Each US3 Candidate

- Implement → Eval → Reward analysis → Write record → next candidate
- Candidates are sequential (review each result before proceeding)
- Experiment record must be written before moving to the next candidate (constitution requirement)

### Parallel Opportunities

- T004 and T005 (Phase 2): can be written simultaneously (different functions)
- T015 and T016 (Phase 5): can be done simultaneously (docstring vs README)
- T017 (Candidate P documentation): can be done in parallel with any Phase 5 task

---

## Parallel Example: Phase 2

```bash
# Simultaneous (different functions, same file — coordinate by writing one then the other):
Task T004: "Implement _converged_orbit_lead in agent_v32.py"
Task T005: "Implement _comet_two_pass in agent_v32.py"
```

## Parallel Example: Phase 5

```bash
# Simultaneously after T013 eval completes:
Task T015: "Update agent_v32.py docstring"
Task T016: "Update README.md Agents table"
```

---

## Implementation Strategy

### MVP (User Stories 1 and 2 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T005)
3. Complete Phase 3: US2 targeting fix (T006–T008)
4. Complete Phase 4: US1 comet evacuation (T009–T012)
5. Complete Phase 5: Validate agent_v32 (T013–T016)
6. **STOP and VALIDATE**: agent_v32 beats agent_v31 in 50-game eval

### Incremental Delivery

1. Phases 1–5: agent_v32 (bug fixes only, new personal best)
2. Phase 6: agent_v33 if experiments succeed (score push)
3. Phase 7: Submission-ready

### Notes

- [P] tasks = independent scope, no unresolved dependencies
- Each US3 candidate experiment must include a reward-log run (`--reward-log experiments/009-candidate-X-retest.jsonl`) per plan.md R-005
- The 55% win-rate threshold against agent_v32 is the sole pass/fail gate; mean reward delta is secondary and informational only
- Delete failing candidate files after recording results (keep repo clean)
- Kaggle submission is manual; record it in SUBMISSIONS.md after the fact
