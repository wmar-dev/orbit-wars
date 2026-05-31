# Feature Specification: Clean Agent with Helper Module

**Feature Branch**: `013-clean-agent-helper`

**Created**: 2026-05-31

**Status**: Draft

**Input**: User description: "Make a new agent based on @main.py with learnings from all the previous agents with cleaner code and a helper.py that isolates the deterministic calculations, so a human can use the helper functions when crafting an agent. Test against agent 38 and agent 40."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Human-Crafted Agent Development (Priority: P1)

A human game developer wants to write a new Orbit Wars agent from scratch without having to re-implement or understand the accumulated low-level physics and game-mechanics calculations. They import `helper.py` and compose their own strategy using the helper functions, letting them focus on decision logic rather than geometry.

**Why this priority**: The primary stated goal of this feature is making helper functions available for human agent authors. Without a clean, documented `helper.py`, this feature delivers no new value over agent_v40.

**Independent Test**: A developer creates a minimal 10-line agent that imports `helper.py` and calls at least two helper functions; the agent runs to completion in a local eval against any opponent without errors.

**Acceptance Scenarios**:

1. **Given** a fresh Python file with `from helper import *`, **When** a developer calls `fleet_speed(100)`, `path_safe(...)`, `predict_planet_pos(...)`, and `angle_to(...)`, **Then** each function returns correct numeric values with no side effects.
2. **Given** `helper.py` in the repo root, **When** `python -c "import helper; print(helper.__all__)"` is run, **Then** all public helper functions are listed without errors.
3. **Given** a new agent file that uses only `helper.py` functions for all physics/geometry, **When** run in `eval.py` for 10 games, **Then** no `AttributeError`, `ImportError`, or division-by-zero errors occur.

---

### User Story 2 - New Best Agent (Priority: P2)

A developer wants a single clean agent file (`agent_v41.py`) that incorporates all proven improvements from the v38/v40 lineage, is readable top-to-bottom, and achieves competitive win rates against both agent_v38 and agent_v40.

**Why this priority**: This consolidates 40 iterations of incremental improvements into one clean canonical implementation, making the codebase maintainable.

**Independent Test**: Run `eval.py --agent0 agent_v41.py --agent1 agent_v38.py --games 50` and `eval.py --agent0 agent_v41.py --agent1 agent_v40.py --games 50`; results are reported and recorded.

**Acceptance Scenarios**:

1. **Given** `agent_v41.py` and `agent_v38.py`, **When** 50 evaluation games are run with seed 0, **Then** agent_v41 achieves ≥50% win rate vs agent_v38.
2. **Given** `agent_v41.py` and `agent_v40.py`, **When** 50 evaluation games are run with seed 0, **Then** agent_v41 achieves ≥45% win rate vs agent_v40 (acceptable draw parity given v40 promotes on ship score).
3. **Given** the agent file, **When** reviewed by a human, **Then** each logical section is immediately identifiable (parsing, threat detection, comet handling, targeting, move generation) without needing to read helper implementations.

---

### User Story 3 - Reusable Helper Library (Priority: P3)

A developer exploring new strategies can read `helper.py` as a standalone reference document showing what game-mechanics calculations are available, then assemble a novel agent strategy without touching `agent_v41.py`.

**Why this priority**: Secondary to working code, but important for the stated human-crafting use case.

**Independent Test**: `helper.py` can be imported in isolation (`python -c "import helper"`) without importing `kaggle_environments` or any agent file.

**Acceptance Scenarios**:

1. **Given** only `helper.py` in the Python path, **When** `import helper` is called, **Then** it imports successfully with no side effects.
2. **Given** `helper.py`, **When** a developer reads the function signatures, **Then** each function's purpose is clear from its name and parameter names alone, with a one-line docstring for any non-obvious function.

---

### Edge Cases

