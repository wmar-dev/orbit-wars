# Combined Agent: agent_v20

**Date**: 2026-05-30 | **Branch**: 006-agent-experiments-round-2

## Stacked mechanics

Only mechanics that passed ≥55% win rate vs agent_v15 were stacked:

| Mechanic | Agent | Win rate vs v15 | Included? |
|----------|-------|-----------------|-----------|
| Speed-corrected orbit lead | agent_v16 | 70% | **Yes** |
| Transit-adjusted fleet sizing | agent_v17 | 15% | No |
| Adaptive range expansion | agent_v18 | 0% | No |
| Capture-ROI scoring | agent_v19 | 60% | **Yes** |

agent_v20 = agent_v15 + speed-corrected orbit lead (E) + capture-ROI scoring (H).

## Self-play result

20 games vs agent_v15 (20 games):

- agent_v20 wins: 15
- agent_v15 wins: 5
- Draws: 0
- **Win rate: 75%**

Exceeds the ≥65% combined-agent target (SC-003).

## Diagnostic results

Run: `diagnose_v9.py --agent agent_v20.py --games 20`

- Total launches: 20,832
- Captured: 10,862 (52.1%)
- Transit losses: 9,053 (43.5%) — includes misses, combat losses, target already captured
- Unknown: 917 (4.4%)
- **Sun losses: 0** (`_path_safe()` full-ray sun check unchanged; no launches aimed into sun exclusion path)
- **OOB losses: 0** (`_path_safe()` OOB guard unchanged)

All safety guards intact (SC-004).

## Conclusion

**PASS** — agent_v20 achieves 75% win rate vs agent_v15 with two stacked mechanics and zero safety regressions.

The combination of accurate orbit-lead targeting (E) and ROI-based target selection (H) compounds the individual improvements: E ensures fleets hit orbiting targets by computing the correct travel time per fleet size, while H ensures the right targets are chosen by weighing capture cost against remaining production value. Zero draws in 20 games confirms decisive outcomes every game.
