# Feature Specification: Planet Wars Winner Strategies

**Feature Branch**: `016-planet-wars-winner-strategies`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "Learn from the Planet Wars contest winner (https://quotenil.com/Planet-Wars-Post-Mortem.html, https://github.com/melisgl/planet-wars) and run experiments to improve the agent."

## Context

The 2010 Google AI Challenge "Planet Wars" winner (bocsimacko) documented their approach in a post-mortem. Our current best agent (v56) scores ~846 on the Orbit Wars leaderboard, while the top competitors are at ~1724 — roughly a 2x gap. The winning strategies from the historical contest are directly applicable to Orbit Wars and represent a concrete roadmap of techniques we have not yet implemented.

Key insights from the post-mortem and GitHub source:
- **Surplus concept**: Only dispatch ships that won't be needed for defense or existing commitments
- **Multi-turn scheduling**: Coordinate attacks across multiple turns rather than greedy single-turn decisions
- **Redistribution**: Move ships between friendly planets to concentrate force where needed
- **Position-based penalization**: A per-enemy-ship penalty (small, per-turn) encourages spatial control without requiring explicit territory logic
- **Dynamic look-ahead horizon**: Depth based on break-even turns rather than a fixed window
- **Full attack future analysis**: Evaluate positions by asking "who wins if both players commit all ships?"
- **Opening patience**: In the early game (first few planets), patience and alpha-beta search beat greedy expansion
- **MIN-TURN-TO-DEPART-1**: A constraint on departure timing that suppressed destabilizing rock-paper-scissors cycles — described as "the most important one-character change"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Implement and evaluate surplus-based dispatching (Priority: P1)

As the agent developer, I want to replace the current garrison-floor heuristic with a proper surplus calculation that accounts for in-flight commitments, so the agent doesn't over-commit ships and lose planets.

**Why this priority**: The current agent dispatches based on a static garrison floor but doesn't account for already-dispatched fleets. Proper surplus is foundational — other improvements layer on top of it.

**Independent Test**: Run 50 games of the new agent vs v56. Pass if win rate ≥ 55%.

**Acceptance Scenarios**:

1. **Given** an agent with ships already dispatched toward a target, **When** considering the next dispatch, **Then** those already-committed ships are subtracted from the available surplus.
2. **Given** an incoming enemy threat detected on a planet, **When** calculating surplus, **Then** the surplus is zero if available ships ≤ threat size + garrison floor.
3. **Given** a planet below its garrison floor, **When** the agent runs, **Then** no ships are dispatched from that planet.

---

### User Story 2 - Implement redistribution (ship consolidation) (Priority: P2)

As the agent developer, I want the agent to move excess ships from weaker/safer planets toward stronger planets or forward positions, so ship concentration improves without waiting for an attack opportunity.

**Why this priority**: The post-mortem identifies redistribution as a key mechanism for improving influence and attack capacity. Currently, surplus ships sit idle on safe planets.

**Independent Test**: Run 50 games vs v56 with redistribution added. Pass if win rate ≥ 52% and average ship utilization (ships dispatched / total ships) improves by ≥ 10%.

**Acceptance Scenarios**:

1. **Given** a backline planet with large surplus and no nearby targets, **When** a frontline friendly planet is closer to enemy planets, **Then** the agent dispatches surplus ships toward the frontline planet rather than sitting idle.
2. **Given** two friendly planets, one high-production frontline and one low-production backline, **When** the backline has surplus, **Then** the agent concentrates ships at the frontline.
3. **Given** all planets are under threat, **When** redistribution runs, **Then** no redistribution occurs (defense takes priority).

---

### User Story 3 - Implement position-based penalty for spatial control (Priority: P3)

As the agent developer, I want the agent to apply a small continuous penalty proportional to enemy ship counts when evaluating candidate planets, so the agent naturally gravitates toward favorable spatial positions.

**Why this priority**: The post-mortem credits this as a key insight that drove the bot toward spatial control without requiring explicit territory logic. It's a lightweight change with potentially high impact.

**Independent Test**: Run 50 games vs v56 with penalty added. Pass if win rate ≥ 52%.

**Acceptance Scenarios**:

