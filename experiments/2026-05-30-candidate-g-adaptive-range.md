# Candidate G: Adaptive Range Expansion (agent_v18)

**Date**: 2026-05-30 | **Branch**: 006-agent-experiments-round-2

## Hypothesis

The current agent uses a fixed `RANGE_FACTOR = 2.0` regardless of game state. When winning decisively (own ships >> enemy ships), the agent leaves distant high-value targets uncontested — missing kill shots. When losing, it overreaches with long-distance attacks that waste ships. Adapting the range factor to the own/enemy ship ratio (expand when winning ≥1.5×, contract when losing ≤0.7×) lets the agent press when ahead and consolidate when behind. Expected improvement: ≥55% win rate vs agent_v15.

## Change

Built on agent_v15. Before the per-planet loop, added:
```
own_ships = sum(p.ships for p in my_planets)
enemy_ships = sum(p.ships for p in planets if p.owner == 1 - player)
ratio = own_ships / max(enemy_ships, 1)
range_factor = 3.5 if ratio >= 1.5 else 1.5 if ratio <= 0.7 else 2.0
```
Replaced `nearest_dist * RANGE_FACTOR` with `nearest_dist * range_factor`. Kept `RANGE_FACTOR = 2.0` constant as the default fallback.

## Self-play result

20 games vs agent_v15 (20 games):

- agent_v18 wins: 0
- agent_v15 wins: 1
- Draws: 19
- **Win rate: 0%**

## Conclusion

**FAIL** — 0% win rate (19 draws, 1 loss) is identical to the self-play baseline pattern.

The adaptive range produces no measurable effect in symmetric self-play. When both agents are agent_v18, both adjust their range in lockstep based on the same game state — if one is "winning" (ratio ≥ 1.5), the other is "losing" (ratio ≤ 0.7), so both expand/contract together and the net tactical effect cancels out. The mechanic may have asymmetric value against a fixed opponent, but it cannot demonstrate that advantage in symmetric self-play. This mechanic will NOT be included in agent_v20.
