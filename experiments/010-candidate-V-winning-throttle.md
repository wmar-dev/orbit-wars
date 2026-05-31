# Candidate V: Winning-State Garrison Reduction (agent_v37)

**Date**: 2026-05-30 | **Branch**: 010-agent-experiments-round-3

## Hypothesis

agent_v33 maintains `GARRISON_FLOOR_FACTOR = 3` (3× production minimum garrison) unconditionally. When the agent has ≥2× more total ships than all enemies combined, this 3× floor is conservative — the agent is winning decisively and doesn't need to hold back 3× production per planet. Reducing the floor to 1× production in this state frees ships for aggressive endgame strikes that close the game faster. The 2:1 threshold is conservative enough to avoid oscillation: a single lost planet won't immediately flip the ratio back below the gate.

## Change

Built on agent_v33:
1. After computing `my_planets` and `planets`, add:
   ```python
   own_total = sum(p.ships for p in my_planets)
   enemy_total = sum(p.ships for p in planets if p.owner not in (-1, player))
   effective_floor_factor = 1 if own_total >= 2.0 * max(enemy_total, 1) else GARRISON_FLOOR_FACTOR
   ```
2. Replace the `GARRISON_FLOOR_FACTOR` used in the garrison floor calculation with `effective_floor_factor` (pass as parameter or inline)

The mechanic is evaluated turn-by-turn — when the ratio falls below 2:1, `effective_floor_factor` reverts to 3 on the next turn.

## Self-play result (2-player)

50 games vs agent_v33 (seeds 0–49):

- agent_v37 wins: 0
- agent_v33 wins: 0
- Draws: 50
- **Score: 50.0%**
- Pass threshold: ≥55% — **FAIL**

## Conclusion

**FAIL** — 50% score (50 draws). Every game ends in a draw because the mechanic never activates: the 2:1 `own_total / enemy_total` threshold requires a decisive lead that never materializes when playing against agent_v33 (a strong opponent with identical base strategy). Both agents expand at the same rate, so neither achieves 2× the other's ship count before game end. When v37 faces v33, the effective_floor_factor remains 3 (the baseline) for the entire game, making v37 and v33 functionally identical — hence all draws. The mechanic is only useful in games where a commanding lead already exists; against an evenly-matched opponent it is inert. Try a lower threshold (1.5×) to activate more often, or apply the reduction to a specific game phase (e.g., turn > 300 only) rather than a ratio gate.
