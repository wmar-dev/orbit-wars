# Research: Agent Round 015

**Phase**: 0 — Research
**Feature**: specs/014-agent-round-015
**Date**: 2026-06-01

---

## Decision 1: ROI scoring mismatch — what exactly changes

**Decision**: Modify `_roi` to accept an optional `actual_fleet_size` parameter. When provided, use `fleet_speed(actual_fleet_size)` for the travel-time calculation instead of the default `fleet_speed(t.ships + 1)`.

**Rationale**: The travel time in `_roi` determines the time-decay multiplier (`100 - travel`) and is not used in the denominator's garrison estimate (`t.ships + t.production * travel + 1` — this term is kept as-is, since Experiment 014 Candidate A proved the denominator is empirically tuned, not a mechanical garrison model). Only the numerator's time-decay is affected. For enemy planets, we dispatch a fleet of `ships_needed` (larger than `t.ships + 1`), which travels faster, making the actual time-decay higher than `_roi` currently computes.

**How to pass `actual_fleet_size` during scoring**: For each enemy candidate in `roi_scores`, call `_enemy_fleet_size` upfront (before scoring) to get `ships_needed` and the corrected position. Store as `(t, bx, by, ships_needed)`. For neutral candidates, `ships_needed = t.ships + 1`. Pass this to `_roi`.

**Cost**: `_enemy_fleet_size` is called for every enemy candidate (not just the winner). Benchmark: in a typical 4-planet game with ~3 enemy candidates per planet, this adds ~12 extra `_enemy_fleet_size` calls per turn — negligible at Python speeds vs the 1s actTimeout.

**Alternatives considered**:
- Post-hoc re-score after selecting winner — does not change which target wins, only validates the winner; not useful.
- Keep numerator unchanged, only fix denominator — Experiment 014 Candidate A proves this breaks the calibrated ordering.

---

## Decision 2: Endgame ROI normalization — `remaining_turns` formula

**Decision**: `remaining_turns = max(1.0, 500.0 - step)` passed as a parameter to `_roi`, replacing the hardcoded `100.0` in `max(1.0, 100.0 - travel)`.

**Rationale**: `step` is available in `obs` at every turn (`obs.get("step", 0)`). The game has exactly 500 turns (episodeSteps default). The current constant 100.0 means the formula underestimates the time-decay penalty for distant targets in the first 400 turns (remaining is 400–100, so actual value would be higher than 100.0) and overestimates it in the last 100 turns (remaining < 100, so the formula should decay faster).

**Effect by game phase**:
- Turn 0–400: `remaining_turns` (100–500) ≥ 100, so `remaining_turns - travel` ≥ `100 - travel`. Enemy targets score *higher* when remaining time is generous. Net effect: early-game ROI is slightly inflated for distant targets → more aggressive expansion. Whether this helps depends on the game.
- Turn 400–500: `remaining_turns` (0–100) < 100, so `remaining_turns - travel` < `100 - travel`. Distant targets score *lower*. Agent focuses on nearby, quick captures. This is the intended improvement.

**Clamping**: `max(1.0, remaining_turns - travel)` prevents zero or negative scores.

**Alternatives considered**:
- Use `min(remaining_turns, 100.0)` as a cap: preserves current behavior until late game. Lower risk but misses the early-game signal. Start with uncapped version.

---

## Decision 3: Garrison defense buffer — where and what to add

**Decision**: In the garrison floor computation, when a planet has a nonzero inbound threat, add a buffer of `p.production * 2` above the raw threat count:

```
incoming = threat.get(src.id, 0)
buffer = src.production * 2 if incoming > 0 else 0
floor = max(src.production * GARRISON_FLOOR_FACTOR, incoming + buffer)
```

**Rationale**: If enemy sends exactly N ships and garrison = N, combat result is: N attacker vs N garrison → attacker does not exceed garrison (30 > 30 is false per CONTEST.md), so no capture. Garrison goes to max(0, N - N) = 0. Planet survives but is completely undefended the following turn. Adding `production × 2` means the planet has at least `production × 2` ships remaining after the attack (2 turns of recovery before the enemy can follow up).

**Guard**: The buffer only activates when `incoming > 0`, so there is no regression when no threat is detected.

**Alternatives considered**:
- Fixed buffer of 5 ships: doesn't scale with production; high-production planets deserve a larger buffer.
- Buffer = `production * 3`: more conservative but reduces offensive surplus. Start with `×2` and tune if candidate is marginal.

---

## Decision 4: Sender pre-screening — where to add the check

**Decision**: Inside the `best_sender` loop, for enemy-owned targets (`t.owner != -1`), compute a rough `ships_needed` estimate using the current target position (not orbit-lead) and exclude senders whose `src.ships` is less than this estimate.

