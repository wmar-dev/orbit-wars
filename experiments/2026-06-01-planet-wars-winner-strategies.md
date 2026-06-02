# Experiment: Planet Wars Winner Strategies

**Date**: 2026-06-01
**Baseline**: agent_v56.py (score 846 on Kaggle leaderboard)
**Branch**: 016-planet-wars-winner-strategies

## Hypothesis

Four heuristic improvements derived from the 2010 Google AI Challenge Planet Wars winner (bocsimacko) will improve agent_v56:

- **Variant A (Surplus)**: Track intra-turn fleet commitments so surplus is not over-estimated.
- **Variant B (Redistribution)**: Send surplus ships from safe backline planets to frontline friendly planets.
- **Variant C (Spatial penalty)**: Reduce candidate score by per-ship amount based on nearby enemy density.
- **Variant D (Cooldown)**: Enforce a minimum 1-turn interval between dispatches from the same planet.

## Evaluation Protocol

| Stage | Games | Purpose | Threshold |
|-------|-------|---------|-----------|
| Screen | 50 | Eliminate harmful variants | Drop if score < 45% |
| Eval | 200 | Rank survivors | Advance if score ≥ 54% |
| Final | 400 | Confirm best | Submit candidate if ≥ 53% |

Eval command: `uv run python eval.py --agent0 <variant> --agent1 agent_v56.py --games N --jobs 8`

## Results Table

| Variant | File | Screen (50g) | Eval (200g) | Final (400g) | Status |
|---------|------|-------------|-------------|--------------|--------|
| A: Surplus | agent_v57_surplus.py | 47% (0W,3L,47D) | — | — | Neutral — no effect |
| B: Redistrib | agent_v57_redistrib.py | 4% (2W,48L) | — | — | ❌ Harmful — eliminated |
| C: Spatial 0.01 | agent_v57_spatial.py | 40% | — | — | ❌ Harmful at high weight |
| C: Spatial 0.005 | agent_v57_spatial.py | 44% | — | — | ❌ Borderline fail |
| C: Spatial 0.002 | agent_v57_spatial2.py | 49% (100g) | — | — | Neutral |
| D: Cooldown-1 | agent_v57_cooldown.py | 47% (0W,3L,47D) | 49.5% (7W,9L,184D) | — | Neutral |
| A+C (0.005) | agent_v57_ac.py | 50% (100g) | — | — | Neutral |

## Detailed Results

### Variant A — Surplus Commitment Tracking

**Implementation note**: The committed dict tracks intra-turn dispatches and adjusts the
available ship check from `mine.ships < ships_needed` to `mine.ships - committed < ships_needed`.
Since the current code dispatches at most once per planet per turn, committed is always 0 —
making Variant A behaviorally identical to v56.

**Screen attempt 1 (18% score)**: Bug — overly conservative garrison floor enforcement at dispatch
time. Fixed by removing the garrison floor constraint from the dispatch guard.

**Screen attempt 2 (47% — 0W, 3L, 47D)**:
```
Agent 0 (agent_v57_surplus.py): 0 wins
Agent 1 (agent_v56.py): 3 wins
Draws: 47
Score: 47.0%
```
Result: PASS screen. Behavioral analysis: effectively identical to v56 because committed
is always 0 when checked. No meaningful difference.

**Eval**: Not run — variant is neutral, no upside signal.

### Variant B — Redistribution

**Implementation note**: Sends surplus ships from safe backline planets to frontline planets
scored by `production / (min_dist_to_enemy + 1)`.

**Screen v1 (0% score)**: Bug — redistribution fired even for threatened planets, and sent
ships to comet planets about to evacuate. Fixed with stricter eligibility filters.

**Screen v2 (4% — 2W, 48L)**:
```
Agent 0 (agent_v57_redistrib.py): 2 wins
Agent 1 (agent_v56.py): 48 wins
Score: 4.0%
```
Result: FAIL — catastrophic even after bug fix.

**Root cause analysis**: Redistribution is fundamentally harmful in Orbit Wars because:
1. Planets orbit — "frontline" changes every turn. Ships sent to the "frontline" may arrive
   at a planet that has since moved to a safe position.
2. The transit time for redistribution ships (10–30 turns) means they miss the tactical window.
3. Reducing garrison on backline planets by 1/3 of surplus makes them vulnerable to flanking.
4. The receiving frontline planet may be captured by the time ships arrive, feeding ships to the enemy.

**Conclusion**: Redistribution does not work in Orbit Wars. Eliminated from all combinations.

### Variant C — Spatial Penalty

**Implementation note**: Pre-computes `enemy_neighborhood[t.id] = sum(enemy.ships for enemy in
range SPATIAL_RADIUS of t)`. Adjusts ROI: `adjusted_roi = roi - SPATIAL_PENALTY_WEIGHT * neighborhood`.
Filters candidates with adjusted_roi ≤ 0.

