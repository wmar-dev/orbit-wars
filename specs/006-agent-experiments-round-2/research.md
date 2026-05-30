# Research: Agent Improvement Experiments — Round 2

**Branch**: `006-agent-experiments-round-2` | **Date**: 2026-05-30

All clarification questions were resolved in the spec session (including the orbit-lead targeting miss identified during spec authoring). This document consolidates design decisions and supporting rationale.

---

## Decision Log

### D-001: Speed-corrected orbit lead (Candidate E)

**Decision**: Compute `fleet_speed(target.ships + 1)` per target inside the candidates loop, replacing the single `speed = fleet_speed(mine.ships + 1)` that was computed once per source planet.

**Rationale**: `fleet_speed` is a non-linear function of ship count: `1 + 5 × (log(n)/log(1000))^1.5`. When a source planet has 80 ships but sends only 11, the current code estimates speed as `fleet_speed(81) ≈ 3.4` but the fleet actually travels at `fleet_speed(11) ≈ 2.0` — a 70% overestimate. The orbit-lead then predicts the target planet's position too early in its orbit, and the fleet arrives to find the planet has passed the aim point. The fix is to use the actual fleet size for speed estimation.

**Implementation detail**: The candidates loop must compute `speed_for_lead = fleet_speed(t.ships + 1)` for each target `t` before calling `_refined_orbit_lead`. The best-sender precomputation loop uses distance to current position (not orbit-led), so no change is needed there.

**Alternatives considered**:
- Use average of `fleet_speed(mine.ships + 1)` and `fleet_speed(target.ships + 1)` — rejected; the fleet actually travels at the speed determined by its launched size, not an average.
- Add a third refinement iteration in `_refined_orbit_lead` — addresses convergence but not the speed input error; does not fix the root cause.

---

### D-002: Transit-adjusted fleet sizing (Candidate F)

**Decision**: Estimate travel turns as `distance_to_predicted_pos / fleet_speed(target.ships + 1)` (using the orbit-lead predicted position for distance, not the current position). Send `ships_needed = int(target.ships + target.production × travel_turns + 1)`. If source doesn't have enough ships, skip this target.

**Rationale**: Planets produce ships every turn. If a target has 10 ships and production 3, and the fleet takes 12 turns to arrive, the garrison will have grown to ~46 ships. Sending `target.ships + 1 = 11` ships will lose this engagement silently, wasting 11 ships. Accounting for growth at launch time prevents failed captures.

**Interaction with Candidate E**: Both use `fleet_speed(target.ships + 1)` for travel time. If both pass, they share the same predicted position and travel-turns estimate in the combined agent — no conflict.

**Edge case — skip vs. fallback**: If adjusted `ships_needed > mine.ships`, the target is skipped. This differs from Candidate B (garrison sizing) which had a garrison floor that could prevent ALL planets from firing. The transit-adjusted skip applies only when the source genuinely can't win the engagement; other targets with lower ship counts or closer range remain available.

**Alternatives considered**:
- Cap at `mine.ships` and send anyway — defeats the purpose; we'd still lose the engagement.
- Use a fixed transit buffer (`target.ships + k`) instead of production-based — simpler, but insensitive to target production rate and travel distance.

---

### D-003: Adaptive range expansion (Candidate G)

**Decision**: Compute `range_factor` dynamically each turn:
- `own_ships = sum(p.ships for p in my_planets)`
- `enemy_ships = sum(p.ships for p in planets if p.owner == 1 - player)`
- If `own_ships / max(enemy_ships, 1) ≥ 1.5`: `range_factor = 3.5`
- If `own_ships / max(enemy_ships, 1) ≤ 0.7`: `range_factor = 1.5`
- Otherwise: `range_factor = 2.0` (unchanged from agent_v15)

**Rationale**: The 2× fixed range causes the agent to ignore distant high-value targets when winning (missed kill shots) and to overreach when losing (wasting ships on long shots). Adapting range to game state lets the agent press decisively when ahead and consolidate when behind.

**Why opponent-owned ships only (not neutral)**: Neutral ships don't attack; comparing own vs neutral would incorrectly signal "losing" during early-game expansion when neutrals outnumber everyone. Only the opponent's fighting strength is the meaningful reference.

