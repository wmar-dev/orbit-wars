# Research: Agent Strategic Improvements

**Feature**: 019-agent-mcts-coordination-defense
**Date**: 2026-06-02

---

## Decision 1: MCTS vs Beam Search

**Question**: Should we use full MCTS (with UCB1 tree, random rollouts, backpropagation) or beam search (enumerate candidate action sets, simulate forward, pick best)?

**Timing baseline**: agent_v58 runs in 0.29ms avg / 1.43ms max per turn. With a 1000ms budget, we have headroom for ~3000+ greedy evaluations per second.

**Finding**: Full MCTS is complex — it requires a tree data structure, UCB1 node selection, and random rollout policies. Beam search (fixed-width forward lookahead) is simpler to implement and nearly as effective when the branching factor is moderate. For Orbit Wars with ~5–10 owned planets and ~20 candidate targets, the action space is large but the best actions are concentrated: only the top 3–5 targets per planet matter. A beam search that generates K candidate action sets (combinations of which target each planet attacks), simulates N turns forward, and picks the highest-scoring leaf is the right approach.

**Timing estimate for beam search**:
- Forward model per step: ~0.05ms (no orbit lead, no path safety — just production accumulation and fleet ETA countdown)
- 100 candidate sets × 5 simulated turns × 0.05ms = 25ms → well within budget
- Can afford 500+ candidates if needed

**Decision**: Implement **beam search** rather than full MCTS. Generate up to 200 candidate action sets by sampling combinations of per-planet fleet dispatches, simulate 5 turns forward per candidate using a fast forward model, score by `sum(own_production) - sum(enemy_production)` at the simulated terminal state, execute the best-scoring set. Fall back to v58 greedy if search exceeds 800ms.

**Rationale**: Beam search is easier to implement correctly within one session, avoids the complexity of tree balancing and rollout policies, and 0.29ms per greedy call leaves enough headroom for hundreds of simulations. The production-advantage score is a strong signal since games are won by production dominance.

**Alternatives considered**:
- Full MCTS with UCT: higher theoretical ceiling but much more code; defer to a follow-up feature
- Alpha-beta minimax: requires modeling opponent moves explicitly; opponent model would need to be approximate anyway, making beam search equivalent

---

## Decision 2: Forward Model Design

**Question**: How to simulate N turns ahead efficiently?

**Finding**: The full agent_v58 turn is expensive because it calls `_launch_corrected_orbit_lead` and `_path_safe` for every candidate target. For simulation, we don't need orbital precision — we need:
1. Planet ships to grow by `production` each step when owned
2. In-transit fleets to decrement ETA by 1 each step
3. Fleets arriving at ETA=0 to resolve: if fleet ships > garrison, capture; else reduce garrison
4. No new fleet launches during simulation (hold current action set fixed)

This reduces simulation to pure arithmetic: ~O(planets + fleets) per step, roughly 0.02–0.05ms.

**Decision**: Forward model uses flat arrays of `(owner, ships, production)` for planets and `(owner, target_id, ships, eta)` for fleets. Does NOT simulate opponent moves (assumes opponent holds or repeats last action). Does NOT recompute orbit positions. Validated: neutral planets are static garrisons, so fleet arrivals are computed with straight-line distance / fleet_speed.

**Rationale**: The approximation error from ignoring orbital motion over 5 turns is small (angular_velocity ≈ 0.037 rad/step → 0.185 rad over 5 steps = ~10 degrees of arc, or ~5 units positional error on a 100-unit board). For scoring production advantage, this is negligible.

---

## Decision 3: Action Set Generation

**Question**: How to generate K diverse candidate action sets?

**Finding**: Enumerating all combinations of per-planet actions is exponential (3^N for N planets each with 3 choices). For N=10 owned planets that would be 59049 combinations — too many. 

Better approach: generate candidates by:
1. **Greedy baseline**: current v58 action (always include)
2. **Per-target variations**: for each planet, swap its target to its 2nd or 3rd best ROI option
3. **Aggressive variants**: send fleets from multiple planets to the same high-value target (swarm)
4. **Defensive variants**: leave planets with incoming threats undeployed

This gives ~50–150 meaningful variations without combinatorial explosion.

**Decision**: Generate candidates as:
- 1 greedy baseline (v58 output)
- For each owned planet (up to 8): swap its target to 2nd-best → yields up to 8 variations
- For each high-value neutral (top 3 by ROI): send all surplus planets to it → yields 3 "swarm" variants
- Hold-all variant (no dispatches) as baseline
- Total: ~20–30 candidates. Evaluate all within 10–20ms.