**Screen at 0.01 weight (40% — 20W, 30L)**:
```
Score: 40.0%
```
Result: FAIL — penalty too strong, many valid candidates filtered out.

**Screen at 0.005 weight (44% — 22W, 28L)**:
```
Score: 44.0%
```
Result: FAIL — still slightly below 45%, but within noise.

**Eval at 0.002 weight (100 games)**:
```
Agent 0 (agent_v57_spatial2.py): 46 wins
Agent 1 (agent_v56.py): 48 wins
Draws: 6
Score: 49.0%
```
Result: Neutral at this weight.

**Observation**: The spatial penalty may be directionally correct but the effect is very small.
The 40% → 44% improvement from 0.01 → 0.005 suggests the optimal weight might be 0.001–0.002.

### Variant D — Departure Cooldown (1 turn)

**Screen (47% — 0W, 3L, 47D)**:
```
Score: 47.0%
```

**Eval (200 games — 49.5%)**:
```
Agent 0 (agent_v57_cooldown.py): 7 wins
Agent 1 (agent_v56.py): 9 wins
Draws: 184
Score: 49.5%
```
Result: Neutral. The 92% draw rate (184/200) shows cooldown makes the game more passive.
Cooldown suppresses small fleet attacks, which increases stalemates.

**Root cause analysis**: In Orbit Wars, orbital mechanics create transient windows for attack.
A 1-turn cooldown causes the agent to miss these windows, leading to draws rather than
decisive wins. The post-mortem's MIN-TURN-TO-DEPART-1 was designed for Planet Wars
where planet positions are static — in Orbit Wars, each turn is a unique opportunity.

### Combination A+C (100 games)

```
Agent 0 (agent_v57_ac.py): 50 wins
Agent 1 (agent_v56.py): 50 wins
Draws: 0
Score: 50.0%
```
Result: Perfectly neutral. Combining two neutral variants produces a neutral result.

## Analysis Gate (T045)

**Solo screen results**:
- Variant A passed screen: YES (47%) — but behaviorally neutral
- Variant B passed screen: NO (4%) — eliminated from all combinations
- Variant C passed screen: NO (44%) — borderline, testing at lower weight
- Variant D passed screen: YES (47%) — behaviorally neutral at 200g

**Combinations being tested**:
- A+C (0.005): 100-game eval in progress
- C (0.002): 100-game eval in progress

**Combinations eliminated**: All combinations including B dropped.

## Root Cause Analysis — Why Techniques Didn't Transfer

The Planet Wars winner's techniques were designed for a game with **static planets**.
Orbit Wars has **orbiting planets**, which fundamentally changes the strategic calculus:

1. **Surplus/commitment tracking**: Only matters when a planet can dispatch multiple fleets
   per turn. Current v56 architecture dispatches at most once per planet per turn, so committed
   tracking has no effect.

2. **Redistribution**: Works in static-planet games where "frontline" is stable. In Orbit Wars,
   the frontline rotates with planetary orbits, making redistribution ships miss their windows.

3. **Spatial penalty**: The penalty correctly identifies deep-territory attacks as risky, but
   Orbit Wars games are short enough that aggressive expansion usually beats conservative play.
   The penalty discourages attacks that would have been profitable.

4. **Departure cooldown**: In static Planet Wars, fleet accumulation between attacks builds
   force effectively. In Orbit Wars, waiting forfeits attack windows that won't return for
   several orbits.

## Conclusion

**Result**: No improvement found. All variants are neutral (47–50%) or harmful (B: 4%).
**No new agent version created.** agent_v56 remains the best agent.

**What we learned**:
The 2010 Planet Wars winner's heuristics do not transfer to Orbit Wars due to orbital mechanics:
- **Redistribution** is actively harmful — transit time renders it tactically useless and strips garrison.
- **Cooldown** creates draws by forfeiting attack windows that won't recur for several orbits.
- **Spatial penalty** converges to neutral at any weight that doesn't harm normal attacks.
- **Commitment tracking** has no effect with the current single-dispatch-per-planet architecture.

**Recommended next steps**:
1. Pursue reinforcement learning (Constitution I) as the primary improvement path.
2. If continuing heuristics: focus on attack timing (predict when a planet garrison will be at minimum)
   rather than spatial positioning heuristics.
3. Consider multi-planet coordinated attacks (attack T1 and T2 simultaneously to prevent
   the enemy from reinforcing with ships originally bound for T1).
4. To make commitment tracking meaningful: allow multiple fleet dispatches per planet per turn
   when total ships dispatched ≤ surplus. This requires restructuring the main dispatch loop.
