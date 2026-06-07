# Contracts: RL Full Observation

## Observation Encoding Contract

```python
encode_obs(obs, player_id: int) -> (vec: np.ndarray[560], mask: np.ndarray[80])
```

**Producer**: `rl/obs.py::encode_obs`
**Consumer**: `rl/env.py::OrbitWarsEnv.step/reset`
**Guarantees**: Converts any valid kaggle observation to a fixed-size float32(560) vector. Handles edge cases by zero-padding unused slots. Mask[0:40] = source-valid, mask[40:80] = target-valid.

---

## Action Decoding Contract

```python
decode_action(action: np.ndarray[15], obs, player_id: int) -> list[[src_id, angle, ships]]
```

**Producer**: `rl/obs.py::decode_action`
**Consumer**: `rl/env.py::OrbitWarsEnv.step`
**Guarantees**: Converts 15-value factored action (5 slots × 3 values) to kaggle move list. Drops invalid fleet actions silently. Max 5 fleets per turn.

---

## Env Interface Contract

```python
class OrbitWarsEnv(gym.Env):
    observation_space: Box(-2.0, 2.0, (560,), float32)
    action_space: MultiDiscrete([40, 40, 4] × 5)  # Tuple of 5 × 3 ints
    reset(seed) -> (obs[560], info)
    step(action[15]) -> (obs[560], reward, terminated, truncated, info)
```

**Consumer**: `rl/ppo.py` (training loop)

---

## PolicyNet Forward Contract

```python
net.__call__(x: mx.array[560]) -> (
    src_logits: list[mx.array[5, 40]],
    tgt_logits: list[mx.array[5, 40]],
    frac_logits: list[mx.array[5, 4]],
    value: mx.array[1]
)
```

**Consumer**: `rl/ppo.py::get_action_and_value`

---

## Export Contract

```python
export(checkpoint_path: str, output_path: str, algo: str, verify: bool)
```

**Output**: Self-contained Python file with `agent(obs, config)` function. Inlined numpy forward pass matches MLX forward pass. Principle VI compliant.
