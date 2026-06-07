# Feature Specification: RL Training

**Feature Branch**: `026-rl-training`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "Let's try RL approach."

## User Scenarios & Testing

### User Story 1 — RL Training Pipeline Setup (Priority: P1)

The existing RL infrastructure (ppo.py, env.py, obs.py) is initial/experimental code that may have bugs or missing features. Before meaningful training can happen, the pipeline must be verified end-to-end: the Gymnasium env correctly wraps the game, the obs encoder produces valid state vectors, action decoding produces legal moves, and PPO training runs without crashes.

**Why this priority**: If the pipeline is broken, no training can proceed. This is the foundation for all RL work.

**Independent Test**: Run `uv run python rl/ppo.py --episodes 10 --opponent random` and confirm it completes without errors, produces a checkpoint file, and logs training episodes.

**Acceptance Scenarios**:

1. **Given** the RL pipeline is set up, **When** I run a 10-episode PPO training run vs `random`, **Then** it completes without exceptions and outputs checkpoint `.npz` and `.pt` files.
2. **Given** the checkpoint is saved, **When** I run with `--resume`, **Then** it loads the previous weights and continues training.
3. **Given** PPO training is running, **When** the agent plays a turn, **Then** the decoded action produces valid `[src_id, angle, ships]` commands.

---

### User Story 2 — Train Against Strong Opponent (Priority: P2)

The RL agent must train against progressively stronger opponents to improve. Currently, training vs `random` only teaches basic mechanics. We need to train against `agent_v64` (the current best heuristic agent, 54% vs v63) as the primary opponent, then self-play against the latest checkpoint, to discover strategies that beat or match the heuristic.

**Why this priority**: The final goal is to beat v64. Training only vs random will never reach that level.

**Independent Test**: Train 1000 episodes vs `agent_v64` and measure average episode reward trending upward over the course of training.

**Acceptance Scenarios**:

1. **Given** training vs `agent_v64`, **When** average episode reward in the last 200 episodes exceeds the first 200 episodes by at least 0.5, **Then** the agent is improving.
2. **Given** a trained checkpoint, **When** evaluated vs `agent_v64` in a 50-game self-play eval with --swap, **Then** win rate ≥ 20% (interim target).

---

### User Story 3 — Evaluate Trained Policy (Priority: P3)

Once a trained checkpoint exists, we need a rigorous evaluation harness that loads the policy network and runs head-to-head games against v64, reporting win rate, average reward, and timing. The eval must use the same logic as the heuristic agents' eval (`eval.py h2h`).

**Why this priority**: Without evaluation, we can't tell if training is improving the agent. The eval harness bridges the RL training loop and the competition evaluation pipeline.

**Independent Test**: Run the eval script with a random-policy baseline and confirm it reports ~50% win rate vs `random` and a plausible timing profile.

**Acceptance Scenarios**:

1. **Given** a trained checkpoint, **When** I run `make eval` against `agent_v64`, **Then** it reports win rate, average reward, and per-turn timing.
2. **Given** a trained checkpoint, **When** evaluated, **Then** p99 per-turn timing < 800ms.

---

### Edge Cases

- What happens when the RL policy produces an invalid action (source = target, or source not owned)? The `decode_action` returns an empty list, and the env returns a no-op turn. Training should penalize this via negative reward.
- What happens when no planets are owned (eliminated)? The env terminates with `done=True` and a negative terminal reward.
- What happens when training runs out of memory? MLX training on Apple Silicon uses unified memory — monitor GPU memory usage with `mx.metal.device_info()`.
- What happens when a checkpoint is loaded from a different network architecture? The `load_checkpoint` will fail with a key mismatch — only load checkpoints from compatible `PolicyNet` structures.

## Requirements

### Functional Requirements

- **FR-001**: The PPO training script MUST complete at least 1000 episodes without crashing when training against `random`.
- **FR-002**: Training MUST produce checkpoint files at regular intervals (every `CHECKPOINT_EVERY` episodes) in both `.npz` and `.pt` formats.
- **FR-003**: The `--resume` flag MUST load the latest checkpoint and continue training from that episode count.
- **FR-004**: Training MUST support `agent_v64` as an opponent string (loaded via `importlib` from the agent file).
- **FR-005**: The observation encoder MUST convert any valid game observation into a fixed-size 319-dim float32 vector without exceptions.
- **FR-006**: The action decoder MUST reject illegal actions (source slot = target slot, source not owned) by returning an empty list.
- **FR-007**: The evaluation harness MUST run a batch of head-to-head games between a loaded policy checkpoint and a heuristic agent file, reporting win rate.
- **FR-008**: The RL environment MUST use Gymnasium's `step/reset` interface so it can be used with standard RL libraries.

### Key Entities

- **PolicyNet**: MLX neural network with 2 hidden layers (256 units), actor heads for source/target/fraction, and a value head. Weights saved as `.npz` and `.pt`.
- **OrbitWarsEnv**: Gymnasium wrapper around the kaggle `orbit_wars` environment. Uses `encode_obs` and `decode_action` from `rl/obs.py`.
- **Observation vector**: 319-dim float32 vector encoding planet/fleet/comet/global state plus action mask bits.
- **Checkpoint**: Saved model weights in `.npz` format (MLX-native) and `.pt` format (torch-compatible for export).

## Success Criteria

### Measurable Outcomes

- **SC-001**: The PPO training pipeline runs 1000 episodes vs `random` without errors, producing checkpoints and logs.
- **SC-002**: After training 5000 episodes vs `agent_v64`, the policy achieves ≥20% win rate vs v64 in a 50-game eval.
- **SC-003**: After training 20000 episodes with self-play escalation (opponent progression), the policy achieves ≥40% win rate vs v64.
- **SC-004**: p99 per-turn timing for the policy network is < 100ms (12.5% of 800ms budget).
- **SC-005**: The final trained policy can be exported to a single-file agent (`main.py`) with all weights inlined, matching the submission format.

## Assumptions

- Training runs on Apple Silicon (M-series) using the MLX framework for GPU acceleration.
- The existing `rl/` directory code (ppo.py, env.py, obs.py, export.py) is functional but may require bug fixes before it runs reliably.
- The `PILLOW` environment variable or virtual env has `kaggle-environments`, `mlx`, `mlx-embedding`, `gymnasium`, `numpy`, and `torch` (for export) installed.
- Training 1000 episodes takes approximately 5-10 minutes on M-series hardware.
- The RL agent uses the same action space as existing code: MultiDiscrete([12, 12, 4]) = source slot, target slot, ship fraction index.
- Self-play escalation follows the existing `get_opponent` schedule: random (0-200), strong heuristic (200-500), then mix of self-play and heuristic.
