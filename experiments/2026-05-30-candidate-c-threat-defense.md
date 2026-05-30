# Candidate C: Threat-Aware Defense (agent_v13)

**Date**: 2026-05-30 | **Branch**: 005-agent-improvement-experiments

## Hypothesis

Using a narrow `incoming > garrison + production × 5` trigger for defensive reinforcements avoids the over-defense trap that degraded agent_v6 (documented in `experiments/2026-05-29-defensive-reinforce.md`). Only dispatch reinforcements when the threat genuinely exceeds a planet's ability to self-recover in ~5 turns. Expected improvement: ≥55% win rate vs agent_v10.

## Change

Built on agent_v10. At turn start, compute `threat[p] = sum(enemy fleet ships destined for p)` for each owned planet. If `threat[p] > p.ships + p.production * 5`, dispatch reinforcement from the closest owned planet with surplus ships (`source.ships - garrison_floor > 0`). Cap: one dispatch per threatened planet per turn. Offensive logic is unchanged.

## Self-play result

20 games vs agent_v10 (seeds 0–19):

- agent_v13 wins: 2
- agent_v10 wins: 1
- Draws: 17
- **Win rate: 10%**

(Identical pattern to agent_v10 self-play baseline — all draws, same win distribution)

## Conclusion

**FAIL** — 10% win rate is below the 55% threshold.

The threat-aware defense mechanic produces results identical to the baseline self-play, meaning no meaningful effect. In typical game positions the `production × 5` trigger is either never reached (enemy threats rarely exceed this buffer early game) or reached too rarely to change outcomes. The defense source exclusion from offensive play may slightly reduce offense in the rare cases defense fires.

The mechanic correctly avoids agent_v6's over-defense trap, but provides no measurable positive effect against agent_v10. This mechanic will NOT be included in agent_v15.
