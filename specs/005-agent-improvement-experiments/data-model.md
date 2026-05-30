# Data Model: Agent Improvement Experiments

**Branch**: `005-agent-improvement-experiments` | **Date**: 2026-05-30

This document describes the entities, state, and behavioral contracts for the agent_v11–v15 series. These agents are pure Python scripts with no persistent state between turns — all data is derived from the game observation each turn.

---

## Core Entities (from game engine, read-only)

### Planet

| Field | Type | Description |
| ----- | ---- | ----------- |
| `x`, `y` | float | Board position (0–100) |
| `ships` | int | Current ship count |
| `production` | int | Ships produced per turn |
| `owner` | int | 0 = neutral, 1 = player, 2 = opponent |
| `radius` | float | Physical radius (used for obstruction checks) |

### Fleet (in-flight)

| Field | Type | Description |
| ----- | ---- | ----------- |
| `x`, `y` | float | Current position |
| `ships` | int | Ships in fleet |
| `owner` | int | 1 = friendly, 2 = enemy |
| `source` | Planet | Origin planet |
| `destination` | Planet | Target planet |

### Observation

| Field | Type | Description |
| ----- | ---- | ----------- |
| `planets` | list[Planet] | All planets this turn |
| `fleets` | list[Fleet] | All in-flight fleets this turn |
| `step` | int | Current turn number |

---

## Derived State (computed per turn in agents)

These are not persisted — recomputed each call to the agent function.

### en_route_coverage (Candidate A)

```
en_route_coverage[target_planet] = sum of ships in all friendly fleets
                                   whose destination == target_planet
```

A target is considered **covered** when `en_route_coverage[target] >= target.ships + 1`.

### garrison_floor (Candidate B)

```
garrison_floor[planet] = max(production × N, fixed_floor)
```

Where N is the winning sub-experiment value (5, 10, or fixed). Ensures a source planet never drops below this count after a launch.

**available_surplus**:

```
available_surplus[planet] = max(0, planet.ships - garrison_floor[planet])
```

A planet with `available_surplus == 0` cannot launch.

### threat_level (Candidate C)

```
threat_level[owned_planet] = sum of ships in enemy fleets
                              whose destination == owned_planet
```

Defense triggers when: `threat_level[planet] > planet.ships + planet.production × 5`

**reinforcement_target**: The owned planet with the largest `threat_level − (garrison + production × 5)` deficit, if any exceed the threshold. At most one reinforcement dispatch per threatened planet per turn.

### sender_efficiency (Candidate D)

```
sender_efficiency[source][target] = distance(source, target) / available_surplus[source]
```

For each target, only the source with the minimum `sender_efficiency` value may launch. Sources with `available_surplus == 0` are excluded.

---

## Behavioral Contracts

### Fleet size formula

All agents v11–v15 send at most:

```
send_count = min(target.ships + 1, available_surplus[source])
```

A launch is skipped entirely if `send_count <= 0`.

### Safety invariants (inherited from agent_v10, never weakened)

1. `_path_safe(source, target, planets)` returns False if the flight path passes within `planet.radius + PLANET_MARGIN` of any non-source, non-target planet.
2. `_path_safe` also returns False if the ray from source to board edge passes within `SUN_EXCLUSION = 12.0` of the sun.
3. Target aim point uses one iteration of orbit-lead refinement (predict at t0, recompute at t1).
4. Comet `future_idx` is clamped to `len(path) - 1`; empty-path guard prevents index errors.

### Agent docstring requirement (FR-008)

Each agent file begins with a docstring listing:
- Which mechanics it adds
- Which prior agent(s) it builds on
- Evaluation result (filled in after eval run)

---

## Experiment Record Schema

Each file in `experiments/` follows this structure (constitution §Experiment & Documentation Discipline):

| Field | Required | Description |
| ----- | -------- | ----------- |
| `Hypothesis` | Yes | Expected improvement and rationale |
| `Change` | Yes | What was modified vs the base agent |
| `Self-play result` | Yes | Win rate vs agent_v10 over ≥20 games |
| `Conclusion` | Yes | Pass/fail, lessons learned, keep or discard |

Experiment records for candidates A–D are created **before** the agent files are written (FR-001).
