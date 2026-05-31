# Tasks: Agent Decision Experiments

**Input**: Design documents from `specs/013-agent-decision-experiments/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅

**Organization**: Tasks are grouped by experiment (user story). Each experiment is
independently runnable — variant files are created, evaluated, and recorded before
moving to the next experiment. The four experiments run sequentially; within each
experiment, variant creation tasks are parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared output)
- **[Story]**: Experiment/user story label ([US1]–[US4])
- No test tasks — this feature uses eval harness results as the test signal

---

## Phase 1: Setup

**Purpose**: Create the experiment record scaffolding and verify the eval harness works.

- [x] T001 Create experiment record at experiments/013-agent-decisions.md with section headers for all four experiments and a combined results table (no data yet — just the structure from data-model.md)
- [x] T002 Smoke-test the eval harness: run `uv run python eval.py --agent0 agent_v38.py --agent1 agent_v38.py --games 10` to confirm symmetric self-play produces ~50% and the harness exits cleanly

---

## Phase 2: Foundational (Baseline Control)

**Purpose**: Establish the agent_v38 control baseline — the reference all variants are compared against.

**⚠️ CRITICAL**: Variant evals are meaningless without a confirmed control result.

- [x] T003 Run baseline control eval: `uv run python eval.py --agent0 agent_v38.py --agent1 agent_v38.py --games 50`. Record result in experiments/013-agent-decisions.md under "Control Baseline" (expect ~50% ± noise). This confirms the harness is stable at the 50-game scale.

**Checkpoint**: Harness confirmed stable. All four experiment phases can now begin.

---

## Phase 3: Experiment A — Target Scoring Formula (Priority: P1) 🎯 MVP

**Goal**: Determine whether the current ROI scoring formula is optimal or whether an
alternative scoring approach produces faster planet accumulation and higher win rate.

**Independent Test**: At least one scoring variant achieves ≥55% win rate vs agent_v38
over 50 games with seed 0, confirming the ROI formula is improvable (SC-001).

### Variant Creation (parallel — different output files)

- [x] T004 [P] [US1] Create agent_013_scoring_2.py by copying agent_v38.py and replacing the `_roi()` function with `production / (target.ships + 1)` — ignores distance entirely. Remove the reward-blend normalization (no REWARD_ALPHA needed). Keep all other logic identical to agent_v38.
- [x] T005 [P] [US1] Create agent_013_scoring_3.py by copying agent_v38.py and adding a distance gate to the candidate filtering loop: skip any target where `distance > nearest_enemy_dist * 1.5` (compute nearest_enemy_dist once per source planet as the distance to the closest non-owned planet). Keep the ROI formula unchanged for remaining candidates.
- [x] T006 [P] [US1] Create agent_013_scoring_4.py by copying agent_v38.py and replacing `_roi()` with a normalised linear blend: compute `prod_norm = t.production / map_max_prod` and `dist_norm = dist / map_max_dist` (both computed once per turn using max across all planets), then score = `0.67 * prod_norm + 0.33 * (1 - dist_norm)`. Remove the reward-blend normalization step.

### Evaluation (sequential — all write to same record file)

- [x] T007 [US1] Eval scoring-2: `uv run python eval.py --agent0 agent_013_scoring_2.py --agent1 agent_v38.py --games 50`. Record win rate and notes in experiments/013-agent-decisions.md under "Experiment A".
- [x] T008 [US1] Eval scoring-3: `uv run python eval.py --agent0 agent_013_scoring_3.py --agent1 agent_v38.py --games 50`. Record win rate and notes.
- [x] T009 [US1] Eval scoring-4: `uv run python eval.py --agent0 agent_013_scoring_4.py --agent1 agent_v38.py --games 50`. Record win rate and notes.
- [x] T010 [US1] Identify the best scoring variant (highest win rate) and record "Best: [variant], [win rate]" and a one-paragraph root cause analysis in experiments/013-agent-decisions.md Experiment A conclusion. If no variant beats 50%, record this finding and the likely reason.

**Checkpoint**: Experiment A complete. Best scoring formula identified. Experiment B can begin.

---

## Phase 4: Experiment B — Fleet Sizing Policy (Priority: P2)

**Goal**: Determine whether minimum-capture fleet sizing (`target.ships + 1`) is optimal,
or whether production-buffered or race-aware sizing produces higher capture success rate
and win rate.

**Independent Test**: At least one fleet sizing variant achieves ≥55% win rate vs agent_v38
over 50 games with seed 0, confirming minimum-capture sizing is improvable (SC-002).

### Variant Creation (parallel — different output files)

- [x] T011 [P] [US2] Create agent_013_fleet_2.py by copying agent_v38.py and replacing `ships_needed = best_target.ships + 1` with `travel_turns = dist_to_target / fleet_speed(best_target.ships + 1)` then `ships_needed = best_target.ships + 1 + int(math.ceil(best_target.production * travel_turns))`. Use `math.hypot(bx - mine.x, by - mine.y)` for dist_to_target. Keep all other logic identical.
- [x] T012 [P] [US2] Create agent_013_fleet_3.py by copying agent_v38.py and adding race detection before the `ships_needed` line: scan `raw_fleets` for enemy fleets where `_angle_diff(f_angle, atan2(best_target_y - f_y, best_target_x - f_x)) < 0.2` (RACE_EPSILON). If a qualifying enemy fleet exists, set `ships_needed = max(best_target.ships + 1, enemy_fleet.ships + best_target.ships + 1)`. Keep the existing `ships_needed = best_target.ships + 1` as default when no race is detected.
- [x] T013 [P] [US2] Create agent_013_fleet_4.py by combining both changes from T011 and T012: apply production-buffer first (fleet-2 formula), then apply race-aware override if an enemy fleet is heading toward the same target. The race-aware override computes remaining turns until enemy arrival and uses `enemy_fleet.ships + target_ships_at_arrival + 1` as the floor.

### Evaluation

- [x] T014 [US2] Eval fleet-2: `uv run python eval.py --agent0 agent_013_fleet_2.py --agent1 agent_v38.py --games 50`. Record win rate and notes in experiments/013-agent-decisions.md under "Experiment B".
- [x] T015 [US2] Eval fleet-3: `uv run python eval.py --agent0 agent_013_fleet_3.py --agent1 agent_v38.py --games 50`. Record win rate and notes.
- [x] T016 [US2] Eval fleet-4: `uv run python eval.py --agent0 agent_013_fleet_4.py --agent1 agent_v38.py --games 50`. Record win rate and notes.
- [x] T017 [US2] Identify best fleet sizing variant, record "Best: [variant], [win rate]" and root cause analysis in Experiment B conclusion. Note whether higher capture cost (more ships per send) helped or hurt in practice.

**Checkpoint**: Experiment B complete. Best fleet sizing policy identified. Experiment C can begin.

---

## Phase 5: Experiment C — Garrison Floor (Priority: P3)

**Goal**: Characterise the win-rate curve over garrison floor multipliers 1×–5× and test
a dynamic phase-based floor, to find the optimal balance between offensive surplus and
defensive retention.

**Independent Test**: The garrison floor sweep clearly identifies the optimal static
multiplier (SC-003). At least one variant achieves ≥50% win rate.

### Variant Creation (parallel — different output files)

- [x] T018 [P] [US3] Create agent_013_floor_1.py by copying agent_v38.py and changing `GARRISON_FLOOR_FACTOR = 3` to `GARRISON_FLOOR_FACTOR = 1`. One-line change.
- [x] T019 [P] [US3] Create agent_013_floor_2.py by copying agent_v38.py and changing `GARRISON_FLOOR_FACTOR = 3` to `GARRISON_FLOOR_FACTOR = 2`. One-line change.
- [x] T020 [P] [US3] Create agent_013_floor_4.py by copying agent_v38.py and changing `GARRISON_FLOOR_FACTOR = 3` to `GARRISON_FLOOR_FACTOR = 5`. One-line change.
- [x] T021 [P] [US3] Create agent_013_floor_5.py by copying agent_v38.py and replacing the static `GARRISON_FLOOR_FACTOR` with a dynamic computation inside the `agent()` function: add `step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)` then `dynamic_factor = 1.0 + 3.0 * min(step / 300.0, 1.0)` and use `dynamic_factor` in place of `GARRISON_FLOOR_FACTOR` in the floor calculation.

### Evaluation

- [x] T022 [US3] Eval floor-1 (factor=1): `uv run python eval.py --agent0 agent_013_floor_1.py --agent1 agent_v38.py --games 50`. Record win rate and planet-loss observations in Experiment C.
- [x] T023 [US3] Eval floor-2 (factor=2): run eval, record result.
- [x] T024 [US3] Eval floor-4 (factor=5): run eval, record result.
- [x] T025 [US3] Eval floor-5 (dynamic): run eval, record result.
- [x] T026 [US3] Identify best garrison floor variant. Record the win-rate curve (factor 1/2/3/5 + dynamic) as a table in Experiment C conclusion. Note the relationship between floor value and win rate — does it peak at a specific value, or is the curve monotone?

**Checkpoint**: Experiment C complete. Optimal garrison floor identified. Experiment D can begin.

---

## Phase 6: Experiment D — Source Assignment Policy (Priority: P4)

**Goal**: Determine whether surplus-gated multi-sender coordination (where any planet with
spare ships can optionally contribute to a shared target) beats the single-best-sender
rule, without regressing win rate.

**Independent Test**: Multi-sender variant achieves ≥50% win rate (no regression, SC-004)
and produces measurably more enemy-planet captures per game than single-sender baseline.

### Variant Creation (parallel — different output files)

- [x] T027 [P] [US4] Create agent_013_assign_2.py by copying agent_v38.py and adding a secondary-sender pass AFTER the primary `best_sender` dispatch loop. In the secondary pass: for each owned planet `p` not already dispatched this turn, compute `surplus_p = p.ships - floor(p)`. If `surplus_p > 10` (MIN_CONTRIB), find the highest-priority uncaptured target `t_best` by ROI score and dispatch `MIN_CONTRIB` ships from `p` to `t_best` (using the same orbit-lead position). Ensure `p` is still eligible to be a primary sender for other targets (do not mark it as dispatched after the secondary send).
- [x] T028 [P] [US4] Create agent_013_assign_3.py by copying agent_v38.py and modifying the `best_sender` assignment loop to also track `second_sender[t.id]` (the second-best by `dist / surplus` score). In the main dispatch loop, if `mine.id == second_sender.get(best_target.id)` and `mine.ships - floor(mine) >= ships_needed // 2 + 1`, also dispatch `ships_needed // 2 + 1` ships from this planet, sending to the same position as the primary sender. Primary sender sends `ships_needed - ships_needed // 2` ships (together they total `ships_needed + 1`).

