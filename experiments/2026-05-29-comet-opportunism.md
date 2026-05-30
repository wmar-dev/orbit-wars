# Experiment: Comet Opportunism (US2)

**Date**: 2026-05-29
**Agent**: agent_v5.py
**Hypothesis**: Using precomputed comet path data to predict where comets will be when a fleet arrives — and handling comet lifecycle (departing/evacuating sources) — should allow the agent to capture comets more reliably and avoid losing ships on comets that depart.

## Change Description

Added `_build_comet_path_lookup(obs)` that builds `{planet_id: (path_list, path_index, remaining_steps)}` from `obs.comets`.

In the targeting loop:
- For comet targets: compute `future_idx = int(path_index + travel_turns)`. Skip if `future_idx + 5 >= len(path)` (5-turn expiry buffer). Otherwise use `path[future_idx]` as predicted position.
- For non-comet targets: use current `(t.x, t.y)` unchanged.

Owned comet lifecycle handling:
- `remaining_steps == 0` (departing this turn): skip as dispatch source entirely.
- `remaining_steps == 1` (evacuating next turn): override to dispatch ALL ships to best sun-safe target regardless of normal affordability check.

## Self-Play Result

| Metric | Value |
|--------|-------|
| agent_v5 wins | 11 / 20 |
| agent_v3 wins | 9 / 20 |
| Draws | 0 |
| Win rate (agent_v5) | **55.0%** |
| Threshold | ≥55% (11+ wins) |
| Result | **PASS** (exactly at threshold) |

## SC-3 Regression (sun-avoidance)

`uv run python eval.py --agent0 agent_v5.py --agent1 main.py --games 3 --verbose` — no fleets dispatched through sun exclusion zone. Sun-avoidance filter intact.

## Conclusion

Comet opportunism passes at exactly the 55% threshold (11/20). The improvement is narrow — comet capture opportunities are relatively rare per game and comets are often not high-production targets. The evacuate-next-turn logic prevents ship loss on expiring comets. This mechanic is validated for inclusion in the combined agent, though its marginal gain is small.
