# Candidate S: Cross-Turn Fleet Deduplication (agent_v34)

**Date**: 2026-05-30 | **Branch**: 010-agent-experiments-round-3

## Hypothesis

agent_v33's single-sender coordination (Candidate D) prevents two planets from sending to the same target in the same turn, but does not prevent cross-turn redundancy: if planet A dispatched a fleet to target T five turns ago and the fleet hasn't arrived yet, the best-sender calculation may designate planet B to also send to T this turn. The result is two fleets funding the same target — one of which is wasted. Detecting friendly in-transit fleets via `obs.fleets` angle-matching and deducting their ships from the needed count should eliminate this waste, freeing ships for a second concurrent capture.

## Change

Built on agent_v33:
1. Add `ANGLE_EPSILON = 0.1` (radians, ≈5.7°) — match threshold for angle-based fleet inference
2. Parse `obs.fleets` (new access) to build `in_transit` dict: for each friendly fleet, angle-match it to the closest target whose predicted position is within ANGLE_EPSILON of the fleet's heading; accumulate `in_transit[target_id] += fleet.ships`
3. Replace `ships_needed = best_target.ships + 1` with `ships_needed = max(1, best_target.ships + 1 - in_transit.get(best_target.id, 0))`
4. Skip dispatch if `ships_needed <= 0` (target already fully funded by in-transit fleets)

## Self-play result (2-player)

50 games vs agent_v33 (seeds 0–49):

- agent_v34 wins: 2
- agent_v33 wins: 48
- Draws: 0
- **Score: 4.0%**
- Pass threshold: ≥55% — **FAIL**

## Conclusion

**FAIL** — 4% score (2/50 wins). The angle-based deduplication (ANGLE_EPSILON=0.1 rad) is too aggressive: it incorrectly matches friendly fleets in transit to unrelated nearby targets (especially at the start of games when planets are densely clustered), causing the agent to skip dispatches it should make. The result is a passive agent that holds back ships while agent_v33 expands freely. Root cause: without a destination field in obs.fleets, the angle-matching at 0.1 rad produces too many false positives. A wider threshold would cause more false positives; a narrower threshold would miss true positives due to orbital drift. The angle-inference approach is fundamentally unreliable for this mechanic without destination info.