**Rationale**: 20–30 candidates × 5 turns × 0.05ms/turn = ~5–8ms — very fast. Can expand to 100+ if needed.

---

## Decision 4: Fleet Coordination — Global Assignment

**Question**: How to prevent two mines from dispatching to the same target?

**Finding**: Current `best_sender` logic assigns each target to one source planet, but only by finding the single best source. The dispatch loop then picks the best target *for each mine* — if two mines both have the same planet as their best target, both dispatch. The `best_sender` check (`if best_sender.get(t.id) != mine.id`) prevents this... wait.

Re-reading: actually `best_sender[t.id]` maps each TARGET to its best SOURCE. Then in the mine loop, candidates for mine X only include targets where `best_sender[t.id] == X`. So each target is ALREADY assigned to exactly one source. The issue is different: two mines can independently pick the same target if they both show up as "best sender" for different targets, but one planet captures the target first, leaving the second fleet wasted.

The real redundancy issues are:
1. An in-transit own fleet is already heading to a target with sufficient ships, but another mine also dispatches to it
2. Two mines both dispatch because the target's `best_sender` changes turn-to-turn as positions orbit

**Decision**: Add a "covered targets" check: before dispatching, check if an in-transit own fleet has already sent `>= target.ships + 1` ships to that target. If so, skip it. This prevents the second-fleet redundancy without restructuring `best_sender`.

**Rationale**: Simpler than a full global assignment rewrite, addresses the actual redundancy case, and can be implemented in ~10 lines added to the dispatch check.

---

## Decision 5: Defensive Reinforcement

**Question**: When to reinforce vs. abandon a threatened planet?

**Finding**: The current agent computes `threat[pid]` (incoming enemy ships for each owned planet) and uses it for garrison floor (holding extra ships). But it never dispatches reinforcement.

The condition for dispatching defense:
- Enemy fleet ETA to owned planet P ≤ K turns
- `P.ships + P.production * ETA + reinforcement_ships > threat[pid]` (planet survives)
- Nearest allied planet Q has `Q.ships - garrison_floor > reinforcement_ships` (can afford)
- `Q` can dispatch and arrive at P before or simultaneously with the enemy fleet
- P's production justifies the cost: `P.production ≥ DEFENSE_MIN_PRODUCTION` (e.g., ≥ 2)

**Decision**: Add a defense pre-pass before the normal dispatch loop:
1. For each owned planet P with incoming threat, compute threat ETA from fleet position and speed
2. If P.production ≥ 2 and planet cannot hold on its own, find nearest allied planet Q with surplus
3. If Q can arrive in time (Q-to-P travel ≤ ETA), dispatch reinforcement from Q
4. Mark Q as having dispatched this turn (skip in normal loop)

**Rationale**: Keeps defense separate from the main loop for clarity. Threshold of production ≥ 2 avoids defending worthless planets. The ETA check ensures reinforcement actually arrives in time.

---

## Decision 6: Implementation Order and Combination

**Finding**: Each improvement can be developed and tested independently, then combined.

**Decision**: Implementation order:
1. **Fleet coordination** (simplest, ~20 lines) — validates the pattern
2. **Defense** (moderate, ~40 lines) — independent pre-pass
3. **Beam search** (largest, ~100 lines) — separate simulator module inline in the agent file
4. **Combined** (v59_combined) — all three active together

Each standalone variant gets its own 50-game eval. Combined gets 50-game eval. If combined ≥ 55% vs v58, it becomes the submission candidate (v59.py).

**Rationale**: Staging allows identifying which improvement contributes most (and whether any combination harms performance). Parallels the spec's US1/US2/US3 story structure.

---

## Summary

| Improvement | Approach | Key risk | Mitigation |
|---|---|---|---|
| Beam search | 20–30 candidates × 5-turn forward sim | Simulation inaccuracy | Use production-advantage score (robust to position errors) |
| Fleet coordination | In-transit coverage check | Missing real redundancy cases | Log redundant pairs before/after to validate |
| Defense | Pre-pass with ETA + production threshold | Over-defending (wasting offense) | Threshold production ≥ 2; ETA arrival check |
| Combined | All three active | Interactions causing regressions | Test each variant standalone first |
