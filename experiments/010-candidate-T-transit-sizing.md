# Candidate T: Transit-Adjusted Fleet Sizing (agent_v35)

**Date**: 2026-05-30 | **Branch**: 010-agent-experiments-round-3

## Hypothesis

agent_v33 computes `ships_needed = best_target.ships + 1` — the garrison at the time of dispatch plus one. But enemy planets with positive production accumulate ships during fleet transit. For a target with production=3 and travel_time=15 turns, the fleet arrives needing to beat `target.ships + 45` but only has `target.ships + 1` ships — it loses the engagement. Estimating the garrison at arrival time as `target.ships + target.production × travel_turns` and sending enough ships to beat that projection should eliminate losing-on-arrival fleet losses.

## Change

Built on agent_v33:
1. After computing `bx, by` (predicted target position) and `dist = math.hypot(mine.x - bx, mine.y - by)`, compute:
   ```python
   travel_turns = math.ceil(dist / fleet_speed(best_target.ships + 1))
   projected_garrison = int(best_target.ships + best_target.production * travel_turns)
   ships_needed = projected_garrison + 1
   ```
2. Use `ships_needed` from this formula everywhere the original `best_target.ships + 1` was used (affordability check and move dispatch)

One fixed-point iteration only (second iteration changes result by <2 ships for typical cases).

## Self-play result (2-player)

50 games vs agent_v33 (seeds 0–49):

- agent_v35 wins: 0
- agent_v33 wins: 50
- Draws: 0
- **Score: 0.0%**
- Pass threshold: ≥55% — **FAIL**

## Conclusion

**FAIL** — 0% score (0/50 wins). The transit-adjusted sizing drastically over-estimates ships needed, making the agent unable to afford most targets. For a production-3 enemy planet 30 units away (travel_turns ≈ 10), the agent computes `projected_garrison = current_ships + 30` — a fleet that's 30 ships larger than needed. Since agent_v33 uses `ships_needed = target.ships + 1`, v33 captures the target while v35 waits to accumulate the larger fleet. The mechanic's correct assumption (garrison grows during transit) backfires because agent_v33's ROI formula already accounts for garrison growth via `t.ships + t.production * travel` in the denominator — v33's ROI scoring implicitly deprioritizes hard-to-reach growing garrisons. Adding the transit sizing on top makes v35 systematically over-send and lose timing on every target. Not worth retrying with a smaller buffer coefficient since the ROI formula already handles this tradeoff.
