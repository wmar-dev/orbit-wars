# Feature Specification: RL Full Observation

**Feature Branch**: `027-rl-full-obs`

**Created**: 2026-06-07

**Status**: Draft

**Input**: User description: "Try RL again with using knowledge @CONTEST.md."

## User Scenarios & Testing

### User Story 1 — Full-Board Observation (Priority: P1)

The RL agent currently sees only 12 of 20-40 planets. It must observe ALL planets on the board to make informed decisions. The observation encoder must scale to 40 planets, support 50+ fleets, include orbiting/static planet type flags, and provide comet path predictions.

**Why this priority**: If the agent can't see most of the board, it will never learn competitive play regardless of training duration.

**Independent Test**: Run a game with 40 planets, encode the observation, and confirm the output vector is non-zero for all occupied planet slots and has the correct total size.

**Acceptance Scenarios**:

1. **Given** a game with 40 planets, **When** I run `encode_obs`, **Then** the output vector contains non-zero values across all planet features for each of the 40 planets.
2. **Given** a 4-player game, **When** I encode the observation, **Then** all enemy-owned planets are correctly identified (owner != player_id and != -1).
3. **Given** the observation includes comet groups, **When** I encode, **Then** comet planet positions and remaining steps are embedded in the vector.
4. **Given** the observation includes orbiting planets, **When** I encode, **Then** the planet type (orbiting vs static) is encoded as a feature flag.

---

### User Story 2 — Multi-Fleet Action Space (Priority: P1)

The RL agent currently outputs ONE fleet per turn. The game allows multiple dispatches from different planets in the same turn. The action space must expand to produce N fleets per turn (N=5), where each fleet has a source planet, target angle, and ship count.

**Why this priority**: The single-fleet action is the most crippling limitation. A heuristic agent dispatches 5-10 fleets per turn. RL must match this throughput.

**Independent Test**: Run the agent in a game and confirm it dispatches up to 5 fleets per turn, each with valid planet IDs, angles, and ship counts.

**Acceptance Scenarios**:

1. **Given** the RL agent controls 3+ planets with surplus ships, **When** it takes a turn, **Then** it dispatches at least 2 fleets in a single step.
2. **Given** the action space outputs 5 fleets, **When** a fleet has an invalid source (same as target, or not owned), **Then** that fleet is silently dropped and does not affect other fleets.
3. **Given** an observation with planets at known positions, **When** the agent outputs an angle, **Then** the fleet trajectory is geometrically valid (points toward a target region).

---

### User Story 3 — Train vs Strong Heuristic (Priority: P2)

With the fixed observation and multi-fleet action space, train the PPO policy against agent_v64 and achieve a measurable win rate.

**Why this priority**: The previous attempt hit 0% because the agent was blind and couldn't execute multi-fleet strategies. Fixing the pipeline is necessary but not sufficient — we must verify the training loop actually produces improvement.

**Independent Test**: Train 2000 episodes vs v64, then evaluate with 50 head-to-head games. Report win rate.

**Acceptance Scenarios**:

1. **Given** the agent has been trained for 5000 episodes against v64, **When** evaluated in 50 games with side-swapping, **Then** win rate ≥ 5% (interim target).
2. **Given** the agent has been trained for 20000 episodes against v64, **When** evaluated in 50 games, **Then** win rate ≥ 20%.

---

### Edge Cases

- What if the game has fewer planets than MAX_PLANETS? Unused slots should be zero-padded in the observation vector.
- What if a planet has zero surplus (garrison floor >= ships)? That planet should not appear as a valid source, but the agent can still target it.
- What if the agent tries to send a fleet from a planet that was captured mid-turn? Only planets owned at the START of the turn can dispatch.
- What if all planets are comets about to expire? The agent should be able to launch from comets (they follow normal planet rules before expiration).
- What if the game has >50 fleets simultaneously? Common in late-game 4-player — excess fleets beyond the max slot count are discarded.
- What if `initial_planets` is not available? Fall back to treating all planets as static.

## Requirements

### Functional Requirements

- **FR-001**: The observation encoder MUST support up to 40 planet slots (7 features each) in a fixed-size output vector.
- **FR-002**: The observation encoder MUST support up to 50 fleet slots (5 features each).
- **FR-003**: The observation encoder MUST encode an orbiting-vs-static flag for each planet.
- **FR-004**: The observation encoder MUST predict future comet positions using the `paths` field and encode the nearest N waypoints.
- **FR-005**: The action space MUST output up to 5 fleets per turn, each with source planet slot, target angle, and ship fraction.
- **FR-006**: Each fleet's action MUST be independently masked: invalid fleet slots are zeroed and ignored during the step.
- **FR-007**: The agent MUST send at most one fleet per source planet per turn (cannot double-dispatch from the same planet).
- **FR-008**: The training pipeline MUST continue to support `--resume`, checkpointing, and export to a single-file agent.
- **FR-009**: The exported agent file MUST be Principle VI compliant (no local imports, only stdlib + numpy).

### Key Entities

- **FullObservation**: 40 planet slots, 50 fleet slots, 10 comet slots, 4 global features, 80 mask bits. Estimated size 40×7 + 50×5 + 10×3 + 4 + 80 = 280 + 250 + 30 + 4 + 80 = 644 floats.
- **MultiFleetAction**: 5 ordered fleet slots, each with source index (0-39), target index (0-39), ship fraction (0-3). Factorized action: 5 × (40 × 40 × 4) = 5 × 6400 = 32000 discrete options, implemented as 5 × 3 logits.
- **PlanetType** (orbiting vs static): Derived from `initial_planets` distance from center. Static if `orbital_radius + planet_radius >= 50`. Encoded as a binary feature per planet slot.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After 5000 episodes of training vs agent_v64, the policy achieves ≥5% win rate (50-game eval, side-swapped).
- **SC-002**: The agent dispatches an average of ≥2 fleets per turn across a 500-step game (up from the current 1-fleet limit).
- **SC-003**: The observation encoder correctly encodes all 40 planets in a test game with 40 planets (verified by reading back the vector).
- **SC-004**: The exported agent file passes Principle VI self-containment check and runs in the kaggle sandbox.
- **SC-005**: P99 per-turn inference time remains < 100ms (12.5% of 800ms budget).

## Assumptions

- Training continues on Apple Silicon (M-series) with MLX backend for GPU acceleration.
- The multi-fleet action is implemented as multiple independent action heads (not a sequential policy). Each fleet slot's action is sampled independently, then fleets with source=target or invalid sources are dropped.
- Moving planet positions are NOT dynamically predicted in the observation encoder; only the `planet_type` flag and current position are encoded. Future work could add positional prediction.
- The observation vector size change (319 → ~644) requires re-architecting the policy network's input layer, but the 2×256 MLP backbone remains unchanged.
- The export pipeline's numpy forward pass must be updated to match the new observation layout.
- MAX_COMETS remains at 10; comet path prediction uses the next 2 waypoints encoded as delta-x, delta-y.
- The garrison floor factor (3× production) from the previous RL setup is preserved for computing surplus.
