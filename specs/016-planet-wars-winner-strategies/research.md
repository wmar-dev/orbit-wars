# Research: Planet Wars Winner Strategies

**Date**: 2026-06-01
**Sources**: quotenil.com/Planet-Wars-Post-Mortem.html, github.com/melisgl/planet-wars

---

## Decision 1: Which winner techniques are applicable to Orbit Wars?

**Decision**: Four techniques map directly to Orbit Wars mechanics. Alpha-beta search / multi-turn scheduling is deferred.

**Rationale**:
- Orbit Wars and Planet Wars share the core loop: capture planets, grow production, dispatch fleets.
- The four selected techniques (surplus, redistribution, spatial penalty, departure cooldown) operate at the per-turn decision level and require no fundamental architecture change.
- Alpha-beta search requires a full game simulator, which is not available in the current eval setup. It is out of scope for this feature.

**Alternatives considered**:
- Full alpha-beta search: High potential but requires a forward model of the game state. Left for a future dedicated spec.
- Nash equilibrium mixed strategies: The post-mortem explicitly says this "kept making mistakes." Rejected.
- Neutral planet evaluation in primary scoring: Post-mortem notes this "paradoxically encouraged inaction." Current agent already handles neutrals separately from enemy planets via the `owner == -1` branch — this is already close to correct.

---

## Decision 2: How to track in-flight commitment without access to own fleet positions?

**Decision**: Track intra-turn commitments only (within a single `agent()` call). Module-level tracking is not needed for commitment because we cannot observe previously-dispatched fleets in `obs`.

**Rationale**:
- The Orbit Wars observation does not expose a player's own in-flight fleets (only enemy fleets are visible in the `fleets` list filtered by owner).
- Therefore full multi-turn surplus accounting is impossible without a separate flight log.
- Intra-turn tracking catches the most common surplus violation: a planet dispatching more ships than it should because a previous loop iteration already consumed its surplus.

**Alternatives considered**:
- Module-level flight log: Possible but fragile (resets on agent re-import, wrong if env resets mid-game). The intra-turn fix is simpler and addresses the most common case.

---

## Decision 3: What redistribution heuristic avoids hurting the agent?

**Decision**: Redistribution fires only if source surplus exceeds a threshold (default 10 ships) AND source has no offensive target this turn. Target is the friendly planet with the highest `production / (min_dist_to_enemy + 1)` score.

**Rationale**:
- Without a threshold, redistribution wastes ships on tiny transfers and creates unnecessary fleet traffic.
- The `no offensive target this turn` guard ensures redistribution never competes with attacks — attacks always win.
- Choosing the frontline planet (closest to enemies, highest production) as the target maximizes the strategic value of consolidated ships.

**Alternatives considered**:
- Always redistribute: Creates oscillating fleets between planets and no net improvement. Rejected.
- Redistribute toward weakest friendly planet: Defensive orientation, contradicts the forward-pressure goal. Rejected.

---

## Decision 4: What spatial penalty weight avoids over-penalizing?

**Decision**: Start with `SPATIAL_PENALTY_WEIGHT = 0.01` applied to the sum of enemy planet ships within 30 units of the target. The weight is a named constant for easy tuning.

**Rationale**:
- The post-mortem describes "a slight continuous penalty per enemy ship." The word "slight" suggests a small coefficient.
- An ROI score of 1.0 for a good neutral represents about 100 production² / 100 ships ≈ 1. Enemy sums within 30 units typically range 10–150 ships. At 0.01, penalty is 0.1–1.5, enough to differentiate but not override obvious wins.
- Radius 30 is ~30% of the board — captures meaningful neighborhood without globally weighting the whole map.

**Alternatives considered**:
- Weight 0.001: Too small to affect decisions in most cases. May start there if 0.01 is too aggressive.
- Weight 0.1: At this weight, a planet surrounded by 50 enemy ships gets a penalty of 5, which would dominate most ROI scores. Too aggressive.
- Radius 50 (half the board): Too global — effectively penalizes all targets near the center. Rejected.

---

## Decision 5: What cooldown value best matches the post-mortem's MIN-TURN-TO-DEPART-1?

**Decision**: Test 1-turn cooldown (default) and 2-turn cooldown as separate variants. The post-mortem sets `MIN-TURN-TO-DEPART-1 = 2`, meaning a planet waits at least 2 turns between consecutive fleet dispatches.

**Rationale**:
- In the original contest, this was the single most impactful parameter change.
- Orbit Wars fleet sizes and production rates may differ, so we test both values empirically.
- Cooldown does not apply to evacuation (comet approaching) or defensive response (garrison under threat), preserving safety.

**Alternatives considered**:
- Cooldown 3+: Likely too restrictive for Orbit Wars where production is relatively fast. Test only if 1 and 2 both improve.

---

## Decision 6: Sample sizes for statistical validity at 95% confidence

**Decision**: 50-game screen → 200-game eval → 400-game final.

**Rationale** (binomial proportions, two-tailed z-test):
- At 50 games: 95% CI width ≈ ±14%. Can only confidently detect improvements ≥ 15%. Use for elimination only.
- At 200 games: 95% CI width ≈ ±7%. Can detect improvements ≥ 8% with 80% power.
- At 400 games: 95% CI width ≈ ±5%. Can detect improvements ≥ 5% with 80% power. Sufficient for submission confidence.

This satisfies Constitution Principle VII (95% confidence gate) for the submission decision.

---

## Implementation Notes from GitHub Source

The winning bot (Common Lisp, `alpha-beta.lisp`) implements:
1. **Step-based architecture**: A "step" bundles a set of fleet orders targeting one planet; multiple steps combine into a "move". This is more complex than our single-dispatch architecture but the outputs are equivalent.
2. **Surplus calculation**: `(surplus planet)` computes ships available after all scheduled orders are accounted for. We approximate this with intra-turn commitment tracking.
3. **Redistribution**: Explicit logic to move ships from safe backline planets to contested frontline planets.
4. **Positional penalty**: Applied as a score modifier in the evaluation function, not as a hard constraint.

The core insight: the bot treats planet evaluation as an optimization over a scoring function that accounts for spatial context, not just point-in-time ROI.
