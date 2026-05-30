# Combined Agent: agent_v30

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

Stack all Round 4 mechanics that individually passed ≥55% score vs agent_v20:
- **Candidate O** (lower garrison floor, 55%): GARRISON_FLOOR_FACTOR = 3 instead of 5
- **Candidate Q** (no range limit, 70%): remove distance cap on candidate targets

Combined, these mechanics should produce a decisive improvement: lower garrison enables faster dispatching while no-range-limit enables attacking globally optimal targets. Both mechanics produce 0 draws in isolation, indicating decisive outcomes. Expected: ≥65% score vs agent_v20.

## Change

Built on agent_v20:
1. `GARRISON_FLOOR_FACTOR = 3` (was 5)
2. Remove `max_range = nearest_dist * RANGE_FACTOR` and `dist <= max_range` guard from candidate loop; merge the two loops into one (no range restriction)

## Self-play result (2-player)

20 games vs agent_v20 (seeds 0–19):

- agent_v30 wins: 15
- agent_v20 wins: 5
- Draws: 0
- **Win rate: 75%**
- **Score: 75%**
- Target: ≥65% score — **PASS**

## 4-Player Result

20 games vs 3× random (seeds 0–19):

- Wins (rank 1): 20
- Win rate: 100%
- Average rank: 1.00
- Target: avg rank ≤ 2.0 — **PASS**

## Safety Audit

20 games via diagnose_v9.py (seeds 0–19):

- Sun losses: **0**
- OOB losses: **0**
- Total launches: 22865
- Capture rate: 54.3%
- Transit loss rate: 41.5% (fleets intercepted or reaching wrong position — not a safety issue)
- Requirement: 0 sun/OOB — **PASS**

## Conclusion

**NEW BEST AGENT** — agent_v30 passes all gates:
- ✅ 75% score vs agent_v20 (target ≥65%)
- ✅ 100% 4-player win rate vs random (target avg rank ≤ 2.0)
- ✅ 0 sun losses, 0 OOB losses

Combining Candidate O (lower garrison floor) and Candidate Q (no range limit) produces a decisive improvement over agent_v20. The lower garrison enables more aggressive dispatching; the no-range-limit enables globally optimal targeting. Both mechanics are unconditional (always active), breaking the symmetric-draw pattern that defeated Candidates J, K, and other ratio-gated mechanics.

Agent_v30 is the new local self-play best. It should be evaluated on the Kaggle leaderboard as the next submission candidate.
