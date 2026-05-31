# Combined Agent: agent_v38 (Round 6)

**Date**: 2026-05-30 | **Branch**: 010-agent-experiments-round-3

## Hypothesis

Only one Round 6 candidate passed ≥55% vs agent_v33:
- **Candidate U** (threat-aware garrison floor, 86%): raise garrison floor to max(3×production, incoming_enemy_ships) for threatened planets

Candidates S (4%), T (0%), and V (50% draws) all failed. Combined agent stacks Candidate U only on agent_v33. Expected: score ≥65% vs agent_v33, consistent with the 86% isolated result (no interaction partners to regress against since U is the only stacked mechanic).

## Change

Built on agent_v33:
- **Candidate U**: parse obs.fleets for enemy fleets, angle-match to owned planets (ANGLE_EPSILON=0.1), raise garrison floor to max(3×production, threat_ships) for threatened planets only

## Self-play result (2-player)

50 games vs agent_v33 (seeds 0–49):

- agent_v38 wins: 43
- agent_v33 wins: 7
- Draws: 0
- **Score: 86.0%**
- Target: ≥65% score — **PASS**

## Safety Audit

50 games via diagnose_v9.py (seeds 0–49):

- Sun losses: **0**
- OOB losses: **0**
- Total launches: 34,231
- Capture rate: 32.9%
- Transit loss rate: 62.2% (fleets intercepted or arriving late — not a safety issue)
- Requirement: 0 sun/OOB — **PASS**

## Conclusion

**NEW BEST AGENT** — agent_v38 passes all gates:
- ✅ 86% score vs agent_v33 (target ≥65%)
- ✅ 0 sun losses, 0 OOB losses

The threat-aware garrison floor (Candidate U) is the sole passing mechanic of Round 6.
It prevents agent_v33's failure mode of draining threatened planets offensively —
the agent now holds garrison on planets facing imminent enemy attack without adding
any defensive dispatch overhead. The 86% result is the largest single-mechanic
improvement since Candidate Q (no range limit, 70% vs v20).

Agent_v38 is the new local self-play best. Promotion complete.
