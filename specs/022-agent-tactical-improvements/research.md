# Research: Agent Tactical Improvements

**Date**: 2026-06-06 | **Branch**: `022-agent-tactical-improvements`

## Finding 1 — Root Cause of Early-Game Divergence

**Source**: Replay analysis (7 games vs slawekbiel, `experiments/2026-06-04-replay-analysis.md`)

**Decision**: Early-game dispatch threshold is the primary cause. Median divergence at turn 8.

**Rationale**: In all 7 analyzed games, the opponent captured a neutral planet 1–3 turns ahead of us. Specifically: our agent had 50+ ships stockpiled at home by turn 8 while the opponent had already secured a second planet and was compounding production. The dispatch loop failed to fire because the garrison floor (`production × gff`) combined with fleet-sizing checks resulted in "ship available but threshold not met" states.

**Root mechanism in code**: In `_greedy_moves`, the main loop requires `mine.ships - floor > 0` (surplus check) then `mine.ships >= ships_needed` (affordability check). In turns 0–10 with `gff=1.0`, these checks should pass. The actual blocker is that our ROI-ranked targeting sends the first fleet to the *best-ROI* neutral (which may be moderately far) rather than the *nearest* neutral. If the best-ROI target requires N ships but the nearest target requires only N/3 ships, the agent waits to accumulate N. Fix: in turns 0–15, prioritize nearest capturable neutral over best-ROI neutral.

**Alternatives considered**:
- Lowering gff globally: risky, increases losses to late-game threats
- Increasing aggressiveness via ROI formula tuning: insufficient, doesn't change the targeting priority

---

## Finding 2 — Garrison Conservatism in the Mid-Game

**Source**: Replay analysis + code review of `agent_v60.py` constants

**Decision**: Cap `gff` at 2.5× instead of 4×; change ramp from `step/300` to `step/400`.

**Rationale**: The formula `gff = 1.0 + 3.0 * min(step / 300.0, 1.0)` reaches its maximum of 4.0 at step 300 — which is only 60% through a 500-turn game. By step 300, the garrison requirement is 4× production, meaning a planet producing 3 ships/turn must hold 12 ships before it dispatches. At that conservatism level, even a medium surplus doesn't trigger a dispatch.

The replay showed dispatches at 0.43/turn in turns 30–50 vs the opponent's 0.92/turn. The gff at step 40 is `1 + 3 * (40/300) = 1.4`, which is mild. The bottleneck at that stage is more likely the ROI threshold and fleet sizing for enemy planets (we compute `ships_needed` with growth during travel, which can be large). But in the late game (step 200+), gff=3.0 is clearly suppressing dispatches.

New formula: `gff = 1.0 + 1.5 * min(step / 400.0, 1.0)` caps at 2.5× at step 400+.

**Alternatives considered**:
- Removing gff scaling entirely: too risky, we lose garrison discipline
- Per-planet threat-conditioned floor: correct but complex; easier to tune the global formula first

---

## Finding 3 — Lookahead Eval Horizon Bias

**Source**: `experiments/2026-06-05-lookahead-search.md` (depth sensitivity study)

**Decision**: Use cumulative production score over the rollout rather than horizon-only sampling.

**Rationale**: The depth sensitivity study showed monotonic degradation beyond depth=10. At depth=10, beam gets 54% vs v58. At depth=15, only 35%. The hypothesis: longer rollouts amplify optimism bias because production accumulates for the agent unchallenged (no opponent model). With cumulative scoring, each step's snapshot is weighted, and the compounding error is smoothed rather than concentrated at the horizon. A planet captured at step 3 contributes 7× its production vs one captured at step 9 — which is the actual economic reality.

**Timing**: Cumulative scoring adds `depth` extra `score()` calls per candidate. At depth=10 and ~15 candidates: 150 extra scoring calls. `score()` is O(planets + fleets) ≈ O(30), so ~4500 extra ops total. Negligible vs the 800ms budget.

**Alternatives considered**:
- Discount factor (future production worth less): principled but adds a hyperparameter to tune
- Horizon-only with threat discount: partial fix, doesn't address the capture-timing blindness
- Keeping depth=10 horizon-only: already done in v60; needed improvement

---

## Finding 4 — Independent Toggle Strategy

**Source**: Prior experiments (v57 variants, v59 variants showed interference effects)

**Decision**: Three independent toggle constants (`EARLY_DISPATCH_ENABLED`, `DYNAMIC_GARRISON_ENABLED`, `WEIGHTED_EVAL_ENABLED`), all `True` by default in the final file but individually set to `False` during A/B evaluation.

**Rationale**: v57 and v59 experiments showed that combining multiple changes before isolating their individual signal can hide regressions. If the combination does worse, it's ambiguous which component hurt. Three 50-game evals (one per direction) plus one 50-game combined eval provides clear attribution.

**Alternatives considered**:
- Single combined implementation: faster to write, impossible to diagnose on failure
- Sequential stacking (add one at a time permanently): accumulates assumptions; can't isolate direction 3's value if direction 2 already changed the baseline
