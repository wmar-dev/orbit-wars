# Implementation Plan: Agent Improvement Experiments — Round 6

**Branch**: `010-agent-experiments-round-3` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-agent-experiments-round-3/spec.md`

## Summary

Run four isolated mechanic experiments (agent_v34–v37) built on agent_v33 (the current best local agent), evaluated over 50 games each vs agent_v33. All passing mechanics (≥55% score) are stacked into a combined agent (agent_v38) and evaluated at ≥65% target. Four failure modes of agent_v33 are targeted: cross-turn fleet over-sending, transit garrison under-estimation, garrison depletion under threat, and slow endgame when winning.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: `kaggle_environments` (game harness), `reward_signal.py` (blended scoring constants). No new dependencies introduced.

**Storage**: Flat files at repo root (`agent_vN.py`), experiment records in `experiments/` (Markdown), evaluation logs in `logs/` (CSV via `diagnose_v9.py`).

**Testing**: `eval.py --agent0 agent_vN.py --agent1 agent_v33.py --games 50 --seed 0` (win rate), `diagnose_v9.py` (safety audit, 0 sun/OOB losses).

**Target Platform**: Local development (macOS), Kaggle submission environment.

**Project Type**: Competitive game agent (heuristic rule-based, single Python function).

**Performance Goals**: ≥55% score vs agent_v33 per candidate (50 games); ≥65% for combined. Actuation time: <1 second/turn (Kaggle actTimeout budget).

**Constraints**: Each agent is a single self-contained `.py` file at repo root. No game engine modifications. No new external imports. All logic in the `agent(obs)` function. `eval.py` and `diagnose_v9.py` are not modified.

**Scale/Scope**: 4 candidate agents + 1 combined agent = 5 new agent files. 50 games × 6 evaluations = 300 evaluation games. Each 50-game run takes ~2–4 minutes locally.

**Key observation schema** (from CONTEST.md):
- `obs.planets` → list of `[id, owner, x, y, radius, ships, production]`
- `obs.fleets` → list of `[id, owner, x, y, angle, from_planet_id, ships]` — **no `to_planet_id`**
- `obs.initial_planets` → list of initial planet states (for orbit-lead)
- `obs.angular_velocity` → float (radians/turn)
- `obs.comets` → list with `paths` and `path_index` (for comet intercept)

**Critical constraint for Candidate S**: Friendly fleets in `obs.fleets` have NO destination field. Cross-turn target deduplication requires angle-based trajectory inference (project fleet position forward at fleet speed, check proximity to each target's predicted position at that time). This approach is approximate; see research.md for the accepted design.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reinforcement Learning First | ⚠️ Acknowledged | This is heuristic rule-based, not RL. Constitution says RL is primary path but heuristics are acceptable as baseline. Agent has improved consistently via self-play evaluation — no violation. |
| II. Fair Play & Rules Compliance | ✅ Pass | All mechanics operate within CONTEST.md rules. No bug exploitation. Safety guards preserved. actTimeout (<1s/turn) respected. |
| III. Manual Submissions Only | ✅ Pass | No automated submission pipeline. Submission step is documented as manual (`make submit`). |
| IV. Experiment Documentation | ✅ Pass | Each candidate gets its own experiment record in `experiments/` before the agent file is written. All fields (hypothesis, change, result, conclusion) required. |
| V. Local Self-Play as Primary Loop | ✅ Pass | All candidates evaluated ≥50 games vs agent_v33 before any submission considered. Promotion gate (65%) enforced. |

**Result**: All gates pass. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/010-agent-experiments-round-3/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
experiments/
├── 010-candidate-S-fleet-dedup.md      # Candidate S experiment record
├── 010-candidate-T-transit-sizing.md   # Candidate T experiment record
├── 010-candidate-U-threat-garrison.md  # Candidate U experiment record
├── 010-candidate-V-winning-throttle.md # Candidate V experiment record
└── 010-combined-v38.md                 # Combined agent experiment record

agent_v34.py   # Candidate S: cross-turn fleet deduplication
agent_v35.py   # Candidate T: transit-adjusted fleet sizing
agent_v36.py   # Candidate U: threat-aware garrison floor
agent_v37.py   # Candidate V: winning-state garrison reduction
agent_v38.py   # Combined: all passing mechanics from v34–v37
```

**Structure Decision**: Single-project layout. All agent files at repo root (convention established from v1). Experiment records use `010-` prefix to distinguish from prior round records.

