# Implementation Plan: Replay-Informed Agent Improvements

**Branch**: `012-replay-informed-improvements` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-replay-informed-improvements/spec.md`

## Summary

Build agent_v40 by layering three replay-derived heuristics on top of agent_v38's existing logic: (1) production-weighted planet priority with [0,1]-normalised scoring, (2) coordinated multi-planet attacks toward shared targets, and (3) a ship-banking phase gated on production advantage. Multiple variants of banking threshold and high-production fallback strategy are implemented and evaluated; the best-performing combination becomes agent_v40. Evaluation is local only (≥50 games vs agent_v38, seed 0); Kaggle submission is out of scope for this feature.

## Technical Context

**Language/Version**: Python 3.14 (repo requirement)

**Primary Dependencies**: `kaggle-environments>=1.28.0` (already installed); `numpy` for eval harness; `math` stdlib only in agent file

**Storage**: Flat files at repo root (`agent_v40.py`); experiment record at `experiments/012-replay-informed.md`

**Testing**: `eval.py --agent0 agent_v40.py --agent1 agent_v38.py --games 50 --seed 0` (win rate), `make test` (smoke test vs random)

**Target Platform**: Local macOS development (evaluation), Kaggle submission sandbox (inference — Principle VI compliant)

**Project Type**: Competitive game agent — rule-based heuristics, no training infrastructure

**Performance Goals**: ≥60% win rate vs agent_v38 (50 games, seed 0); turn time <1 second (pure math/stdlib)

**Constraints**: Agent file MUST comply with Principle VI (Option A: self-contained, or Option B: multi-file package). No torch or ML inference at runtime. All logic pure Python + stdlib.

**Scale/Scope**: Single agent file (~400–600 LOC). 3 banking threshold variants × 2 fallback strategy variants = up to 6 variant eval runs. Results in one combined experiment record.

**Key observation schema** (from CONTEST.md):

- `obs.planets` → `[id, owner, x, y, radius, ships, production]`
- `obs.fleets` → `[id, owner, x, y, angle, from_planet_id, ships]`
- `obs.initial_planets` → initial planet states (for orbit-lead)
- `obs.angular_velocity` → float (radians/turn)
- Fleet speed: `1.0 + 5.0 * (log(ships) / log(1000))^1.5`
- 4-fold mirror symmetry; 2-player game starts diagonal (Q1 vs Q4)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Reinforcement Learning First | ✅ Exempt | Constitution permits heuristic baseline agents. This feature improves the heuristic baseline; RL path (spec 011) remains the primary improvement track. |
| II. Fair Play & Rules Compliance | ✅ Pass | No engine modifications. actTimeout <1s enforced (pure math/stdlib). |
| III. Manual Submissions Only | ✅ Pass | Kaggle submission explicitly out of scope for this feature. |
| IV. Experiment & Improvement Documentation | ✅ Pass | Combined experiment record `experiments/012-replay-informed.md` required before any future submission. |
| V. Local Self-Play as Primary Evaluation Loop | ✅ Pass | 50-game eval vs agent_v38 with seed 0 is the gate. |
| VI. Submission Package Completeness | ✅ Pass | agent_v40.py will be self-contained (Option A) — stdlib + kaggle_environments imports only. |

**Result**: All gates pass. Proceeding to implementation.

---

## Project Structure

### Documentation (this feature)

```text
specs/012-replay-informed-improvements/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
agent_v40.py             # New agent — rule-based improvements on agent_v38

