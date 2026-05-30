# Implementation Plan: Agent Gap Analysis & Improvement Experiments

**Branch**: `003-agent-gap-analysis` | **Date**: 2026-05-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-agent-gap-analysis/spec.md`

## Summary

Implement four isolated experiment agents (v4–v7) each adding one mechanic missing from
agent_v3, evaluate each against agent_v3 over 20 games, then build a combined agent (v8)
stacking all mechanics that individually reach ≥55% win rate. Experiments v4–v7 are fully
independent and can run in parallel.

## Technical Context

**Language/Version**: Python 3.14 (pyproject.toml constraint)

**Primary Dependencies**: `kaggle-environments ≥1.28.0` (already installed); `math` stdlib only

**Storage**: N/A — no persistence; eval results printed to stdout and written to `experiments/`

**Testing**: Manual — `uv run python eval.py --agent0 agent_vN.py --agent1 agent_v3.py --games 20 --jobs 4`

**Target Platform**: Local macOS/Linux dev machine

**Project Type**: CLI / script — single-file agents at project root for Kaggle compatibility

**Performance Goals**: Turn decision <1 second; 20-game eval <60 seconds per pairing with `--jobs 4`

**Constraints**: Pure Python, no external models or network calls; each agent file must be
self-contained at project root

**Scale/Scope**: 4 isolated evals + 1 combined eval = 5 eval runs × 20 games; 5 agent files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Rationale |
| --------- | ------ | --------- |
| I. RL First | ✅ Pass | Rule-based heuristic; explicitly permitted as baseline/opponent seed |
| II. Fair Play | ✅ Pass | All mechanics use only observation fields the engine exposes; no exploits |
| III. Manual Submissions Only | ✅ Pass | No automation; all evaluation is local only |
| IV. Experiment Documentation | ✅ Pass (conditional) | Each experiment MUST have an entry in `experiments/` before any Kaggle submission |
| V. Local Self-Play Eval | ✅ Pass | Spec mandates ≥20-game eval per agent vs agent_v3 before promotion |

**Gate result**: PASS. Experiment log creation is a required deliverable for each agent.

## Project Structure

### Documentation (this feature)

```text
specs/003-agent-gap-analysis/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── agent-interface.md  ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
orbit-wars/
├── main.py              # baseline — do not modify
├── agent_v2.py          # production-weighted — do not modify
├── agent_v3.py          # sun-aware — current best; used as eval baseline — do not modify
├── agent_v4.py          # NEW: orbit-lead targeting (Gap 1)
├── agent_v5.py          # NEW: comet opportunism (Gap 2)
├── agent_v6.py          # NEW: defensive reinforcement (Gap 3)
├── agent_v7.py          # NEW: fleet-speed scoring + fast-fleet send (Gaps 4 & 5)
├── agent_v8.py          # NEW: combined agent (all passing mechanics stacked)
├── eval.py              # existing harness — no changes needed
└── experiments/
    ├── 2026-05-29-orbit-lead.md          # NEW: required before submission
    ├── 2026-05-29-comet-opportunism.md   # NEW: required before submission
    ├── 2026-05-29-defensive-reinforce.md # NEW: required before submission
    ├── 2026-05-29-fleet-speed-scoring.md # NEW: required before submission
    └── 2026-05-29-combined-agent.md      # NEW: required before submission