**Alternatives considered**:
- Range factor based on planet count ratio instead of ship count — less sensitive to army buildup during expansion.
- Smoothly interpolate `range_factor` between 1.5–3.5 over the full ratio range — adds complexity with uncertain benefit given the 20-game eval window's high variance.

---

### D-004: Capture-ROI scoring (Candidate H)

**Decision**: Replace `target.production / distance` with `target.production × max(1, 100 - travel_turns) / max(1, target.ships + target.production × travel_turns + 1)`.

Where `travel_turns = distance / fleet_speed(target.ships + 1)`.

**Rationale**: The current `production/distance` score ignores capture cost. A planet 10 units away with production 3 and 80 ships scores the same as one 10 units away with production 3 and 5 ships, even though the 80-ship planet requires a large fleet and may take a long time to arrive. ROI scoring penalizes both the fleet cost (denominator) and late captures (numerator shrinks with travel time), rewarding fast, cheap captures that generate more production turns during the game.

**Formula interpretation**:
- Numerator: `production × (100 - travel_turns)` → how many production turns we'd own this planet for, assuming a 100-turn horizon
- Denominator: `target.ships + target.production × travel_turns + 1` → total ships the fleet must defeat (capture cost)
- Result: production-per-ship-spent, weighted by remaining game time

**Edge case — 100-turn proxy**: If `travel_turns > 99`, the multiplier would be ≤ 1, still giving a positive ROI for highly productive planets. The `max(1, ...)` guard ensures no target is scored at zero due to long transit.

**Alternatives considered**:
- Keep `production/distance` but add a `1/(1 + target.ships)` penalty factor — simpler, but doesn't account for production growth during transit.
- Use actual remaining game turns instead of 100 — requires reading the step counter from obs; adds coupling. 100-turn proxy is a calibrated constant.

---

### D-005: Diagnostic scope

**Decision**: Run `diagnose_v9.py` only on agent_v20 (combined), not on individual candidates (v16–v19).

**Rationale**: SC-004 requires zero sun/OOB losses on the combined agent. Candidates inherit agent_v15's safety guards and none of them modify path-safety logic, so individual diagnostic runs add cost without new signal. This matches the round 005 policy (D-007 in research.md).

---

### D-006: Integration order in agent_v20

**Decision**: Apply mechanics in this order each turn:

1. **Compute global state** (G): Compute `own_ships`, `enemy_ships`, and the dynamic `range_factor`.
2. **Precompute best-sender map** (D from v15, unchanged): For each target, find most efficient sender using `distance / surplus`.
3. **Per-source planet loop**:
   a. Compute `max_range = nearest_dist × range_factor` (G)
   b. For each candidate target:
      - Compute `speed_for_lead = fleet_speed(t.ships + 1)` (E)
      - Compute `x_pred, y_pred` via `_refined_orbit_lead` with corrected speed (E)
      - Apply range and path-safety filters
   c. Select best target by ROI score (H)
   d. Compute `ships_needed` with transit adjustment (F)
   e. Skip if source can't afford adjusted ships_needed

**Interaction guards**:
- Candidates E, F, and H all derive `travel_turns` from `fleet_speed(target.ships + 1)`. In agent_v20, compute once: `speed_for_target = fleet_speed(target.ships + 1)`.
- If F passes and E does not: use current-position distance for travel_turns in F (less accurate but still a net improvement over no adjustment).
- If neither F nor H passes: agent_v20 is just agent_v16 + agent_v18, and `ships_needed = target.ships + 1` reverts to baseline.

---

## Known Gaps (out of scope for round 2)

- **Fleet recall/retargeting**: If a launched fleet's target gets recaptured by the enemy en route, the fleet is wasted. Tracking and redirecting in-flight fleets requires per-turn state persistence — out of scope for rule-based agents.
- **Multi-wave attacks**: Coordinating sequential small fleets to overwhelm defenses. Requires turn-level planning — out of scope.
- **Reinforcement learning**: Still the long-term path per Constitution I. These experiments continue to narrow the heuristic gap before an RL baseline is introduced.