---

## Phase 0: Research

*All unknowns from Technical Context resolved below.*

### Decision 1: Candidate S implementation without `to_planet_id`

**Problem**: `obs.fleets` has no destination field. Cross-turn deduplication (preventing a second attack on a target already funded by an in-transit fleet) requires knowing where each friendly fleet is going.

**Decision**: Use angle-based destination inference.

**Algorithm**:
1. For each friendly fleet F in `obs.fleets` where `F.owner == player`:
   - Compute `fleet_speed(F.ships)`
   - For each target T, compute T's predicted position at `T.dist_to_fleet_current_pos / fleet_speed` turns from now (rough remaining travel time)
   - If the angle from F's current position toward T's predicted position is within `ANGLE_EPSILON = 0.1` radians of `F.angle`, assume F is targeting T
   - Accumulate `in_transit[T.id] += F.ships` for all matched targets
2. When computing `ships_needed` for target T: `ships_needed = max(1, best_target.ships + 1 - in_transit.get(best_target.id, 0))`
3. If `ships_needed <= 0`, skip dispatch (already fully covered)

**Rationale**: 0.1 radian threshold ≈ 5.7° — generous enough to match fleets that aimed at a planet that has since rotated slightly, tight enough to avoid false positives across distant planets. The approximation will have occasional false positives (skipping an attack when the fleet was actually going elsewhere), but this is acceptable in a 50-game evaluation.

**Alternatives considered**:
- Store destination in per-turn agent state: Python function is stateless between calls; no persistent state is accessible.
- Only deduplicate within the same turn: Already handled by single-sender coordination (Candidate D). Cross-turn is the new case.
- Skip Candidate S entirely: The hypothesis is still valid; approximation is the accepted engineering trade-off.

---

### Decision 2: Transit-adjusted sizing formula (Candidate T)

**Problem**: `ships_needed = best_target.ships + 1` ignores that enemy planets with `production > 0` accumulate ships during fleet transit, making the fleet insufficient on arrival.

**Decision**: Use projected garrison at arrival time.

**Formula**:
```
travel_turns = ceil(distance / fleet_speed(ships_needed))
projected_garrison = target.ships + target.production * travel_turns
ships_needed = projected_garrison + 1
```

**Iteration**: `travel_turns` depends on `ships_needed` (fleet speed is size-dependent), which depends on `projected_garrison`, which depends on `travel_turns`. Resolve with one fixed-point iteration:
1. Initial estimate: `travel_turns_0 = distance / fleet_speed(target.ships + 1)`
2. `projected_0 = target.ships + target.production * travel_turns_0`
3. Final: `ships_needed = projected_0 + 1` (one iteration sufficient; second iteration changes result by <1 ship for typical distances)

**Neutral planet edge case**: Neutral planets have production ≥ 1 but may also receive enemy attacks during transit. Production growth is the dominant factor; enemy attack on neutral is not modeled (acceptable approximation).

**Rationale**: For a target with production=3 and travel_turns=15, the naive agent under-sends by up to 45 ships. This is especially impactful for medium-distance enemy strongholds.

**Alternatives considered**: Model enemy reinforcement during transit — too speculative (requires predicting opponent behavior).

---

### Decision 3: Threat-aware garrison floor (Candidate U)

**Problem**: Fixed `GARRISON_FLOOR_FACTOR = 3` doesn't prevent dispatch from planets under imminent enemy attack.

**Decision**: Compute `incoming_enemy_ships(planet)` from `obs.fleets` and set floor to `max(standard_floor, incoming_enemy_ships)` when an enemy fleet is heading to the planet.

**Algorithm**:
- For each enemy fleet F in `obs.fleets` where `F.owner != player`:
  - Use angle-based inference (same ANGLE_EPSILON = 0.1 as Candidate S) to detect if F is heading toward owned planet P
  - Accumulate `threat[P.id] += F.ships`
- `garrison_floor(P) = max(GARRISON_FLOOR_FACTOR * P.production, threat.get(P.id, 0))`

**Constraint**: This mechanic interacts with Candidate S (both parse obs.fleets). When combined, the fleet parsing pass should be shared across both mechanics.

