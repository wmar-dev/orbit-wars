# Feature Specification: Agent Gap Analysis & Improvement Experiments

**Feature Branch**: `003-agent-gap-analysis`

**Created**: 2026-05-29

**Status**: Complete

**Input**: User description: "Identify anything obvious the agent does not take into account from CONTEST.md. Experiment with fixes with these issues to see if it improves agent versus current best agent."

## Overview

The current best agent (`agent_v3.py`) uses production-weighted targeting with sun-path avoidance. This spec identifies the gaps between what the contest rules describe and what agent_v3 actually does, then defines a series of targeted experiments — each adding one mechanic — measured against agent_v3 as the baseline.

## Contest Mechanics Not Accounted For

### Gap 1: Orbiting Planet Motion (HIGH IMPACT)

Agent_v3 aims fleets at a planet's current (x, y). Orbiting planets (those with `orbital_radius + planet_radius < 50`) rotate at `angular_velocity` radians/turn. A fleet takes many turns to arrive; the planet has moved. The agent fires at where the planet *is*, not where it *will be*.

**Relevant observation fields**: `initial_planets`, `angular_velocity`.

**Fix**: Predict target planet position at arrival time using `angular_velocity` and `initial_planets`, then aim at the predicted position.

**Travel time estimate**: `distance_to_target / fleet_speed(ships)` where `fleet_speed(n) = 1.0 + 5.0 * (log(n) / log(1000))^1.5`.

### Gap 2: Comets (MEDIUM IMPACT)

The agent never targets comets. Comets are planets with low garrison (skewed toward minimum of 4 rolls from 1–99 — typically very low), produce 1 ship/turn while owned, and appear at steps 50, 150, 250, 350, 450. They are identified via `comet_planet_ids` in the observation.

**Fix**: Include comets in the candidate target list. Because comets move along known paths (`comets[].paths`, `comets[].path_index`), aim at their predicted position at arrival.

**Constraint**: Do not launch from a comet if it may leave the board that turn (check `path_index` approaching the end of `paths`).

### Gap 3: No Defense / Reinforcement (MEDIUM IMPACT)

Agent_v3 only attacks. It never reinforces an owned planet that enemy fleets are approaching. Ships on an overwhelmed planet are lost; a planet flip also hands the enemy production.

**Fix**: Before selecting attack targets, scan `fleets` for enemy fleets heading toward owned planets. If an inbound fleet would exceed current garrison, send reinforcements from a nearby owned planet (if affordable without stripping it below a safe threshold).

### Gap 4: Fleet Speed Ignored in Targeting Score (LOW-MEDIUM IMPACT)

The targeting score is `production / distance`. Larger fleets move faster (up to 6.0 units/turn vs 1.0 for 1 ship). The score should account for actual travel time rather than raw distance, because a fast large fleet can reach a far target quicker than a slow small fleet.

**Fix**: Replace `distance` in the score denominator with `estimated_turns = distance / fleet_speed(ships_available)` so high-production far planets become relatively more attractive when the agent has a large garrison.

### Gap 5: Combat Over-Sending (LOW IMPACT)

The agent sends exactly `garrison + 1` ships to capture. If multiple own planets target the same neutral planet simultaneously (rare but possible), ships are wasted. More importantly, a `garrison + 1` fleet is slow (1 ship → speed 1.0) and wastes almost all the garrison.

**Fix**: Send a minimum viable capturing fleet that still travels at reasonable speed. A fleet of ~10 ships moves at speed ≈ 2.5; a fleet of 50 moves at ≈ 4.1. Consider sending `max(garrison + 1, small_fast_fleet_size)` to balance capture certainty vs. travel time.

## User Scenarios & Testing

### User Story 1 — Orbiting Planet Lead Targeting (Priority: P1)

As an agent developer, I want the agent to aim fleets at where orbiting planets will be at fleet arrival time, so fleets don't miss their targets.