### Evaluation

- [x] T029 [US4] Eval assign-2: `uv run python eval.py --agent0 agent_013_assign_2.py --agent1 agent_v38.py --games 50`. Record win rate in Experiment D. Use `--verbose` flag on a 10-game sample to manually count how many turns produce multi-planet dispatches to the same destination.
- [x] T030 [US4] Eval assign-3: run eval, record win rate. Also note from verbose output: how often does the second sender fire vs the primary?
- [x] T031 [US4] Identify best source assignment variant. Record "Best: [variant], [win rate]" and note the frequency of coordination events vs win-rate trade-off.

**Checkpoint**: All four experiments complete. Best variant from each experiment identified.

---

## Phase 7: Combined Agent & Promotion

**Purpose**: Stack the four best variants into agent_v42, run final eval, and promote
if the ≥60% win-rate target is met.

- [x] T032 Create agent_v42.py by applying all four best-variant changes to a single copy of agent_v38.py. Apply in this order to avoid merge conflicts: (1) garrison floor change, (2) fleet sizing policy change, (3) scoring formula change, (4) source assignment policy change. Verify the file passes `make test` (smoke test vs random).
- [x] T033 Run final eval: `uv run python eval.py --agent0 agent_v42.py --agent1 agent_v38.py --games 50`. This is the SC-005 gate.
- [x] T034 Record final combined results in experiments/013-agent-decisions.md under "Combined (agent_v42)": win rate, comparison to each individual experiment's best, and conclusion (does stacking the four improvements compound or interfere?).
- [x] T035 [P] If agent_v42 achieves ≥60% win rate: update README.md Agents table to add agent_v42 row with win rate and bold it as current best. Also update `AGENT` and `RENDER_AGENT` in Makefile to point to agent_v42.py.
- [x] T036 [P] If agent_v42 achieves ≥60% win rate: update CLAUDE.md to reference the final experiment record for context on the current best agent's provenance.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (needs harness confirmed working)
- **Experiment A (Phase 3)**: Depends on Phase 2 (needs control baseline)
- **Experiment B (Phase 4)**: Depends on Phase 2 (independent of Experiment A)
- **Experiment C (Phase 5)**: Depends on Phase 2 (independent of Experiments A and B)
- **Experiment D (Phase 6)**: Depends on Phase 2 (independent of Experiments A, B, and C)
- **Combined (Phase 7)**: Depends on all four experiments complete