**Rationale**: More surgical than Candidate I (reactive defense, 16% vs v20) because this only raises the floor — it does NOT add new dispatch moves (which caused Candidate I's regression by diverting attack ships to defense).

**Alternatives considered**: Full reactive defense dispatch (Candidate I) — previously failed at 16% vs v20, 5% vs v32; explicitly excluded.

---

### Decision 4: Winning-state garrison reduction (Candidate V)

**Problem**: `GARRISON_FLOOR_FACTOR = 3` is constant. When own ships ≥ 2× all enemy ships, keeping 3× production garrison wastes ships that could close the game.

**Decision**: Dynamic garrison floor based on total-ship ratio.

**Formula**:
```python
own_total = sum(p.ships for p in my_planets)
enemy_total = sum(p.ships for p in planets if p.owner != player and p.owner != -1)
winning = own_total >= 2.0 * max(enemy_total, 1)
effective_floor_factor = 1 if winning else GARRISON_FLOOR_FACTOR  # 1 vs 3
```

**Threshold rationale**: 2.0× is conservative — ensures the agent won't regress into a losing position due to the reduced floor before it can adapt. Prior adaptive mechanics (Candidates G, J, K) used ratio gates and failed because they broke the decisive-outcome pattern established by agent_v20's no-range-limit mechanic. Candidate V uses a high-confidence gate (2:1) and only reduces the floor, never increasing range or adding complexity elsewhere.

**Interaction with other mechanics**: Candidate V reduces garrison floor. If combined with Candidate T (transit-adjusted sizing), the larger `ships_needed` from transit sizing might partially offset the extra ships freed by the reduced floor — net effect is more ships available for guaranteed-success sends. No conflict.

**Alternatives considered**: 1.5× threshold — more aggressive, higher risk of mid-game oscillation. 3.0× — too conservative, rarely triggers. 2.0× chosen as the safe-but-meaningful middle ground.

---

### Decision 5: Evaluation protocol

**50 games** (not 20) is the standard for this round because:
- agent_v33 uses production² ROI which produces decisive outcomes with few draws
- 20-game win rates have high variance (~±10%) for mechanics that pass at 55%–65%
- 50 games gives ±7% variance at 60% win rate (using binomial approximation)

**Borderline candidates** (50–55% in 50 games): extend to 100 games before excluding. Below 50% after 50 games: excluded immediately.

**Seeds**: 0–49 for 50-game runs, 0–99 for 100-game extensions. Random seed ensures reproducibility.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for full entity definitions.

**Key structures** (new or changed in Round 6):

| Name | Type | Description |
|------|------|-------------|
| `in_transit` | `dict[int, int]` | Maps `target_planet_id → ships_already_heading_there` (friendly fleets, cross-turn) |
| `threat` | `dict[int, int]` | Maps `owned_planet_id → enemy_ships_heading_there` |
| `projected_garrison` | `int` | `target.ships + target.production × travel_turns` — estimated garrison at fleet arrival |
| `effective_floor_factor` | `int` | 1 if winning by ≥2:1 ratio, else 3 (`GARRISON_FLOOR_FACTOR`) |
| `own_total` | `int` | Sum of ships on all owned planets |
| `enemy_total` | `int` | Sum of ships on all enemy-owned (non-neutral) planets |

### Agent Interface Contract

The agent function interface is unchanged: `agent(obs) → list[move]` where `move = [from_planet_id, angle_radians, num_ships]`.

**New obs fields accessed** (additions to v33):
- `obs.fleets` → list of `[id, owner, x, y, angle, from_planet_id, ships]` (used by Candidates S and U)

**No changes to `eval.py`, `diagnose_v9.py`, or `reward_signal.py`.**

See [contracts/agent-interface.md](contracts/agent-interface.md) for full interface spec.

### Quickstart

See [quickstart.md](quickstart.md) for step-by-step evaluation commands.

**TL;DR run sequence**:

```bash
# Evaluate each candidate (run one at a time)
python eval.py --agent0 agent_v34.py --agent1 agent_v33.py --games 50 --seed 0
python eval.py --agent0 agent_v35.py --agent1 agent_v33.py --games 50 --seed 0
python eval.py --agent0 agent_v36.py --agent1 agent_v33.py --games 50 --seed 0
python eval.py --agent0 agent_v37.py --agent1 agent_v33.py --games 50 --seed 0

# Evaluate combined (after identifying passing mechanics)
python eval.py --agent0 agent_v38.py --agent1 agent_v33.py --games 50 --seed 0

# Safety audit on the promoted agent
python diagnose_v9.py --agent agent_v38.py --games 50 --seed 0
```