**Why this priority**: Orbiting planet misses are complete resource losses with zero capture upside. The contest guarantees at least one orbiting group exists every game.

**Independent Test**: Run `eval.py` comparing `agent_v4.py` (orbit-lead targeting only) vs `agent_v3.py` over 20 games. Agent v4 should win more often on maps where orbiting planets are common attack targets.

**Acceptance Scenarios**:

1. **Given** an orbiting planet at angle θ with angular velocity ω, **When** the agent launches a fleet that takes T turns to arrive, **Then** the fleet's heading angle points at θ + ω×T (the predicted position), not θ.
2. **Given** a static planet (orbital_radius + planet_radius ≥ 50), **When** the agent targets it, **Then** the heading is unchanged from current position (no regression).
3. **Given** a predicted landing position that crosses the sun, **When** applying the sun-avoidance filter, **Then** the fleet is still skipped.

---

### User Story 2 — Comet Opportunism (Priority: P2)

As an agent developer, I want the agent to consider capturing comets when their garrison is low, so it gains bonus production without fighting fortified planets.

**Why this priority**: Comets have very low starting ships and spawn 5 times per game. Missing easy captures is a concrete resource loss.

**Independent Test**: Run `eval.py` comparing a comet-aware agent vs `agent_v3.py`. Check that the comet-aware agent captures at least one comet per game in verbose mode.

**Acceptance Scenarios**:

1. **Given** a comet in `comet_planet_ids` with low garrison, **When** an owned planet can afford capture and the path is sun-safe, **Then** the agent targets the comet.
2. **Given** a comet whose `path_index` is near the end of its `paths` list, **When** computing whether to launch, **Then** the agent skips it (the comet will leave the board before the fleet arrives).
3. **Given** the agent owns a comet, **When** the comet's path is about to end, **Then** the agent does not launch from it (respects the turn-order rule that comets expire before launches).

---

### User Story 3 — Defensive Reinforcement (Priority: P3)

As an agent developer, I want the agent to send reinforcements to threatened owned planets, so it avoids free planet flips from uncontested enemy fleets.

**Why this priority**: A lost planet means both a garrison loss and a production swing. Defending is often cheaper than recapturing.

**Independent Test**: Run `eval.py` comparing a defense-aware agent vs `agent_v3.py`. In verbose mode, check that the agent issues reinforcement moves when enemy fleets are inbound.

**Acceptance Scenarios**:

1. **Given** an enemy fleet heading toward an owned planet that will exceed garrison on arrival, **When** a nearby friendly planet has surplus ships, **Then** the agent dispatches reinforcements.
2. **Given** a reinforcement opportunity where stripping the source planet below a safety threshold would leave it indefensible, **When** the agent evaluates, **Then** it does not send reinforcements (avoids self-harm).

---

### Edge Cases

