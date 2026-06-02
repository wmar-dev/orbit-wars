# Tasks: Fix Fleet Targeting When Both Source and Target Are Moving

**Feature**: 017-fix-moving-planet-targeting
**Input**: Design documents from `specs/017-fix-moving-planet-targeting/`
**Branch**: `017-fix-moving-planet-targeting`

---

## Phase 1: Setup

**Purpose**: Create the new agent file as the working copy for this feature.

- [x] T001 Copy `agent_v56.py` to `agent_v57.py` — add docstring header describing both fixes (launch-offset correction and path-safety intermediate prediction); leave all code identical to v56 for now

**Checkpoint**: `diff agent_v56.py agent_v57.py` shows only docstring differences.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Establish a baseline self-play measurement confirming the bug exists, so we can measure the fix.

- [x] T002 Run 20-game diagnostic to confirm baseline: `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 20 --jobs 8` — result should be ~50% (identical agents)

**Checkpoint**: Self-play of identical agents gives 48–52%. Eval harness is working.

---

## Phase 3: User Story 1 — Fix Fleet Intercept From Orbiting Source (Priority: P1) 🎯 MVP

**Goal**: Fleets dispatched from an orbiting source planet correctly intercept orbiting target planets by accounting for the launch position offset (`planet.radius + 0.1` ahead of planet center).

**Independent Test**: Run 50 games vs agent_v56 — win rate ≥ 45% (no regression). Then 200 games — win rate ≥ 55%.

### Implementation for User Story 1

- [x] T003 [US1] Add `_launch_corrected_orbit_lead` function in `agent_v57.py` — wraps `_converged_orbit_lead` with one additional pass: after computing the initial aim point from `mine.center`, compute the actual launch position as `mine.center + unit_vec * (mine.radius + 0.1)`, then re-run `_converged_orbit_lead` from the launch position to get a corrected aim point

  ```python
  # Pattern to implement in agent_v57.py:
  def _launch_corrected_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed):
      ax, ay = _converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed)
      dist = math.hypot(ax - mine.x, ay - mine.y)
      if dist < 1e-6:
          return ax, ay
      ux, uy = (ax - mine.x) / dist, (ay - mine.y) / dist
      lx = mine.x + ux * (mine.radius + 0.1)
      ly = mine.y + uy * (mine.radius + 0.1)
      mine_launch = type('M', (), {'x': lx, 'y': ly})()
      return _converged_orbit_lead(t, mine_launch, initial_planets_map, angular_velocity, speed)
  ```

- [x] T004 [US1] Replace all `_converged_orbit_lead(t, mine, ...)` call sites in `agent_v57.py` with `_launch_corrected_orbit_lead(t, mine, ...)` — specifically in: (a) the evacuation loop (`best_evac` search), (b) the main attack loop (targeting candidates), (c) `_enemy_fleet_size`'s internal recompute with `mine_fake` should also use the corrected version

  Note: for `_enemy_fleet_size`, the `mine_fake` already has explicit x/y set to `mine.center`; apply the same correction pattern there.

- [x] T005 [US1] Run 50-game screen eval: `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 50 --jobs 8`

  Pass criterion: ≥ 45% score. Record result in docstring of `agent_v57.py`.

- [x] T006 [US1] If screen passes (≥ 45%): run 200-game eval: `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 200 --jobs 8`

  Pass criterion: ≥ 55% win rate. If result < 55%, document findings and do NOT proceed to submission.

**Checkpoint**: Fix A is confirmed working. `agent_v57.py` beats `agent_v56.py` by ≥ 55% at 200 games, or Fix A is documented as neutral/harmful and the investigation continues.

---

## Phase 4: User Story 2 — Path Safety With Orbiting Intermediate Planets (Priority: P2)

**Goal**: `_path_safe` uses predicted intermediate planet positions (at flight midpoint) instead of current positions, preventing valid attacks from orbiting sources from being blocked by planets that have since moved.

**Independent Test**: Run 50 games of the updated agent vs agent_v56 — win rate should be ≥ 47% (no regression from Fix A). Combined with Fix A, expect higher than Fix A alone.

**Prerequisites**: T003–T006 complete (Fix A must be in `agent_v57.py` before adding Fix B).

### Implementation for User Story 2