1. **Given** two capture opportunities of equal ROI, **When** one is surrounded by more enemy ships, **Then** the agent prefers the planet surrounded by fewer enemy ships.
2. **Given** the early game, **When** evaluating neutral planets, **Then** planets deeper in enemy territory are scored lower than equally-valued planets on our side of the board.
3. **Given** the penalty weight is adjustable, **When** the weight is 0, **Then** the agent behaves identically to the baseline.

---

### User Story 4 - Evaluate multi-turn departure constraint (MIN-TURN-TO-DEPART equivalent) (Priority: P4)

As the agent developer, I want to experiment with a minimum departure interval constraint that prevents sending a fleet from the same planet every turn, so the agent avoids the rock-paper-scissors oscillation patterns.

**Why this priority**: Described in the post-mortem as "the most important one-character change." Low implementation cost, potentially high impact.

**Independent Test**: Run 50 games with cooldown constraint (1-2 turns) vs v56. Pass if win rate ≥ 52%.

**Acceptance Scenarios**:

1. **Given** a planet dispatched a fleet last turn, **When** the constraint is active, **Then** the planet may not dispatch again until the cooldown expires.
2. **Given** a planet under imminent threat, **When** the constraint is active, **Then** the constraint is overridden for defensive evacuation.
3. **Given** cooldown = 0, **When** the agent runs, **Then** behavior is identical to baseline (no constraint applied).

---

### Edge Cases

- What happens when all friendly planets are below garrison floor and no redistribution is possible? (Agent returns empty moves.)
- What happens when redistribution target is also a comet planet about to depart? (Skip comet planets as redistribution targets.)
- What happens if surplus ships after accounting for commitments is negative? (Clamp to zero — no dispatch.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST calculate per-planet surplus by subtracting both the garrison floor and all ships already committed (in-flight) to pending targets.
- **FR-002**: The agent MUST support redistribution moves that send surplus ships to a friendly planet with higher forward value.
- **FR-003**: Redistribution MUST be lower priority than offensive capture; a planet with a capture target MUST prefer attacking over redistributing.
- **FR-004**: The target scoring function MUST accept an optional spatial penalty weight that reduces score based on nearby enemy ship density.
- **FR-005**: The agent MUST support a configurable departure cooldown (min turns between dispatches from same planet), defaulting to 0 (off).
- **FR-006**: All existing mechanics (comet evacuation, orbit lead, sun avoidance, threat detection) MUST be preserved across all experiments.
- **FR-007**: Each experiment variant MUST be runnable in isolation as a standalone agent file for A/B evaluation against v56.
- **FR-008**: Each experiment MUST be evaluated with at least 50 games vs v56 before drawing conclusions.

### Key Entities

- **Surplus**: Ships available for dispatch = total ships − garrison floor − committed in-flight ships targeting uncommitted destinations.
- **Redistribution move**: A fleet sent from one friendly planet to another friendly planet to concentrate force.
- **Spatial penalty**: A per-target score deduction proportional to the sum of enemy ship counts within a configurable radius.
- **Departure cooldown**: Per-planet counter tracking turns since last dispatch; blocks new dispatches until expired.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one experiment variant achieves ≥ 55% win rate against v56 over 50 games.
- **SC-002**: The best-performing variant achieves a leaderboard score improvement of ≥ 50 points over v56 (from 846 toward the top-20 range).
- **SC-003**: No experiment variant performs below 40% win rate against v56 across 50 games (confirms each idea is at least not harmful before tuning).
- **SC-004**: All variants complete a 50-game evaluation in under 30 minutes of wall-clock time.
- **SC-005**: The final selected agent passes the existing comet evacuation and sun-avoidance regression tests.

## Assumptions

- The Orbit Wars game mechanics (fleet speed, garrison, production, orbiting planets, comets) are stable — no API changes expected.
- Agent v56 is the correct baseline for evaluation; the best submitted agent is v50 (score 846), and v56 is the current development head.
- The post-mortem techniques are heuristic-level insights, not direct code ports — adaptation for Orbit Wars mechanics is expected.
- Experiments are independent agent files (e.g., agent_v57_surplus.py, agent_v57_redistrib.py) evaluated sequentially, not in parallel.
- The departure cooldown experiment will test values of 1 and 2 turns; values above 2 are out of scope.
- Redistribution is limited to one hop per turn to keep the agent's complexity manageable.
- Multi-turn scheduling (alpha-beta search) is out of scope for this feature — it warrants its own larger spec if initial experiments show high potential.
