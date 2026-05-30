# Candidate N: 4-Player Focus-Fire on Leading Opponent (agent_v25 only)

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

In 4-player games, allowing the leading opponent to snowball unchecked results in a runaway win. Directing a portion of offensive pressure toward the leading opponent's planets — specifically a 1.3× ROI multiplier for their owned targets — disrupts their growth without committing to a full binary conflict. In 2-player this is equivalent to Candidate K (there is only one opponent, they are always the "leader"). This mechanic is 4-player only and will be gated by player count in agent_v25.

## Change

4-player gated. In `agent_v25`, identify the leading opponent:

```python
leading_opponent = max(other_player_ids, key=lambda pid: sum(p.ships for p in planets if p.owner == pid))
```

Apply `focus_multiplier = 1.3` to ROI score for any target with `t.owner == leading_opponent`. Combined with Candidate M: trailing agents prefer neutrals (M), non-trailing agents prefer the leader's planets (N). Not tested in isolation (4P mechanic). Evaluated as part of agent_v25 combined via `eval4.py`.

## 4-Player Result

<!-- To be filled in after eval4.py run -->
- Average rank vs 3× random:
- Pass threshold: avg rank ≤ 2.0

## Conclusion

<!-- To be filled in after eval -->