- What happens when all orbiting planet predicted positions cross the sun? (fall back to static targeting, then skip if still sun-crossing)
- What if a comet is targeted by both own planets simultaneously? (over-sending is acceptable for v1 comet support)
- What if an inbound enemy fleet is already too close to intercept with any reinforcement? (skip; don't waste ships on lost causes)
- What if the agent owns a comet that will expire next turn? (launch all ships off it toward the best available target — ships are lost when the comet departs, so any launch is better than nothing)
- What if `angular_velocity` is 0 (a planet that appears orbiting but is actually static)? (prediction reduces to current position — no regression)

## Clarifications

### Session 2026-05-29

- Q: Should each experiment agent add only one new mechanic on top of agent_v3 (isolated), or should each build cumulatively on the previous winner? → A: Both — run isolated experiments first, then build one combined agent stacking all mechanics that individually passed the 55% threshold.
- Q: For defensive reinforcement (Gap 3), what should the minimum safe garrison threshold be? → A: Production × 10 (dynamic) — a planet holds at least `production * 10` ships before it can send reinforcements.
- Q: Should gaps 4 and 5 each get their own isolated experiment agents, or are they low-priority enough to skip or bundle? → A: Bundle gaps 4 & 5 together into one agent file (scoring and launch tweaks combined).

## Functional Requirements

### Experiment Structure (clarified)

Experiments are run in two phases:

**Phase 1 — Isolated experiments** (one mechanic each, all vs agent_v3):

- `agent_v4.py` — orbit-lead targeting only (Gap 1)
- `agent_v5.py` — comet opportunism only (Gap 2)
- `agent_v6.py` — defensive reinforcement only (Gap 3)
- `agent_v7.py` — fleet-speed scoring + minimum fast-fleet send combined (Gaps 4 & 5)

**Phase 2 — Combined agent**:

- `agent_v8.py` — stacks all mechanics from isolated agents that individually passed ≥55% win rate vs agent_v3.

### Requirements

1. **FR-1**: The agent shall compute a planet's predicted position at fleet arrival time for all planets where `initial_planets` data shows the planet as orbiting (distance from center < 50 - planet_radius at game start).
2. **FR-2**: The agent shall use the predicted position (not current position) to compute fleet heading angle for orbiting targets.
3. **FR-3**: The agent shall apply the sun-avoidance filter against the straight-line path to the predicted position.
4. **FR-4**: The agent shall include planets listed in `comet_planet_ids` as valid capture targets.
5. **FR-5**: The agent shall predict comet positions at fleet arrival time using `comets[].paths` and `comets[].path_index`.
6. **FR-6**: The agent shall skip launching at a comet whose remaining path length is shorter than the estimated fleet travel turns.
7. **FR-7**: Defensive reinforcement shall only send ships from a source planet if that planet retains at least `source.production × 10` ships after the dispatch.
8. **FR-8**: For each experiment, a new agent file is created — existing agent files are never modified.
9. **FR-9**: Each isolated experiment agent shall be evaluated against `agent_v3.py` using `eval.py` with exactly 20 games (seeds 0–19) and results recorded in `experiments/`.
10. **FR-10**: The combined agent (`agent_v8.py`) stacks only mechanics whose isolated agent passed ≥55% win rate, and is evaluated the same way.
11. **FR-11**: Only the combined agent (or the best isolated agent if no others pass) is considered for Kaggle submission.

## Success Criteria

1. At least one experiment produces an agent that wins ≥55% of games against agent_v3 over a 20-game evaluation.
2. The winning agent's advantage is reproducible: a second 20-game run also shows ≥55% win rate (ruling out seed variance).
3. Each experiment is implemented and evaluated in a single agent file with no regressions in sun-avoidance behavior.
4. Turn decision time remains under 1 second per turn.

## Assumptions

- `angular_velocity` is constant and uniform for all orbiting planets in a given game (per CONTEST.md: "constant angular velocity").
- Fleet travel time approximation using current-distance / fleet-speed is sufficient for orbit lead calculation (exact iterative solution not needed for v1).
- The eval harness (`eval.py`) with 20 games and sequential seeds 0–19 provides statistically meaningful signal (±10% win rate uncertainty at 20 games).
- Static planets have `orbital_radius + planet_radius ≥ 50`; this can be inferred from `initial_planets` data (a planet is orbiting if it is not within `orbital_radius + radius ≥ 50` of center at game start).

## Dependencies

- `agent_v3.py` — current best agent, used as evaluation baseline
- `eval.py` — existing evaluation harness (no changes needed)
- `initial_planets` observation field — required for orbit lead calculation
- `angular_velocity` observation field — required for orbit lead calculation
- `comets` observation field — required for comet path prediction
- `comet_planet_ids` observation field — required to identify comet targets

## Out of Scope

- Multi-planet coordination (preventing two own planets from targeting the same enemy planet simultaneously)
- Arc routing around the sun (fleets take curved paths); still skipping sun-crossing routes
- Reinforcement against multi-fleet coordinated attacks by the opponent
- Machine learning or any approach that requires training data
