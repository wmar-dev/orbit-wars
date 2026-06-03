# Research: Early Expansion Experiments from Replay 78539022

**Feature**: 018-replay-neutral-fleet-experiments
**Date**: 2026-06-02

---

## Decision 1: Root cause of delayed first fleet dispatch

**Question**: Why did P0 (our agent) first dispatch a fleet at step 12 while P1 dispatched at step 6?

**Finding**: The root cause is a silent "skip" in the targeting loop. Agent v57 selects the single highest-ROI target per source planet, then checks `if mine.ships < ships_needed: continue`. If the best ROI target (Planet 16, 31 ships needed) is unaffordable, the agent does **not** fall back to cheaper candidates — it skips the mine entirely for that turn.

At step 6, P0's home planet had ~24 ships (estimated from initial+growth). Planet 16 needed 31 ships → unaffordable, skip. Planet 8 also had 18 ships and was within budget (needed 19), but it never got evaluated because the agent already picked planet 16 as best and bailed when it couldn't afford it.

Relevant code: [agent_v57.py:380-413](../../agent_v57.py#L380)

**Decision**: The primary experiment is adding an affordability fallback — if the highest-ROI target is unaffordable, fall through to the next-best target that `mine.ships >= ships_needed`.

**Rationale**: This fixes a correctness bug rather than a strategy change. The agent should still prefer high-ROI targets but should not sit idle waiting for ships when cheaper targets exist.

**Alternatives considered**:
- Pre-filter candidates to affordable-only: simpler, but loses the ability to "save up" for a clearly superior expensive target (e.g., a nearby high-growth planet worth waiting for)
- Change ROI formula: doesn't address the dispatch timing problem; planet 16's ROI was only slightly above planet 8's, so formula changes alone wouldn't reliably fix the delay

---

## Decision 2: Does the current ROI formula correctly score early-expansion targets?

**Question**: Is the existing `_roi` function biased toward expensive neutrals?

**Finding**: The `_roi` formula is:
```
(production²) × max(1, 100−travel) / max(1, ships + production×travel + 1)
```
This is actually reasonable — it penalizes planets that grow during transit (larger denominator). However, the denominator uses `t.production * travel` assuming the neutral GROWS while the fleet is in transit. But fleet sizing uses only `t.ships + 1`. This is inconsistent:
- If neutrals grow: fleet size is under-estimated → fleet may fail to capture
- If neutrals don't grow: ROI denominator over-penalizes (treating it as harder than it is)

From replay data: Planet 11 had 18 ships at step 6, and was captured by P1 with 19 ships. No evidence neutrals grew during those ~9 steps. This suggests neutrals do NOT grow while neutral.

**Decision**: ROI formula's `production * travel` term in the denominator inflates apparent capture cost for neutrals, biasing the score slightly in favor of high-growth/low-ships planets. For the affordability-fallback experiment, keep ROI formula unchanged. Add a secondary experiment with a simpler "growth-efficiency" scoring: `production / ships` (ignoring transit, since neutrals appear static).

**Rationale**: Separate the two concerns — fix the dispatch bug first (Experiment A), then evaluate ROI formula tuning (Experiment B). This allows isolating which change drives improvement.

**Alternatives considered**:
- Replace ROI entirely with `growth_rate / capture_cost`: simpler but ignores travel distance
- Fix the fleet sizing to account for growth: conservative, but may over-send ships and stall parallel expansion

---

## Decision 3: Should the agent send multiple fleets simultaneously?

**Question**: P1 dispatched second fleet at step 14 (8 steps after first). Should P0 also pursue parallel expansion?

**Finding**: The current agent already loops over all planets and can dispatch from multiple sources in one turn. The constraint is the garrison floor. In the early game with only one owned planet, the agent can only send one fleet per turn from the home planet. After capturing the first neutral (step ~15), P0 could immediately dispatch to a second target from either the home planet or the newly captured one.

The current agent evaluates all targets each turn. If it had dispatched to Planet 8 at step 6, by step 15 (when planet 8 is captured) the home planet would have ~24 + 9×1.69 ≈ 39 ships, enough to dispatch to planet 16 (needs 31). This cascade effect may naturally produce parallel expansion once the fallback fix is applied.

**Decision**: Do not add an explicit multi-target rush mechanic. Instead, verify that the affordability fallback (Experiment A) naturally enables faster parallel expansion. Add this as a measurement criterion.

**Alternatives considered**:
- Explicit "rush" mode that always dispatches to 2 targets in first 30 steps: more aggressive but harder to tune
- Minimum-viable fleet sizing based on neutral static ships: already effectively implemented (`t.ships + 1`), and neutrals appear not to grow

---

## Decision 4: Experiment evaluation methodology

**Question**: How many games and which opponent to evaluate against?

**Finding**: The spec requires ≥50 games against agent_v57. The eval harness (`eval.py`) supports `--jobs N` for parallel game execution. A 50-game run takes ~2 minutes with 4 parallel jobs. Statistical significance: at 50 games, a 5 percentage point improvement has ~30% power (underpowered). At 100 games it improves to ~50%. The constitution requires only ≥20 games for the "beat or tie" gate.

**Decision**: Run 50 games for initial validation; run 100 games for any variant that shows >3pp improvement over baseline, before considering submission.

**Rationale**: 50 games is fast enough for iteration. 100 games gives better confidence before investing in a Kaggle submission, aligning with the constitution's 95% confidence gate (Principle VII).

**Alternatives considered**:
- 200 games (same as v57 vs v56 evaluation): too slow for iterative experimentation
- 20 games only: meets constitution minimum but has high variance

---

## Summary

| Experiment | Root change | Hypothesis | Addresses |
|---|---|---|---|
| A: Affordability fallback | If best ROI target unaffordable, try next-best affordable candidate | Eliminates 6-step dispatch delay | Root cause |
| B: Growth-efficiency scoring | Replace ROI formula with `production/ships` for neutrals | Prefers cheap high-growth planets earlier | Scoring bias |
| C: A+B combined | Both fallback and simplified scoring | Synergistic improvement | Both |
| D: Measure parallel expansion | Count planets owned at step 25 for winning variants | Verify cascade effect | Validation |