```

**Structure Decision**: Flat root layout matching existing convention. All agent files at
root for Kaggle submission compatibility.

## Phase 0: Research Findings

See [research.md](research.md) for full findings. Key decisions:

### R-1: Orbit Lead Calculation

**Decision**: Use a single-pass travel-time estimate to compute predicted planet position.

**Method**:

1. Determine if a planet is orbiting: check if its distance from center (50, 50) at game
   start (`initial_planets`) is < 50 - planet_radius. This is the same criterion the engine
   uses (`orbital_radius + planet_radius < 50`).
2. Compute the planet's current angle from center: `θ = atan2(y - 50, x - 50)`.
3. Estimate travel turns: `T = distance_to_current_pos / fleet_speed(ships)`.
4. Predict arrival position: `θ_arrival = θ + angular_velocity × T`. Then:
   - `x_pred = 50 + orbital_radius × cos(θ_arrival)`
   - `y_pred = 50 + orbital_radius × sin(θ_arrival)`
5. Aim fleet at (x_pred, y_pred); apply sun-avoidance filter against this path.

**Iteration note**: The distance used in step 3 is to the *current* position. A more
precise approach would iterate (recompute distance to predicted position, recompute T,
repeat), but one-pass is sufficient for v1 — orbiting planets don't move far in one turn.

**Rationale**: Observation fields `initial_planets` and `angular_velocity` are sufficient.
No additional dependencies needed.

### R-2: Comet Path Prediction

**Decision**: Use `comets[].paths` and `comets[].path_index` to find the comet's predicted
position at fleet arrival time.

**Method**:

1. For each comet ID in `comet_planet_ids`, find its group in `comets[]` (match planet_id
   to `comet_group.planet_ids`).
2. Current position index: `path_index`. Predicted index at arrival: `path_index + T`.
3. If `path_index + T >= len(paths)`: the comet will have left the board — skip it.
4. Otherwise, target `paths[path_index + T]` as the predicted landing position.
5. Aim fleet at predicted position; apply sun-avoidance filter against this path.

**Safety window**: Also skip if `remaining_path = len(paths) - path_index < T + 5`
(5-turn buffer to avoid chasing a comet that departs just before the fleet lands).

### R-3: Defensive Reinforcement

**Decision**: Scan `fleets` each turn for enemy fleets heading toward owned planets;
dispatch reinforcements if the owning planet's neighbor can afford it.

**Method**:

1. For each enemy fleet `f`, estimate arrival turn: `T_arrive = distance(f, planet) / fleet_speed(f.ships)`.
2. Estimate garrison at arrival: `garrison_at_arrival = current_ships + production × T_arrive`.
3. If `f.ships > garrison_at_arrival`: planet is at risk.
4. Find the nearest owned planet (other than the threatened one) with surplus ships.
5. Surplus = `source.ships - source.production × 10` (the dynamic safety threshold from
   the clarification). Only send if surplus > 0.
6. Send `min(surplus, f.ships - garrison_at_arrival + 1)` ships toward the threatened planet.
7. Reinforcement dispatches happen before attack dispatches in the same turn.

**Note on fleet targeting**: A fleet's `angle` and current position can be used to check
if it's heading toward a planet via dot-product alignment (same approach as `eval.py`'s
verbose wrapper). A fleet is "heading toward" planet P if alignment score > 0.95.

### R-4: Fleet-Speed Scoring (Gap 4)

**Decision**: Replace raw distance with estimated travel turns in the scoring denominator.

**Formula**: `score = production / travel_turns` where
`travel_turns = distance / fleet_speed(ships_available)`.

`fleet_speed(n) = 1.0 + 5.0 × (log(n) / log(1000))^1.5`

A large garrison makes far high-production planets more attractive relative to nearby
low-production ones.

### R-5: Minimum Fast-Fleet Send (Gap 5)

**Decision**: Send `max(garrison + 1, MIN_FAST_FLEET)` ships where `MIN_FAST_FLEET = 10`.

A fleet of 10 ships travels at ~2.5 units/turn vs 1.0 for a 1-ship fleet. This avoids
the pathological case of a `garrison + 1 = 1` fleet crawling across the board.

**Cap**: Never send more than `mine.ships // 2` from a single planet in one attack move
(prevents stripping the planet entirely, unless it's a kill-shot scenario).

## Phase 1: Design

See [data-model.md](data-model.md) for entity definitions.
See [contracts/agent-interface.md](contracts/agent-interface.md) for I/O contract.
See [quickstart.md](quickstart.md) for eval commands.

### Core Algorithm Per Agent

#### agent_v4.py — Orbit-Lead Targeting

```python
def _predict_planet_pos(planet, initial_planets_map, angular_velocity, travel_turns):
    """Return (x, y) predicted position for an orbiting planet."""
    ip = initial_planets_map.get(planet.id)
    if ip is None:
        return planet.x, planet.y
    cx, cy = 50.0, 50.0
    orbital_radius = math.hypot(ip.x - cx, ip.y - cy)
    if orbital_radius + planet.radius >= 50.0:
        return planet.x, planet.y  # static planet
    theta = math.atan2(planet.y - cy, planet.x - cx)
    theta_pred = theta + angular_velocity * travel_turns
    return cx + orbital_radius * math.cos(theta_pred), cy + orbital_radius * math.sin(theta_pred)
```

Agent loop change: replace `t.x, t.y` with `predict_planet_pos(t, ...)` before computing
heading angle and sun-avoidance check.

#### agent_v5.py — Comet Opportunism

Additional preprocessing: build `comet_path_map = {planet_id: (group, local_idx)}` from
`obs.comets` and `obs.comet_planet_ids`. In the target-scoring loop, for comet targets,
replace `(t.x, t.y)` with predicted comet position; skip if remaining path < travel_turns + 5.

#### agent_v6.py — Defensive Reinforcement

Pre-pass before attack loop:

```python
SAFETY_MULTIPLIER = 10

for enemy_fleet in enemy_fleets:
    for my_planet in my_planets:
        if _fleet_heading_toward(enemy_fleet, my_planet):
            T = distance(enemy_fleet, my_planet) / fleet_speed(enemy_fleet.ships)
            projected_garrison = my_planet.ships + my_planet.production * T
            if enemy_fleet.ships > projected_garrison:
                # find nearest owned planet with surplus
                ...
                surplus = source.ships - source.production * SAFETY_MULTIPLIER
                if surplus > 0:
                    send = min(surplus, enemy_fleet.ships - projected_garrison + 1)
                    moves.append([source.id, angle_to_threatened, send])
```

#### agent_v7.py — Fleet-Speed Scoring + Fast-Fleet Send

Scoring change: `score = t.production / (distance / fleet_speed(mine.ships) + EPSILON)`

Launch change: `ships_to_send = max(ships_needed, MIN_FAST_FLEET)` where
`MIN_FAST_FLEET = 10`, capped at `min(mine.ships, mine.ships // 2 + ships_needed)`.

#### agent_v8.py — Combined Agent

Stack all mechanics from agents that pass ≥55% win rate. Apply in order:

1. Orbit-lead position prediction (if v4 passes)
2. Comet targets added to candidate list (if v5 passes)
3. Defensive reinforcement pre-pass (if v6 passes)
4. Fleet-speed scoring + fast-fleet send (if v7 passes)

### Parallelism Note (from user input)

Experiments v4–v7 are independent: each is a self-contained agent file that can be
implemented and evaluated simultaneously. Tasks should be structured to allow all four
isolated experiments to proceed in parallel before the combining step.

The eval harness already supports `--jobs N` for parallel game execution within a single
eval run. Use `--jobs 4` for all eval runs.

## Complexity Tracking

No constitution violations requiring justification.
