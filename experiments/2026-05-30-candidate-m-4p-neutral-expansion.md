# Candidate M: 4-Player Neutral-First Expansion When Losing (agent_v25 only)

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

In 4-player games, when an agent is the trailing player (fewest total ships among all players), attacking any opponent invites retaliatory attacks from the other two opponents simultaneously. Neutral planet captures are cheap (no retaliation), build production, and avoid triggering multi-opponent responses. Adding a 2× ROI multiplier for neutral planets (owner == -1) when trailing should redirect the agent toward safe expansion rather than suicidal offense. This mechanic is 4-player only and will be gated by player count in agent_v25.

## Change

4-player gated. In `agent_v25`, after detecting player count (`n_opponents = len(other_player_ids) >= 3`):

```python
own_total = sum(p.ships for p in my_planets)
other_totals = {pid: sum(p.ships for p in planets if p.owner == pid) for pid in other_player_ids}
trailing = own_total < min(other_totals.values())
```

When `trailing`, apply `neutral_multiplier = 2.0` to ROI scores for targets with `t.owner == -1`. Not tested in isolation (4P mechanic). Evaluated as part of agent_v25 combined via `eval4.py`.

## 4-Player Result

<!-- To be filled in after eval4.py run -->
- Average rank vs 3× random:
- Pass threshold: avg rank ≤ 2.0

## Conclusion

<!-- To be filled in after eval -->
