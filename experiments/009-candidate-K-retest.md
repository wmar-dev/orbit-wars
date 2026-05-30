# Candidate K Retest — 009-fix-comet-fleet-targeting

**Date**: 2026-05-30

## Hypothesis

Candidate K (enemy-territory priority, 50% score vs v20 — 20 draws) adds a 1.5× ROI
multiplier for enemy-owned planets when own_total >= 1.5 * enemy_total. Previously produced
draws because the condition rarely fired in symmetric self-play. With the bug-fixed baseline
v32 (better orbit-lead), position asymmetry may emerge earlier, allowing the multiplier to
fire and differentiate the agents.

## Change vs agent_v32

Added `_roi_k()` that wraps `_roi()` with the conditional 1.5× multiplier for enemy-owned
targets when own_total >= 1.5 * max(1, enemy_total). Replaced `_roi()` call in candidate
scoring with `_roi_k()`. Both own_total and enemy_total computed per-planet-turn.

## Self-Play Result (50 games, agent0=cand_K, agent1=agent_v32)

- Agent0 wins: 0
- Agent1 wins: 0
- Draws: **50**
- Win rate: 0.0% (draws count as losses)
- Score: **50.0%** (draws count as 0.5)
- Mean reward delta (cand_K - v32): **+0.0000**

## Conclusion

**FAIL** — 50% score (50 draws). The identical-draw phenomenon persists. Root cause:
the 1.5× condition requires a decisive positional advantage before it fires. In symmetric
games with matched starting conditions and identical move logic below that threshold, both
agents play identically until the multiplier triggers. Since neither agent gains the edge
to trigger it first, all games end in draws. The reward delta is exactly 0.0000 (identical
decisions throughout). This mechanic will NOT be included in agent_v33.
