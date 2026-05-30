# Combined Agent: agent_v15

**Date**: 2026-05-30 | **Branch**: 005-agent-improvement-experiments

## Stacked mechanics

Only mechanics that passed ≥55% win rate vs agent_v10 were stacked:

| Mechanic | Agent | Win rate vs v10 | Included? |
|----------|-------|-----------------|-----------|
| Redundant fleet avoidance | agent_v11 | 10% | No |
| Garrison sizing | agent_v12 | 0% | No |
| Threat-aware defense | agent_v13 | 10% | No |
| Single-sender coordination | agent_v14 | 70% | **Yes** |

agent_v15 = agent_v10 + single-sender coordination (Candidate D only).

## Self-play result

20 games vs agent_v10 (seeds 0–19):

- agent_v15 wins: 14
- agent_v10 wins: 6
- Draws: 0
- **Win rate: 70%**

Exceeds the ≥65% combined-agent target (SC-003).

## Diagnostic results

Run: `diagnose_v9.py --agent agent_v15.py --games 20`

- Total launches: 18,802
- Sun losses: **0**
- OOB losses: **0**
- All safety guards intact (SC-004)

## Conclusion

**PASS** — agent_v15 achieves 70% win rate vs agent_v10 with zero safety regressions.

Since only one mechanic passed (Candidate D — single-sender coordination), agent_v15 is functionally identical to agent_v14. The result confirms that the single-sender mechanic is the dominant improvement, and its effect holds when formalized as the combined agent baseline.

The T030 subset test is not needed — there are no multi-mechanic regressions to isolate when only one mechanic was stacked.
