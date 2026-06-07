# Contracts: RL Training

## Internal API Contracts

### 1. Observation Encoding Contract

```python
encode_obs(obs, player_id: int) -> (vec: np.ndarray[319], mask: np.ndarray[52])
```

**Producer**: `rl/obs.py::encode_obs`
**Consumer**: `rl/env.py::OrbitWarsEnv.step/reset`
**Guarantees**: Converts any valid kaggle observation to a fixed-size float32 vector. Handles edge cases (empty planets, no comets, missing fleets) by padding with zeros. Mask indicates valid source and target planet slots.

---

### 2. Action Decoding Contract

```python
decode_action(action: np.ndarray[3], obs, player_id: int) -> list[[src_id, angle, ships]]
```

**Producer**: `rl/obs.py::decode_action`
**Consumer**: `rl/env.py::OrbitWarsEnv.step`
**Guarantees**: Converts factored discrete action to kaggle move format. Returns empty list for illegal actions (source=target, source not owned). Fraction indices 0-3 map to 25/50/75/100% of surplus.

---

### 3. Env Interface Contract

```python
class OrbitWarsEnv(gym.Env):
    observation_space: Box(-2.0, 2.0, (319,), float32)
    action_space: MultiDiscrete([12, 12, 4])
    reset(seed) -> (obs[319], info)
    step(action[3]) -> (obs[319], reward, terminated, truncated, info)
```

**Consumer**: `rl/ppo.py` (training loop)
**Backend**: kaggle `orbit_wars` environment with `train()` API for 2-player training.

---

### 4. Checkpoint Save/Load Contract

```python
save_checkpoint(net: PolicyNet, episode: int, score: float, path: str)
load_checkpoint(net: PolicyNet, path: str) -> (episode, score)
```

**Format**: NPZ with dot-separated layer keys (e.g., `fc1.weight`, `actor_src.bias`).
**Metadata keys**: `__episode__` (int array), `__score__` (float array).

---

### 5. Export Contract

```python
export(checkpoint_path: str, output_path: str, algo: str, verify: bool)
```

**Output**: Self-contained Python file with `agent(obs, config)` function.
**Constraints**:
- No local imports (Principle VI compliant)
- Weights inlined as base64-encoded pickle blob
- Numpy forward pass matches MLX forward pass deterministically

---

## External Interface

### Training CLI

```bash
uv run python rl/ppo.py [--episodes N] [--opponent PATH|random] [--checkpoint-dir DIR] [--seed N] [--resume]
```

### Export CLI

```bash
uv run python rl/export.py --checkpoint PATH --output PATH [--algo ppo|dqn|a2c] [--verify]
```
