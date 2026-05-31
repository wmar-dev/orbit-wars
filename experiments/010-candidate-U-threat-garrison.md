# Candidate U: Threat-Aware Garrison Floor (agent_v36)

**Date**: 2026-05-30 | **Branch**: 010-agent-experiments-round-3

## Hypothesis

agent_v33's garrison floor is `max(GARRISON_FLOOR_FACTOR * production, 1)` — a fixed multiple of production regardless of threat. When an enemy fleet is heading toward an owned planet, the agent may still dispatch offensively from that planet (if it has surplus above the floor), leaving it with fewer ships than the incoming attack. The planet then falls. By raising the garrison floor to `max(3 × production, incoming_enemy_ships)` specifically for threatened planets, the agent withholds ships it needs for defense without adding any new dispatch moves (which failed in Candidate I: reactive defense at 16% vs v20).

## Change

Built on agent_v33:
1. Add `ANGLE_EPSILON = 0.1` (same as Candidate S)
2. Parse `obs.fleets` to build `threat` dict: for each enemy fleet, angle-match it to the closest owned planet; accumulate `threat[owned_planet_id] += fleet.ships`
3. Replace `_garrison_floor(src)` with an inline expression: `max(src.production * GARRISON_FLOOR_FACTOR, threat.get(src.id, 0))`

This is distinct from Candidate I (reactive defense) because it does NOT add any defensive dispatch moves — it only prevents outbound attacks from threatened planets.

## Self-play result (2-player)

50 games vs agent_v33 (seeds 0–49):

- agent_v36 wins: 43
- agent_v33 wins: 7
- Draws: 0
- **Score: 86.0%**
- Pass threshold: ≥55% — **PASS**

## Conclusion

**PASS** — 86% score (43/50 wins). The threat-aware garrison floor is a decisive improvement. By raising the garrison floor to the incoming enemy fleet size on threatened planets, agent_v36 keeps enough ships to survive enemy attacks that agent_v33 would lose. Agent_v33 drains threatened planets offensively (if they have surplus above the 3× production floor), leaving them with too few ships to survive the arriving fleet. Agent_v36 blocks this entirely without adding defensive dispatch overhead. This is the key distinction from Candidate I (reactive defense, 16% vs v20): Candidate I dispatched ships to defend, which consumed attack turns; Candidate U simply withholds attack dispatch from threatened planets, preserving both the planet and the offensive budget. The 86% improvement is the largest of any Round 6 candidate.
