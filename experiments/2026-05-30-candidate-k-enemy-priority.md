# Candidate K: Enemy-Territory Priority When Winning (agent_v23)

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

The current ROI formula treats enemy-owned and neutral planets identically. When significantly ahead (own ships ≥ 1.5× enemy ships), capturing enemy production centers directly is more efficient than expanding into neutrals: enemy captures shrink the opponent's production and end the game faster. A 1.5× ROI multiplier for enemy-owned targets, gated on `own_total / enemy_total ≥ 1.5`, should convert winning positions into faster wins. Expected improvement: ≥55% score vs agent_v20.

## Change

Built on agent_v20. Add `_roi_k()` that wraps `_roi()` with a conditional multiplier:

```python
def _roi_k(t, bx, by, mine, own_total, enemy_total, player):
    base = _roi(t, bx, by, mine)
    if t.owner != -1 and t.owner != player and own_total >= 1.5 * max(1, enemy_total):
        return base * 1.5
    return base
```

Replace `_roi()` calls in the candidate scoring loop with `_roi_k()`. Compute `own_total` and `enemy_total` once per turn (enemy_total = ships on opponent-owned planets only, not neutral).

## Self-play result

20 games vs agent_v20 (seeds 0–19):

- agent_v23 wins: 0
- agent_v20 wins: 0
- Draws: 20
- **Win rate: 0%**
- **Score: 50%**
- Pass threshold: ≥55% score

## Conclusion

**FAIL** — 50% score (20 draws) is just below the 55% threshold.

Root cause: The 1.5× multiplier for enemy-owned targets only triggers when `own_total >= 1.5 * enemy_total`. In symmetric self-play, both agents have equal ship counts for most of the game, so the multiplier rarely fires for either agent. When neither triggers, both agents play identically to agent_v20, producing draws.

This is the same structural problem as Candidate J: condition-gated mechanics that don't differentiate at ratio≈1.0 produce identical behavior in symmetric self-play. The mechanic would need to apply even at small ratios (e.g., ratio ≥ 1.05) to create any asymmetry, but such a weak condition might not help in practice.

This mechanic will NOT be included in agent_v25.