experiments/
└── 012-replay-informed.md   # Combined variant comparison table
```

**Structure Decision**: No new directories. agent_v40.py at repo root (matches existing convention). Single experiment record covers all variants.

---

## Phase 0: Research

### R-001: agent_v38 Architecture Audit

**Decision**: agent_v38 uses a single-sender coordination model (`best_sender` dict) — each target gets exactly one source planet. This is the key gap for coordinated multi-planet attacks.

**Current scoring pipeline**:

1. For each target, find the single best source planet by `dist / surplus` score
2. For that source, pick the highest blended ROI target (production² × time-decay / cost)
3. Send `target.ships + 1` ships (minimum to capture)

**What must change for agent_v40**:

- FR-001/FR-002: Replace the ROI-only scoring with a production-weighted value function using [0,1]-normalised inputs
- FR-003: Replace single-sender with multi-sender coordination — allow multiple planets to target the same destination
- FR-004/FR-005: Add banking phase state check before the main targeting loop
- FR-001 race condition: Detect enemy fleets en route to neutral targets; scale up fleet size

### R-002: Production Normalisation

**Decision**: Normalise production and distance independently over the full planet list each turn.

- `prod_norm = planet.production / max_production_on_map` (max production = 5 per CONTEST.md, but use observed max for robustness)
- `dist_norm = distance_to_planet / max_distance_on_map` (max possible distance ≈ 141 on 100×100 board)
- `planet_value = 2 * prod_norm - dist_norm` (production weight 2×, distance penalises farther planets)
- Enemy-owned planets: use same formula but add a separate `contested` flag for fallback mode

**Rationale**: Fixed max values (5 for production, 141 for distance) work reliably. Using observed max risks instability early in game when few planets are visible.

### R-003: Coordinated Attack Design

**Decision**: Replace `best_sender` (one source per target) with a **top-target grouping** model:

1. Score all non-owned planets using the production value function
2. Select the top target (highest value score)
3. All owned planets with surplus ships send toward the top target's predicted position
4. Secondary targets get assigned to remaining surplus planets after the primary wave

**Rationale**: Mirrors Isaiah's observed pattern — 2–3 planets send at nearly identical angles to the same target. Simpler than general multi-target assignment; focuses force on the highest-value planet first.

### R-004: Banking Phase Variants

Three variants to evaluate (FR-004):

| Variant | Condition to Bank | Condition to Exit |
| ------- | ----------------- | ----------------- |
| A — Fixed | `production_advantage ≥ 30%` AND `total_ships < 800` | `total_ships ≥ 800` |
| B — Production-relative | `production_advantage ≥ 30%` AND `total_ships < production_rate × 25` | `total_ships ≥ production_rate × 25` |
| C — Adaptive step-scaled | `production_advantage ≥ 30%` AND `game_step < 200` AND `total_ships < 600` | `total_ships ≥ 600` OR `game_step ≥ 200` |

`production_advantage = my_production / max(enemy_production, 1) ≥ 1.3`

### R-005: High-Production Fallback Variants

Two variants to evaluate (FR-002):

| Variant | Behaviour when no neutral high-production planets remain |
| ------- | ------------------------------------------------------- |
| A — Direct attack | Score enemy high-production planets (production ≥ 4) using value function; treat as top targets regardless of garrison |
| C — Hybrid | Attack the enemy high-production planet with the lowest garrison (most capturable); continue sending to available neutral planets in parallel |

### R-006: Race Condition Detection

**Decision**: Detect enemy fleets en route to a neutral target before sending:

```python
for each enemy fleet:
    expected_angle = atan2(target.y - fleet.y, target.x - fleet.x)
    if angle_diff(fleet.angle, expected_angle) < RACE_EPSILON (0.2 rad):
        enemy_ships_incoming += fleet.ships
ships_to_send = max(target.ships + 1, target.ships + enemy_ships_incoming + 1)
```

Cap at `source.ships - garrison_floor` to avoid overdrafting. If required ships exceed cap, still send cap amount (partial contest is better than ceding).

### R-007: Eval Variant Matrix

6 combinations to evaluate:

| Run | Banking | Fallback | Notes |
| --- | ------- | -------- | ----- |
| v40-A-A | Fixed 800 | Direct attack | |
| v40-A-C | Fixed 800 | Hybrid | |
| v40-B-A | Prod-relative | Direct attack | |
| v40-B-C | Prod-relative | Hybrid | |
| v40-C-A | Adaptive | Direct attack | |
| v40-C-C | Adaptive | Hybrid | Best predicted |

Best win-rate combination vs agent_v38 (50 games, seed 0) becomes agent_v40.

---

## Phase 1: Design

### Data Model

See [data-model.md](data-model.md).

### Agent Context Update

CLAUDE.md updated to point to this plan (see below).

---

## Implementation Phases

### Phase A: Core Value Function (FR-001, FR-002)

Replace agent_v38's `_roi()` scoring with the new production-weighted value function. Implement fallback variant flag (`FALLBACK = "A"` or `"C"`). Keep all other agent_v38 logic intact.

**Acceptance**: `make test` passes; agent can be imported without errors.

### Phase B: Multi-Planet Coordination (FR-003)

Replace `best_sender` single-sender model with top-target grouping. All planets with surplus route to the highest-value target; remaining planets route to secondary targets.

**Acceptance**: In a test game, multiple planets demonstrably send toward the same target in the same turn.

### Phase C: Banking Phase (FR-004, FR-005)

Add `_banking_mode(my_planets, enemy_planets, step, variant)` check at the top of `agent()`. When active, suppress offensive sends (skip targeting loop); allow evacuation sends and defensive sends to proceed.

**Acceptance**: Agent accumulates ships for ≥20 consecutive turns when holding production advantage in a test game.

### Phase D: Race Condition Scaling (FR-001 addendum)

Add enemy-fleet-in-transit detection for neutral targets. Scale `ships_to_send` accordingly.

**Acceptance**: Agent sends enough ships to win contested captures in simulated scenarios.

### Phase E: Variant Eval & Selection (FR-008)

Run all 6 variant combinations against agent_v38 for 50 games each (seed 0). Record results in `experiments/012-replay-informed.md`. Select best combination as agent_v40.

**Acceptance**: One variant achieves ≥60% win rate vs agent_v38; README and Makefile updated.
