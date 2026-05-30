# Candidate I Retest — 009-fix-comet-fleet-targeting

**Date**: 2026-05-30

## Hypothesis

Candidate I (reactive defense dispatch, 5% score vs v20 — FAIL) sends reinforcements to
owned planets that are certain to fall to incoming enemy fleets. With v32's better baseline
and more accurate targeting, defense dispatches might be more precise and the surplus ships
more available.

## Change vs agent_v32

Before the single-sender offense loop, scans enemy fleets using angle alignment (dot product
> 0.95) to infer destination. For each certain-loss scenario (projected garrison < incoming
fleet), dispatches a reinforcement from the nearest source with sufficient surplus.
Defense sources are excluded from offensive dispatch that turn.

## Self-Play Result (50 games, agent0=cand_I, agent1=agent_v32)

- Agent0 wins: 8
- Agent1 wins: 42
- Draws: 0
- Win rate: **16.0%** (draws count as losses)
- Score: **16.0%** (draws count as 0.5)
- Mean reward delta (cand_I - v32): **-0.0893**

## Conclusion

**FAIL** — 16% score and -0.0893 reward delta. Worst mechanic of this round. The defense
dispatch fires on enemy fleets aimed at neutral or other enemy planets (angle alignment is
not precise enough to distinguish destinations), triggering unnecessary reinforcements. When
defense fires, the reinforcing source skips offense, starving attack capacity. The reward
delta of -0.0893 (largest negative in this round) confirms defensive dispatches cost far
more in missed captures than they save in planets. This mechanic will NOT be included in
agent_v33. Conclusion consistent with prior round (5% vs v20).
