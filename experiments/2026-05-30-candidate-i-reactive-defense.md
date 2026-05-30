# Candidate I: Reactive Defense Dispatch (agent_v21)

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

Agent_v20 never defends. When an enemy fleet is en route to an owned planet that cannot survive the attack (projected garrison at arrival < incoming fleet size), the planet is lost without resistance. A targeted dispatch — reinforcing only planets that will definitely fall, only from sources with sufficient surplus — should save ships that are otherwise lost and convert planet losses into holds. This differs from the broad Candidate C (10% vs v10) which defended any threat; Candidate I only fires on certain-loss scenarios and only when a reinforcing source exists.

## Change

Built on agent_v20. Before the per-planet offensive loop, scan `obs.get("fleets", [])` for enemy fleets. For each enemy fleet, infer its target by checking alignment (`dot product > 0.95`) with each owned planet. If the fleet will arrive before the planet can survive (`projected_garrison = planet.ships + planet.production * arrival_turns < fleet.ships`), find the nearest owned source with `surplus = source.ships - garrison_floor(source) >= deficit`. Dispatch reinforcement from that source and mark it as reinforcing (skip its offensive dispatch this turn). Uses `fleet_speed(fleet.ships)` for arrival time estimation.

Fleet tuple format: `[id, owner, x, y, angle, from_planet_id, ships]`

## Self-play result

20 games vs agent_v20 (seeds 0–19):

- agent_v21 wins: 1
- agent_v20 wins: 19
- Draws: 0
- **Win rate: 5%**
- **Score: 5%**
- Pass threshold: ≥55% score

## Conclusion

**FAIL** — 5% score is far below the 55% threshold.

The defense dispatch actively hurts performance. Root cause analysis:
- The angle-alignment fleet detection (dot product > 0.95) may trigger on enemy fleets aimed at neutral planets that happen to lie near the direction to an owned planet. This causes unnecessary reinforcements.
- When defense fires, the reinforcing source is excluded from offensive dispatch. If defense triggers frequently, multiple owned planets stop attacking, starving offense.
- In 2-player games, the enemy launches fleets every turn. The defender may be reacting to most enemy fleets, even those that weren't threats.
- Reinforcing a planet that would have survived anyway wastes ships and turns.

This mechanic will NOT be included in agent_v25 or any combined agent. A more precise implementation would require knowing fleet destination directly (not inferred from angle), which the engine does not expose.
