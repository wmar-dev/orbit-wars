# Candidate J: Smooth Adaptive Range (agent_v22)

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

Candidate G (0% win rate, 47.5% score vs agent_v15) used hard step-function thresholds for range adaptation that caused extreme contraction when losing (RANGE_FACTOR dropped to 1.5 at ratio ≤ 0.7), preventing the agent from reaching any targets. The mechanic was essentially neutral (19/20 draws) but not beneficial. A power-law formula `2.0 * ratio**0.25` achieves the same winning-state expansion but with a much gentler losing-state response: at ratio=0.5 (badly losing), range_factor ≈ 1.68 (mild contraction vs 1.5 hard floor). At ratio=2.0 (winning), range_factor ≈ 2.38 (meaningful expansion). Expected improvement: ≥55% score vs agent_v20.

## Change

Built on agent_v20. Replace the module-level `RANGE_FACTOR = 2.0` constant with a per-turn dynamic computation inside `agent()`:

```python
own_total = sum(p.ships for p in my_planets)
enemy_total = sum(p.ships for p in planets if p.owner != player and p.owner != -1)
range_factor = max(1.5, min(3.5, 2.0 * (own_total / max(1, enemy_total)) ** 0.25))
```

The existing `nearest_dist * RANGE_FACTOR` is replaced with `nearest_dist * range_factor`. All other logic unchanged.

## Self-play result

20 games vs agent_v20 (seeds 0–19):

- agent_v22 wins: 0
- agent_v20 wins: 0
- Draws: 20
- **Win rate: 0%**
- **Score: 50%**
- Pass threshold: ≥55% score

## Conclusion

**FAIL** — 50% score (20 draws) is just below the 55% threshold.

Root cause: At ratio≈1.0 (symmetric early game), `2.0 * 1.0**0.25 = 2.0` exactly, matching agent_v20's fixed RANGE_FACTOR. Both agents make identical decisions throughout the game, producing draws. The power-law formula only differentiates when one agent pulls decisively ahead — but by then the symmetric decisions leading up to that point prevent either from pulling ahead. This is the same self-play symmetry phenomenon as Candidate G (19 draws, 47.5% score).

Score of 50% vs agent_v20 mirror is mathematically correct: identical agents always draw (50% score in expectation).

This mechanic is neutral in symmetric self-play. It may have asymmetric value against a fixed-range opponent but cannot demonstrate it against agent_v20. This mechanic will NOT be included in agent_v25.