- [x] T007 [US2] Update `_path_safe` signature in `agent_v57.py` to accept optional `initial_planets_map=None`, `angular_velocity=0.0`, `travel_turns=0.0` — for orbiting planets, predict position at `travel_turns / 2` instead of using current position:

  ```python
  def _path_safe(ox, oy, tx, ty, all_planets=None, target_id=None, source_id=None,
                 initial_planets_map=None, angular_velocity=0.0, travel_turns=0.0):
      # ... existing sun and OOB checks unchanged ...
      if all_planets:
          mid = travel_turns / 2.0
          for p in all_planets:
              if p.id == target_id or p.id == source_id:
                  continue
              if initial_planets_map and angular_velocity > 0 and mid > 0:
                  px, py = _predict_planet_pos(p, initial_planets_map, angular_velocity, mid)
              else:
                  px, py = p.x, p.y
              clearance = p.radius + PLANET_MARGIN
              if _segment_dist_to_point(ox, oy, tx, ty, px, py) < clearance:
                  return False
      return True
  ```

- [x] T008 [US2] Update all `_path_safe(...)` call sites in `agent_v57.py` to pass the additional keyword arguments:
  - Compute `travel = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(ships_needed)` for the call site in the main attack loop
  - Pass `initial_planets_map=initial_planets_map, angular_velocity=angular_velocity, travel_turns=travel`
  - Do the same for the evacuation loop's `_path_safe` call
  - Do the same for the post-`_enemy_fleet_size` re-validation call

- [x] T009 [US2] Run 50-game screen with both fixes: `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 50 --jobs 8`

  Pass criterion: ≥ 47% score (no regression from adding Fix B on top of Fix A). If < 47%, revert Fix B and keep Fix A only.

- [x] T010 [US2] If screen passes: run 200-game eval with both fixes: `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 200 --jobs 8`

  Record result in docstring. If combined result is worse than Fix A alone (T006 result), revert Fix B.

**Checkpoint**: Fix B either improves or is neutral vs Fix A. The best version of `agent_v57.py` is confirmed.

---

## Phase 5: Polish & Finalization

**Purpose**: Update project artifacts to reflect the new best agent.

- [x] T011 Update docstring in `agent_v57.py` with final eval result (win rate vs v56, game count, fix summary)

- [x] T012 [P] Update `main.py` docstring to reference `agent_v57` — replace agent_v56 description with agent_v57 description including both fixes and final win rate

- [x] T013 [P] Update README.md Agents table — add `agent_v57.py` row with final win rate vs v56; bold it as the new best agent; keep `agent_v56.py` row unchanged

- [x] T014 [P] Update `Makefile` `AGENT` and `RENDER_AGENT` variables to point to `agent_v57.py`

- [ ] T015 If eval result ≥ 55% at 200 games: submit manually via Kaggle and record submission in `SUBMISSIONS.md` with agent version, date, description, and pending score

**Checkpoint**: All project artifacts updated. `agent_v57.py` is the new production agent.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** (Setup): No dependencies — start immediately
- **Phase 2** (Foundational): Depends on T001 — quick baseline confirmation
- **Phase 3** (US1 — Fix A): Depends on T002 passing
- **Phase 4** (US2 — Fix B): Depends on T006 passing
- **Phase 5** (Polish): Depends on final eval result from T010 (or T006 if Fix B reverted)

### Task Dependencies Within Phases

- T003 → T004 → T005 → T006 (sequential: implement then eval)
- T007 → T008 → T009 → T010 (sequential: implement then eval)
- T011 → T012, T013, T014 can run in parallel after T011

### Parallel Opportunities

- T012, T013, T014 can be done in parallel (different files)

---

## Parallel Example: Phase 5 (Polish)

```bash
# After T011 is complete, run these together:
Task: "Update main.py docstring (T012)"
Task: "Update README.md Agents table (T013)"
Task: "Update Makefile (T014)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001: Copy agent_v56 → agent_v57
2. T002: Baseline self-play confirms 50%
3. T003–T004: Implement Fix A
4. T005–T006: Eval Fix A
5. **STOP and VALIDATE**: ≥ 55% win rate = Fix A works; proceed to Fix B or submit

### Full Delivery

1. Fix A (T003–T006) — intercept accuracy
2. Fix B (T007–T010) — path safety accuracy
3. Polish (T011–T015) — submit best version

### Decision Tree

```
T006 result:
  ≥ 55% → proceed to Fix B (T007)
  45–55% → proceed to Fix B (T007), but note Fix A alone is marginal
  < 45% → STOP — Fix A is regressive; diagnose before proceeding

T010 result vs T006:
  Better → keep both fixes; update docstring; polish + submit
  Same → keep both (no harm); update docstring; polish + submit  
  Worse → revert Fix B; use T006 agent; polish + submit
```

---

## Notes

- No tests directory required — eval.py IS the test harness for this project
- Each fix is isolated to specific functions; regression risk is low
- The launch-offset correction (Fix A) is the primary hypothesis; Fix B is additive
- `_launch_corrected_orbit_lead` must NOT be applied to the mine_fake in `_enemy_fleet_size` if the mine_fake already has an adjusted x/y — apply only where `mine` is a real Planet object
- Commits after each eval result for traceability