### Experiment Independence

Experiments A, B, C, and D are independent of each other after Phase 2. Each changes a
different variable in agent_v38. If running sequentially (single developer), follow priority
order: A → B → C → D. If running in parallel (multiple sessions), all four can run
simultaneously after T003 completes.

### Within Each Experiment

- Variant creation tasks (T004–T006, T011–T013, T018–T021, T027–T028) are marked [P]
  and can run in parallel — each writes a different file.
- Eval tasks within the same experiment run sequentially — they all append to the same
  section of the experiment record.

---

## Parallel Execution Example: Experiment A (Scoring Variants)

```bash
# After T003 completes, create all three scoring variants simultaneously:
Task T004: "Create agent_013_scoring_2.py (production-first scoring)"
Task T005: "Create agent_013_scoring_3.py (distance-gated scoring)"
Task T006: "Create agent_013_scoring_4.py (linear-blend scoring)"

# Then run evals sequentially:
Task T007 → T008 → T009 → T010
```

## Parallel Execution Example: All Four Experiments

```bash
# After T003, run all four experiments in parallel (separate terminal sessions):
Session A: T004-T010  (scoring formula)
Session B: T011-T017  (fleet sizing)
Session C: T018-T026  (garrison floor)
Session D: T027-T031  (source assignment)
# Then converge at T032 (combine)
```

---

## Implementation Strategy

### MVP (Experiment A Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Baseline control (T003)
3. Complete Phase 3: Scoring experiment (T004–T010)
4. **STOP and VALIDATE**: Does any scoring variant beat 55%? If yes, this alone may be enough to combine with existing v38 logic. If no, proceed to Experiment B.

### Full Run

1. Complete Phases 1–2 (Setup + Baseline)
2. Run all four experiments A–D (sequentially or in parallel)
3. Combine best variants into agent_v42 (Phase 7)
4. Promote if ≥60% win rate met

### If No Variant Beats 50%

Record the null result: the 50-game eval scale may be insufficient to distinguish small
improvements. Consider re-running the best-performing variant at 200 games for statistical
confidence, or conclude that none of the tested alternatives improve on agent_v38's
current choices.

---

## Notes

- [P] tasks = write to different files, no shared output, safe to run in parallel
- Each user story = one isolated experiment (one changed variable)
- Variant "1" of each experiment = agent_v38 baseline = no separate file needed
- Eval commands all use `--seed 0` and `--games 50` for comparability
- Record results immediately after each eval run — do not batch
- Promote agent_v42 only if SC-005 (≥60% win rate) is met
- Do not submit to Kaggle in this feature — local eval only
