# Candidate F: Transit-Adjusted Fleet Sizing (agent_v17)

**Date**: 2026-05-30 | **Branch**: 006-agent-experiments-round-2

## Hypothesis

Planets produce ships every turn during fleet transit. The current agent sends `target.ships + 1` based on the planet's ship count at launch time, but does not account for garrison growth during the trip. For example, if a target has 10 ships and production 3, and travel takes 12 turns, the garrison will have grown to ~46 ships by arrival — the fleet of 11 ships loses the engagement silently, wasting ships. Adjusting the fleet size to `target.ships + target.production × travel_turns + 1` prevents failed captures. Expected improvement: ≥55% win rate vs agent_v15.

## Change

Built on agent_v15. After selecting `best_target` and computing orbit-lead position `(bx, by)`, added:
```
travel_turns = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(best_target.ships + 1)
ships_needed = int(best_target.ships + best_target.production * travel_turns + 1)
```
The existing skip condition `if mine.ships < ships_needed` naturally enforces "skip if can't afford adjusted amount."

## Self-play result

20 games vs agent_v15 (20 games):

- agent_v17 wins: 3
- agent_v15 wins: 17
- Draws: 0
- **Win rate: 15%**

## Conclusion

**FAIL** — 15% win rate is well below the 55% threshold.

The transit-adjusted sizing replicates the starvation pattern seen in Candidate B (garrison sizing, 0% vs v10): when the required send exceeds the source planet's ships (which happens frequently for distant or high-production targets), the agent skips the target. This effectively reduces offensive throughput, allowing agent_v15 to capture more planets per turn and snowball a decisive lead. The mechanic is correct in theory but the skip-if-insufficient policy is too aggressive — it blocks too many attacks. This mechanic will NOT be included in agent_v20.
