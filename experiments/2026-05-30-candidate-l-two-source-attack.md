# Candidate L: Two-Source Coordinated Attack (agent_v24)

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

Single-sender coordination (Candidate D, the core of agent_v15/v20) assigns one source per target and permanently skips targets no single source can afford after its garrison floor. Large enemy strongholds are therefore indefinitely unreachable. A fallback that allows exactly 2 planets to jointly attack — each sending `ceil(needed/2)` ships — should flip high-value targets that single-sender cannot reach, turning stalemates into captures. Expected improvement: ≥55% score vs agent_v20.

## Change

Built on agent_v20. After the main single-sender offense loop completes, add a two-source fallback:

1. Collect targets that were skipped because no single source could afford them (all sources had `surplus < target.ships + 1`).
2. Among skipped targets, find the one with the highest ROI score.
3. Find the top-2 owned planets by surplus.
4. If `source1.surplus + source2.surplus >= target.ships + 1` and both are within `range_factor * nearest_dist` of the target:
   - Send `ceil(needed/2)` from each source, aimed at the orbit-lead predicted position.
5. Single-sender assignments for affordable targets are not affected.

## Self-play result

20 games vs agent_v20 (seeds 0–19):

- agent_v24 wins: 8
- agent_v20 wins: 12
- Draws: 0
- **Win rate: 40%**
- **Score: 40%**
- Pass threshold: ≥55% score

## Conclusion

**FAIL** — 40% score is below the 55% threshold.

The two-source fallback hurt performance. Root causes:
- The fallback activates even when the best single-source assignment already covered all affordable targets. When two sources gang up on one target, both are unavailable for other individual attacks that turn.
- `ceil(needed/2)` splitting may send the wrong amount — if needed=11, source1 sends 6 and source2 sends 5, total=11. But source2 sending 5 might leave it unable to handle its own garrison floor afterward.
- The fallback selection logic (sort by surplus, take top-2) doesn't account for the fact that both sources might already have been the best senders for different, equally valuable targets. Combining them on one target abandons those other attacks.
- The interaction with dispatched_this_turn tracking means that sources already dispatched offensively via single-sender are correctly excluded, but "available" sources that aren't dispatched may be the wrong choice for a joint attack.

This mechanic will NOT be included in agent_v25.
