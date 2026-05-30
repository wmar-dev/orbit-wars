# Feature Specification: Sun Avoidance Experiment

**Feature Branch**: `002-sun-avoidance-experiment`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Experiment with a new agent to avoid crossing the sun and being destroyed compare baseline and v2 with this ability"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sun-Safe Agent Survives Where Others Are Destroyed (Priority: P1)

A developer wants to confirm that the new agent never routes fleets through the sun, preventing fleet destruction that both the baseline and agent_v2 may suffer from.

**Why this priority**: Fleet destruction from sun crossings is a direct, measurable loss of resources. Eliminating this failure mode is the foundational value of this experiment.

**Independent Test**: Can be fully tested by running a set of seeded games, observing fleet move events, and confirming zero fleets from the new agent are flagged as destroyed by sun collision — compared against baseline and agent_v2 which may have non-zero such events.

**Acceptance Scenarios**:

1. **Given** a game in progress where the shortest path between two planets crosses the sun, **When** the new agent dispatches a fleet from the source planet, **Then** the fleet takes an arc path that avoids the sun and arrives safely at the destination.
2. **Given** 10 games across varied seeds, **When** all games complete, **Then** the new agent suffers zero fleet losses due to sun collision.
3. **Given** the baseline (main.py) and agent_v2 play the same seed games, **When** those games complete, **Then** at least one of those agents incurs a sun-collision loss that the new agent would have avoided.

---

### User Story 2 - Comparative Win Rate Evaluated Against Baseline and v2 (Priority: P2)

A developer runs the full evaluation harness and receives a head-to-head win-rate comparison: new sun-aware agent vs. main.py (baseline) and vs. agent_v2, to determine whether sun avoidance helps or hurts overall performance.

**Why this priority**: Avoiding the sun has a strategic cost (longer travel arcs = slower captures). The experiment must measure whether the safety gain outweighs that cost in terms of overall win rate.

**Independent Test**: Can be tested by running `eval.py` twice — new agent vs. main.py, then new agent vs. agent_v2 — and reading the printed win rates for each pairing.

**Acceptance Scenarios**:

1. **Given** 10 games between the new sun-aware agent and main.py, **When** results are printed, **Then** the new agent's win rate vs. baseline is reported clearly (target: ≥ 70%).
2. **Given** 10 games between the new sun-aware agent and agent_v2, **When** results are printed, **Then** the new agent's win rate vs. agent_v2 is reported (outcome may vary; experiment determines this).
3. **Given** both comparisons complete, **When** results are reviewed, **Then** the developer can draw a clear conclusion about whether sun avoidance is a net positive strategy.

---

### User Story 3 - Experiment Results Recorded (Priority: P3)

A developer records the experiment's results in the experiments log so the finding persists for future reference and Kaggle submissions.

**Why this priority**: Per project practice, every experiment must be documented. The entry allows future agents to build on this finding.

**Independent Test**: Can be tested by checking that an entry exists in the experiments log with win rates, seed range, and a brief strategy note after the evaluation runs.

**Acceptance Scenarios**:

1. **Given** the evaluation completes, **When** the developer records results, **Then** the experiments log contains an entry with: agent name, strategy summary, seeds tested, win rate vs. baseline, and win rate vs. agent_v2.
2. **Given** the log entry is written, **When** a reviewer reads it, **Then** they can understand what sun avoidance means strategically and what the outcome was without running the code.

---

### Edge Cases

- What happens when both the arc-safe path and the direct path are equivalent length (no sun in the way)? The agent should behave identically to its targeting logic with no performance penalty.
- What happens when all planets are clustered on one side and the sun is never on any direct path? The agent should still win at least as often as the strategy it is based on.
- What if a planet is directly behind the sun and no arc avoidance is possible? The agent should skip or deprioritize that target rather than sending fleets to be destroyed.
- What happens if the agent has no ships to send on a given turn? Return a valid no-op action.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The new agent MUST be implemented as a single `agent(obs)` function in a Python file compatible with the `kaggle_environments` Orbit Wars environment.
- **FR-002**: The new agent MUST detect when a direct fleet path from source to target crosses the sun's exclusion zone and route around it or skip the target.
- **FR-003**: The new agent MUST inherit the production-weighted targeting strategy from agent_v2 as its base and layer sun avoidance on top.
- **FR-004**: The new agent MUST never crash or return an invalid action format on any turn.
- **FR-005**: The evaluation harness MUST run at least 10 games for each pairing (new agent vs. baseline, new agent vs. agent_v2) using seeds 0–9.
- **FR-006**: The evaluation output MUST print per-game results and aggregate win rates for each pairing.
- **FR-007**: The experiment results MUST be recorded in the project's experiments log with strategy description, win rates, and seed range.

### Key Entities

- **Fleet**: A group of ships dispatched from a source planet to a target planet; subject to sun collision if path crosses the exclusion zone.
- **Sun exclusion zone**: The circular area centered on the sun within which fleets are destroyed; radius defined by game rules.
- **Arc path**: An alternative route that bypasses the sun by traveling along a curved trajectory rather than a straight line.
- **Agent**: A Python function that receives the game observation each turn and returns a list of fleet dispatch actions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The new agent suffers zero fleet losses due to sun collision across all 10 evaluation games (seeds 0–9).
- **SC-002**: The new agent achieves a win rate of at least 70% against main.py (baseline) across 10 games.
- **SC-003**: The new agent's win rate against agent_v2 is measured and reported; the experiment conclusion states whether sun avoidance is a net positive, neutral, or negative strategy relative to agent_v2.
- **SC-004**: Evaluation results for both pairings are available within 30 seconds of running the evaluation command.
- **SC-005**: A reviewer can determine from the experiments log entry alone — without running code — what the strategic trade-off of sun avoidance is.

## Assumptions

- The Orbit Wars environment exposes sun position and radius in the game observation so the agent can compute whether a path crosses the exclusion zone.
- The existing `eval.py` harness supports arbitrary agent file pairings without code changes; the new agent file simply replaces `--agent0`.
- Sun collision rules destroy the entire dispatched fleet (not partial losses), making avoidance binary: either the fleet is safe or it is entirely lost.
- Mobile support and Kaggle submission are out of scope for this experiment; the goal is local evaluation only.
- The arc-routing implementation will use a simple detour heuristic (e.g., waypoint tangent to the sun's exclusion zone) rather than full A* pathfinding.
