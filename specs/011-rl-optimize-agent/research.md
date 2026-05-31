# Research: RL-Optimized Agent

**Branch**: `011-rl-optimize-agent` | **Date**: 2026-05-31

## Decision 1: RL Algorithm Selection

**Decision**: Try PPO (primary), DQN (comparison), and A2C (ablation) — promote the highest scorer that reaches ≥55% vs agent_v38.

**Rationale**:
- PPO is the most proven algorithm for multi-agent competitive games with long episode horizons. Its on-policy nature aligns with self-play (always training on current vs. current), and GAE handles long-horizon credit assignment better than DQN's 1-step TD.
- DQN's experience replay is more sample-efficient per interaction — valuable because kaggle-environments Python simulation is slow (~0.5–2 seconds/episode). If simulation is the binding bottleneck, DQN may reach 55% faster in wall-clock time.
- A2C is PPO without the clipping loss. Running it alongside PPO lets us measure whether clipping adds value; the result informs future algorithm choices.

**Alternatives considered**:
- SAC/TD3: Designed for continuous action spaces — not applicable to discrete fleet dispatch.
- REINFORCE: Too high variance for reliable convergence; only useful as a sanity-check baseline.
- RLlib: Designed around padded fixed-size obs; painful to customize for variable-length inputs and heavy on dependencies.

## Decision 2: Observation Encoding

**Decision**: Sorted fixed-size padded vector, 319 floats total.

Layout:

| Slot | Count | Features | Subtotal |
| ---- | ----- | -------- | -------- |
| Planets | 12 max | owner (3-bit one-hot), x, y, ships_norm, production_norm | 84 |
| Fleets | 30 max | owner (3-bit one-hot), x, y, ships_norm | 150 |
| Comets | 10 max | x, y, ships_norm | 30 |
| Globals | 1 | player_id, angular_velocity, turn_number | 3 |
| **Total** | | | **267 features + 52 mask bits = 319** |

Sorting: planets by angular position, fleets by distance from nearest own planet, comets by path_index ascending (soonest-expiring first). Missing slots padded with zeros; boolean mask bits appended so the network learns to ignore them.

Owner encoding: 3-bit one-hot (self=`[1,0,0]`, enemy=`[0,1,0]`, neutral=`[0,0,1]`).

**Alternatives considered**: Attention/transformer entity encoder — better in theory (permutation-invariant, no wasted capacity), but requires a custom PyTorch architecture that can't plug into SB3's `MlpPolicy` directly. Deferred if MLP hits a ceiling.

## Decision 3: Action Space

**Decision**: Three factored discrete heads — source planet (12), target planet (12), ship fraction (5).

Fractions: 0.25, 0.5, 0.75, 1.0 of surplus ships, plus no-op (0). Factored heads reduce effective branching factor vs. a flat 720-action space and allow the policy to learn source selection and target selection semi-independently.

Invalid actions (source not owned, source == target, no surplus ships) are masked to −∞ before softmax each turn. This prevents gradient wasted on structurally illegal moves.

**Alternatives considered**: Flat Discrete(720) — works but slows convergence; no structural prior built in.

## Decision 4: Training Loop & Self-Play

**Decision**: CleanRL-style single-file training scripts in `rl/` with staged opponent scheduling.

Self-play schedule:

- Episodes 0–200: vs `"random"` (warm-up, fast games, ensures basic behavior emerges)
- Episodes 200–500: vs agent_v38 (first strong fixed opponent)
- Episodes 500+: 50% vs latest checkpoint, 50% vs agent_v38 (mixed self-play)

Checkpoint every 200 episodes; keep last 5 + best-so-far. OpponentPool selects uniformly from the pool for the self-play 50%.

**Rationale**: Starting against random gives early reward signal before the policy is strong enough to generate informative self-play. Mixing in agent_v38 keeps the training distribution anchored to a known-strong opponent, preventing the policy from only learning to beat old versions of itself.

## Decision 5: Policy Export

**Decision**: Inline numpy weights via base64-encoded pickle.

For a 2–3 layer MLP with 256 units, the forward pass is straightforward to reimplement as numpy matrix multiplications. No torch import needed at inference time — satisfies Principle VI and keeps cold-start time negligible.

Export procedure (`rl/export.py`):

1. Load `.pt` checkpoint
2. Extract `state_dict` tensors as numpy arrays
3. `pickle.dumps(weights)` → `base64.b64encode` → ASCII string
4. Write `agent_vNN.py` from template with hardcoded `WEIGHTS_B64`

Verify numpy inference matches PyTorch to 1e-5 tolerance before each submission.

**Alternatives considered**:
- TorchScript base64: Retains full architecture but requires torch at inference (heavy import, cold-start latency).
- ONNX: Portable but requires `onnxruntime` which may not be in Kaggle sandbox.

## Decision 6: Reward Signal

**Decision**: Use `reward_signal.py`'s `compute_reward()` during training (inlined constants, not imported in agent file). The blended signal (capture bonus + production delta + ship delta + terminal rank) provides per-turn feedback without sparse-reward problems.

The agent file at inference time never calls `compute_reward` — it uses the trained policy. This satisfies Principle VI.

**Alternatives considered**: Terminal-only reward (win/loss) — too sparse for 200-turn games; credit assignment would require many more episodes.

## Decision 7: Python Library

**Decision**: Custom PyTorch training loops (CleanRL-style single files) for full control. No RLlib or SB3 for the primary runs — they add abstraction without benefit for this custom action-masking setup.

SB3 can be used for a quick sanity-check baseline with `MlpPolicy` on the fixed-size obs, but the main training scripts are hand-rolled.

MPS acceleration (`device="mps"`) should be used if available — reduces NN overhead by ~8.8x vs CPU. Simulation is still the dominant cost.