```python
if t.owner != -1:
    naive_speed = fleet_speed(t.ships + 1)
    naive_dist = math.hypot(src.x - t.x, src.y - t.y)
    rough_needed = int(t.ships + t.production * (naive_dist / naive_speed)) + 1
    if src.ships < rough_needed:
        continue
```

**Rationale**: The current code picks the best sender by `dist / surplus`, then later drops the attack if `mine.ships < ships_needed`. No other sender gets a chance to cover the target. The pre-screen ensures we only assign senders that can actually deliver the required fleet.

**Approximation acceptable**: The rough estimate uses `t.x, t.y` (current position), not orbit-lead. For orbiting planets, the lead-corrected position may differ slightly, but the error is bounded. If a sender passes the pre-screen but fails the later exact check, the attack is still dropped (no correctness regression). The pre-screen is a filter, not a guarantee.

**Alternatives considered**:
- Pre-compute full `_enemy_fleet_size` for all (src, t) pairs during sender assignment: too expensive (quadratic in planets × targets).

---

## Decision 5: Committed ships accounting — reframed as friendly fleet sufficiency check

**Finding**: The original spec framing (subtract in-transit ships from surplus) is **incorrect**. When the game engine processes fleet launches (CONTEST.md step 3: "Fleet launch"), ships are immediately removed from the planet garrison. So `planet.ships` in the next turn's observation already reflects all prior dispatches. Subtracting in-transit ships from `surplus` would double-deduct.

**Reframing**: The real problem this candidate should solve is "re-attacking a target that already has sufficient friendly ships in transit." If a friendly fleet of size ≥ current garrison is already en route, sending a second fleet wastes ships that could go elsewhere.

**Decision**: During target candidate evaluation, for each target, check if a friendly fleet of size ≥ `ships_needed` is already in transit toward it. If so, skip that target. Use angle-matching (same ANGLE_EPSILON as threat detection) to identify fleets heading toward a target.

```python
covered_targets = set()
for f in raw_fleets:
    if f_owner != player:
        continue
    for t in targets:
        x_pred, y_pred = current_or_lead_pos(t)
        expected = atan2(y_pred - f_y, x_pred - f_x)
        if angle_diff(f_angle, expected) < ANGLE_EPSILON and f_ships >= ships_needed(t):
            covered_targets.add(t.id)
```

Senders skip targets in `covered_targets`.

**Alternatives considered**:
- Full cross-turn deduplication (v34): failed at 4% vs v33. That approach blocked ALL re-attacks. This version only blocks re-attacks where the in-transit fleet is already sufficient.

---

## Decision 6: Persistent campaign target — state mechanism

**Decision**: Use a module-level dict `_campaign: dict[int, tuple[int, float]]` mapping `planet_id → (target_id, roi_at_assignment)`. This persists across agent() calls within a single Kaggle episode (module globals survive between function calls in the Kaggle sandbox).

**Clearing conditions** (checked at start of each planet's dispatch loop):
1. Target no longer exists or is now owned by player → clear (capture succeeded or target changed).
2. A friendly fleet already covers the target (see Decision 5 logic) → clear.
3. Best available ROI exceeds stored ROI by >30% → switch to new target.
4. Planet has no surplus (can't dispatch anyway) → skip campaign turn but don't clear.

**Stability threshold of 30%**: Prevents flip-flopping while allowing genuine reprioritisation. If threshold proves too sticky (agent pursues obsolete targets), reduce to 20%.

**Risk**: If the module is re-imported mid-game (edge case in some Kaggle environments), `_campaign` resets. Acceptable risk — the agent degrades to current v47 behavior.

**Alternatives considered**:
- Closure-based state: cleaner but requires a factory function wrapping `agent()`. This changes the submission interface. Module global is simpler and matches Kaggle conventions seen in other agents.

---

## Constitution Compliance Notes

**Principle I (RL First)**: This round continues the heuristic-improvement track. RL experiments (round 011) failed to beat the heuristic baseline. The constitution allows heuristics as a "baseline or opponent seed." The standing practice of heuristic iteration is a documented deviation accepted since round 009. No new RL work is in scope for this round.

**Principle IV (Documentation)**: Each candidate requires an `experiments/015-*.md` entry with hypothesis, change, self-play result, and conclusion.

**Principle V (Self-play evaluation)**: 50 games per candidate vs agent_v47. Combined agent evaluated at 50 games vs agent_v47 and agent_v38.

**Principle VII (95% Confidence)**: 50-game sample gives ±7% margin at 95% confidence. A candidate at 56% win rate is distinguishable from 50% (random) at 95% confidence.

**All other principles**: No violations anticipated.
