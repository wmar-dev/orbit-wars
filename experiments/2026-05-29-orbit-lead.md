# Experiment: Orbit-Lead Targeting (US1)

**Date**: 2026-05-29
**Agent**: agent_v4.py
**Hypothesis**: Predicting where orbiting planets will be when a fleet arrives — rather than targeting their current position — should close more captures and improve win rate against the sun-aware baseline (agent_v3).

## Change Description

Added `_predict_planet_pos(planet, initial_planets_map, angular_velocity, travel_turns)` helper that:
1. Looks up the planet's position at game start from `initial_planets`.
2. Computes `orbital_radius = hypot(ip.x - 50, ip.y - 50)`.
3. Returns current position unchanged if `orbital_radius + planet.radius >= 50` (static planet).
4. Otherwise, projects `theta_pred = atan2(y-50, x-50) + angular_velocity * travel_turns` and returns `(50 + r·cos(θ_pred), 50 + r·sin(θ_pred))`.

In the targeting loop, `travel_turns = dist / fleet_speed(mine.ships + 1)` is computed before prediction. The predicted position is used for both the sun-avoidance segment check and the fleet heading angle.

## Self-Play Result

| Metric | Value |
|--------|-------|
| agent_v4 wins | 17 / 20 |
| agent_v3 wins | 3 / 20 |
| Draws | 0 |
| Win rate (agent_v4) | **85.0%** |
| Threshold | ≥55% (11+ wins) |
| Result | **PASS** |

## SC-3 Regression (sun-avoidance)

`uv run python eval.py --agent0 agent_v4.py --agent1 main.py --games 3 --verbose` — no fleets dispatched through sun exclusion zone. Sun-avoidance filter intact.

## Conclusion

Orbit-lead prediction is a strong improvement: 85% win rate vs agent_v3, far above the 55% threshold. The main gain comes from avoiding premature fleet dispatch to where orbiting planets *were* vs. where they *will be*. This mechanic is validated for inclusion in the combined agent.
