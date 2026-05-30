# Data Model: Agent Improvement Experiments — Round 3

**Branch**: `007-more-agent-experiments` | **Date**: 2026-05-30

## Core Game Entities (inherited from engine — read-only)

### Planet

| Field | Type | Notes |
|-------|------|-------|
| id | int | Unique planet identifier |
| owner | int | -1 = neutral, 0–3 = player index |
| ships | int | Current garrison |
| production | int | Ships produced per turn |
| x, y | float | Current position (orbiting) |
| radius | float | Planet radius for collision detection |

### Fleet (obs.fleets — used by Candidate I)

| Field | Type | Notes |
|-------|------|-------|
| owner | int | Player who launched the fleet |
| ships | int | Ship count in this fleet |
| destination | int | Target planet id |
| distance_remaining | float | Distance to target at this turn |

### Comet (obs.comets — inherited from prior agents)

| Field | Type | Notes |
|-------|------|-------|
| planet_ids | list[int] | Planet IDs in this comet group |
| paths | list[list[pos]] | Precomputed positions per planet |
| path_index | int | Current position index |
| remaining_steps | int | Steps until comet departs |

---

## Agent-Internal Entities (computed per turn, not persisted)

### CandidateTarget

Computed inside the agent loop for each source–target pair considered for dispatch.

| Field | Derived from | Used by |
|-------|-------------|---------|
| planet | Planet | All candidates |
| predicted_x, predicted_y | orbit-lead or comet path | All orbit-lead mechanics |
| travel_turns | distance / fleet_speed(ships+1) | Candidates E, H, I, J, K, L |
| roi_score | _roi() with multipliers | Candidates H, K, M, N |
| ships_needed | target.ships + 1 | All |
| affordable (single source) | mine.ships - garrison_floor ≥ ships_needed | Single-sender, Candidate L |

### DefenseTrigger (Candidate I)

Computed before offensive loop.

| Field | Derived from | Notes |
|-------|-------------|-------|
| threatened_planet_id | fleet.destination | Planet that will fall |
| projected_garrison | planet.ships + production × arrival_turns | Garrison at fleet arrival |
| deficit | incoming_fleet.ships - projected_garrison | Ships needed to survive |
| reinforcement_source_id | nearest source with surplus ≥ deficit | Only if source exists |

### OpponentRanking (4-player, Candidates M and N)

| Field | Derived from | Notes |
|-------|-------------|-------|
| player_id | obs.planets owner values | All non-own, non-neutral players |
| total_ships | sum(p.ships for p.owner == player_id) | Current strength proxy |
| rank | sorted by total_ships desc | 1 = strongest opponent |

---

## Experiment Record Schema (experiments/*.md)

Each file follows this structure (inherited from constitution IV):

```markdown
# Experiment: [Candidate Name]
**Date**: YYYY-MM-DD
**Agent**: agent_vN.py
**Baseline**: agent_vM.py

## Hypothesis
[What improvement is expected and why]

## Change
[What was modified vs the baseline agent]

## Self-Play Result (2-player)
Win rate: X% (N games vs baseline)
Pass threshold: ≥55%
Result: PASS / FAIL

## 4-Player Result (if applicable)
Average rank: X.X (N games vs 3× random)
Pass threshold: avg rank ≤ 2.0
Result: PASS / FAIL

## Conclusion
[Did it improve? What was learned? Keep or discard?]
```

---

## Agent Versioning Scheme

| Range | Round | Baseline | Notes |
|-------|-------|----------|-------|
| v2–v8 | 0 | main.py | Early heuristic development |
| v9–v10 | 003–004 | v8 | Safety fixes |
| v11–v15 | 005 | v10 | Round 1 experiments |
| v16–v20 | 006 | v15 | Round 2 experiments |
| **v21–v25** | **007** | **v20** | **Round 3 experiments (this feature)** |
| v26–v30 | 007+ | v25 (or v20 if v25 fails) | Future rounds if needed |
