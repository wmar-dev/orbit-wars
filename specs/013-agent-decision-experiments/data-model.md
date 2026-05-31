# Data Model: Agent Decision Experiments

**Branch**: `013-agent-decision-experiments` | **Date**: 2026-05-31

This feature is a pure experimentation track — no persistent data store, database schema,
or network API. The "data model" here describes the logical entities that structure the
experiment design and the agent's in-turn decision state.

---

## Logical Entities

### ExperimentVariant

Represents one isolated test configuration. Each variant changes exactly one variable from
agent_v38's defaults and is evaluated over 50 games vs agent_v38.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Short code: `013-<experiment>-<n>` (e.g., `013-scoring-2`) |
| `experiment` | enum | `scoring`, `fleet_sizing`, `garrison_floor`, `source_assignment` |
| `base_agent` | string | Always `agent_v38.py` for isolated tests |
| `changed_variable` | string | Human-readable description of the single change |
| `source_file` | string | Python file implementing this variant (e.g., `agent_013_scoring_2.py`) |
| `win_rate` | float | Fraction of 50 games won vs agent_v38 (draws count as 0.5) |
| `planet_count_step100` | float | Average planets controlled at step 100 (secondary metric) |
| `prod_rate_step150` | float | Average production rate at step 150 (secondary metric) |
| `notes` | string | Root cause summary for significant wins/losses |

### ScoringFormula

The function applied per `(source_planet, target_planet)` pair to rank capture candidates.

| Variant | Formula | Constants |
|---------|---------|-----------|
| scoring-1 (baseline) | `prod² × max(1, 100-T) / max(1, ships + prod×T + 1) × blend` | REWARD_ALPHA=0.1 |
| scoring-2 | `prod / (ships + 1)` | none |
| scoring-3 | ROI with gate `dist ≤ nearest_enemy_dist × 1.5` | DIST_FACTOR=1.5 |
| scoring-4 | `0.67 × prod_norm + 0.33 × (1 - dist_norm)` | weights sum to 1.0 |

Where: `T` = estimated travel turns, `prod` = target production, `ships` = target current ships,
`prod_norm` = `prod / map_max_prod`, `dist_norm` = `dist / map_max_dist`.

### FleetSizingPolicy

The function that returns `ships_needed` given source planet, target planet, and context.

| Variant | Formula | Extra inputs |
|---------|---------|-------------|
| fleet-1 (baseline) | `target.ships + 1` | none |
| fleet-2 | `target.ships + 1 + target.production × ceil(travel_turns)` | `travel_turns` from dist/speed |
| fleet-3 | `max(fleet-1, enemy_ships + target_ships_at_arrival + 1)` if race detected | `raw_fleets`, RACE_EPSILON=0.2 |
| fleet-4 | fleet-2 formula, then apply fleet-3 race-aware override on top | both |

Race detection: enemy fleet heading toward same target if angle diff < RACE_EPSILON radians.

### GarrisonFloor

The minimum ships a planet must retain before it can dispatch.

| Variant | Formula | Constants |
|---------|---------|----------|
| floor-1 | `max(1 × prod, threat)` | FACTOR=1 |
| floor-2 | `max(2 × prod, threat)` | FACTOR=2 |
| floor-3 (baseline) | `max(3 × prod, threat)` | FACTOR=3 |
| floor-4 | `max(5 × prod, threat)` | FACTOR=5 |
| floor-5 | `max(dynamic_factor(step) × prod, threat)` | ramp 1→4 over steps 0–300 |

Where `threat = sum of enemy fleet ships whose angle aligns with the planet (ANGLE_EPSILON=0.1 rad)`
(inherited unchanged from Candidate U in agent_v38).

Dynamic factor: `floor_factor(step) = 1 + 3 × min(step / 300.0, 1.0)` → 1.0 at step 0,
4.0 at step 300+.

### SourceAssignmentPolicy

The rule governing which owned planets may dispatch to each target in the same turn.

| Variant | Rule | New constants |
|---------|------|--------------|
| assign-1 (baseline) | Single best sender per target (lowest `dist / surplus`) | none |
| assign-2 | Primary = best sender. Secondary senders: any planet with `surplus > MIN_CONTRIB` may additionally send `MIN_CONTRIB` ships to the highest-priority target. Secondary senders are not exclusive (still dispatch to their own primary target too). | MIN_CONTRIB=10 |
| assign-3 | Top-2 senders: best sender + second-best sender each send `ceil(ships_needed / 2) + 1`. Both must have surplus above garrison floor after their send. | none |

---

## Experiment Record Schema

`experiments/013-agent-decisions.md` contains one table per experiment and a combined
final evaluation table. Fields per row:

| Column | Description |
|--------|-------------|
| Variant | Short code (e.g., `013-scoring-2`) |
| Win Rate | Fraction of 50 games won (0–1, draws = 0.5) |
| Avg Planets @ 100 | Mean planets controlled at step 100 across 50 games |
| Avg Prod @ 150 | Mean production rate at step 150 across 50 games |
| Notes | Key observation explaining the result |

---

## State Transitions (In-Turn Decision Flow)

The agent's decision pipeline within a single turn (unchanged structural flow from v38;
variants inject into specific steps):

```
obs received
    │
    ├── Build planet and fleet data structures
    ├── Build threat dict (enemy fleets → owned planets)    ← GarrisonFloor reads this
    ├── Build comet path lookup
    │
    ├── For each target: find best_sender                   ← SourceAssignmentPolicy
    │       score = dist / surplus (unchanged across assign variants)
    │       assign-2: also identify secondary senders
    │       assign-3: identify top-2 senders
    │
    ├── For each owned planet:
    │       Handle departing/evacuating comets (unchanged)
    │       ├── Compute garrison floor                      ← GarrisonFloor
    │       ├── Check if this planet is assigned as sender
    │       ├── Predict target position (orbit-lead)        ← unchanged
    │       ├── Score candidates                            ← ScoringFormula
    │       ├── Select best target
    │       └── Compute ships_needed                        ← FleetSizingPolicy
    │
    └── Return move list
```

**Interaction notes**:
- ScoringFormula and FleetSizingPolicy operate independently within the per-planet loop.
  They can be combined without conflict.
- GarrisonFloor and SourceAssignmentPolicy interact: the floor check gates whether a
  secondary/top-2 sender can participate. This interaction is intentional and correct
  (garrison safety is enforced regardless of assignment policy).
- No interaction between ScoringFormula and SourceAssignmentPolicy: scoring selects which
  target; assignment determines which planets send to it.