- What happens when a planet has `ships = 0`? Helper functions must not divide by zero.
- How does the agent behave when all my planets are in `departing_this_turn` (comet evacuation)? Returns empty moves list.
- What if `initial_planets` is empty (early-game or missing data)? `predict_planet_pos` falls back to current position.
- What if a fleet's angle data is missing or malformed? Threat detection skips malformed entries gracefully.
- What if `helper.py` is missing at submission time? The spec assumes `agent_v41.py` imports from `helper.py` (Kaggle multi-file package, Principle VI Option B).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `helper.py` MUST expose all deterministic game-mechanics calculations as importable, pure functions with no side effects: `fleet_speed`, `predict_planet_pos`, `converged_orbit_lead`, `path_safe`, `segment_dist_to_point`, `comet_predicted_pos`, `comet_two_pass`, `build_comet_path_lookup`, `roi`, `reward_estimate`, `angle_diff`, `planet_value`, `enemy_incoming`, `banking_mode`, and `angle_to`.
- **FR-002**: All functions in `helper.py` MUST be usable independently — no function may depend on game state being threaded through as a global variable.
- **FR-003**: `agent_v41.py` MUST import its physics/geometry calculations from `helper.py` rather than re-implementing them inline.
- **FR-004**: `agent_v41.py` MUST incorporate all proven mechanics from agent_v38 and agent_v40: threat-aware garrison floor (Candidate U), production-squared ROI (Candidate R), reward-blend scoring (Candidate S), converged orbit-lead + two-pass comet intercept, comet evacuation, single-sender coordination (replaced by best-sender assignment), GARRISON_FLOOR_FACTOR=3, no range cap, full-ray sun check, and intermediate planet obstruction check.
- **FR-005**: `agent_v41.py` MUST NOT include variant flags or experimental code paths; only the best-confirmed configuration from agent_v40 is retained (BANKING_VARIANT="B", FALLBACK_VARIANT="C", REWARD_ALPHA=0.1).
- **FR-006**: The agent MUST be submitted as a multi-file package (Principle VI Option B): `agent_v41.py` + `helper.py`, both at repo root.
- **FR-007**: Evaluation results for agent_v41 vs agent_v38 and vs agent_v40 MUST be recorded in `experiments/013-clean-agent-helper.md`.
- **FR-008**: README.md Agents table and Makefile `AGENT`/`RENDER_AGENT` MUST be updated to reflect agent_v41 if it becomes the new best agent.

### Key Entities

- **helper.py**: Pure-function module containing all deterministic game-mechanics calculations extracted from agent_v38/v40. Has no global mutable state. Can be imported independently of the agent.
- **agent_v41.py**: Clean agent implementation that imports from `helper.py` and contains only decision logic (parsing, strategy, move generation). Target: ≤350 LOC.
- **experiments/013-clean-agent-helper.md**: Eval results table documenting win rates and game counts for agent_v41 vs agent_v38 and agent_v40.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `helper.py` imports cleanly in under 1 second with no side effects, confirmed by `python -c "import helper"` completing without errors.
- **SC-002**: agent_v41 achieves ≥50% win rate vs agent_v38 across 50 games (seed 0).
- **SC-003**: agent_v41 achieves ≥45% win rate vs agent_v40 across 50 games (seed 0).
- **SC-004**: `agent_v41.py` is ≤350 lines (compared to ~470 LOC in agent_v40), demonstrating the clarity gain from helper extraction.
- **SC-005**: All public helper functions are callable with documented parameters — a developer can write a working agent using only `helper.py` and `main.py` as references without reading agent_v38/v40 source.

## Assumptions

- The submission package is a multi-file Kaggle notebook (Principle VI Option B): both `agent_v41.py` and `helper.py` are included. If Option A (self-contained) is required later, helper code is simply inlined.
- The best variant configuration from agent_v40 is BANKING_VARIANT="B" and FALLBACK_VARIANT="C" — these are locked in based on agent_v40 promotion decision. If further eval reveals otherwise, agent_v41 may adopt a different configuration before finalizing.
- agent_v40 is considered the current best agent and is the primary comparison target; agent_v38 is the secondary baseline.
- `helper.py` does not need its own test file — it is validated through the agent's eval runs and the import smoke test.
- No new game mechanics or strategies are introduced in this feature; it is a refactoring + consolidation of proven mechanics only.
- The `kaggle_environments` import (`Planet` named tuple) remains inside `agent_v41.py`, not in `helper.py`, since it is only needed for observation parsing.
