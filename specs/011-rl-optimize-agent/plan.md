# Implementation Plan: RL-Optimized Agent

**Branch**: `011-rl-optimize-agent` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-rl-optimize-agent/spec.md`

## Summary

Train one or more RL agents (PPO, DQN, and A2C) using self-play against agent_v38 and prior agents. The best-performing RL agent is promoted to a self-contained Python file and submitted to Kaggle. Training uses a gymnasium wrapper over the kaggle-environments orbit_wars env, a sorted fixed-size padded observation vector, and CleanRL-style single-file PPO/DQN/A2C implementations with inline PyTorch. The exported agent inlines its policy weights as a base64-encoded numpy blob, requiring no non-stdlib imports at runtime.

## Technical Context

**Language/Version**: Python 3.14 (repo requirement), PyTorch for training (installed into `.venv`)

**Primary Dependencies**: `kaggle-environments>=1.28.0` (already installed), `torch` (added for training), `gymnasium` (added for training wrapper); inference uses only `numpy`, `math`, `base64`, `pickle` — all stdlib/numpy.

**Storage**: Flat files at repo root (`agent_vNN.py`), checkpoints in `rl/checkpoints/` (`.pt` files), training logs in `rl/logs/` (CSV), experiment records in `experiments/` (Markdown).

**Testing**: `eval.py --agent0 agent_vNN.py --agent1 agent_v38.py --games 50 --seed 0` (win rate), `diagnose_v9.py` (safety audit), `make test` (smoke test vs random).

**Target Platform**: Local macOS development (training), Kaggle submission sandbox (inference). MPS acceleration available if Apple Silicon.

**Project Type**: Competitive game agent — trained offline, exported as single-file inference script.

**Performance Goals**: ≥55% score vs agent_v38 (50 games); >763.2 Kaggle public score. Inference <1 second/turn.

**Constraints**: Exported agent file MUST be self-contained (Principle VI). No local module imports in submitted file. All RL training scaffolding lives in `rl/` and is never submitted. Each candidate RL agent gets its own experiment record in `experiments/` before submission.

**Scale/Scope**: 3 RL algorithm candidates (PPO, DQN, A2C), each trained for 1,000–5,000 episodes. ~2–6 hours per run on CPU; ~1–3 hours with MPS. 3 experiment records + up to 3 Kaggle submissions.

**Key observation schema** (from CONTEST.md):

- `obs.planets` → list of `[id, owner, x, y, radius, ships, production]`
- `obs.fleets` → list of `[id, owner, x, y, angle, from_planet_id, ships]` — no `to_planet_id`
- `obs.initial_planets` → list of initial planet states (for orbit-lead)
- `obs.angular_velocity` → float (radians/turn)
- `obs.comets` → list with `paths` and `path_index`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Reinforcement Learning First | ✅ Pass | This feature **is** the RL path. Directly fulfills Principle I. |
| II. Fair Play & Rules Compliance | ✅ Pass | No game engine modifications. actTimeout <1s enforced via numpy inference (no torch at runtime). |
| III. Manual Submissions Only | ✅ Pass | No automated submission pipeline. `make submit` remains manual. |
| IV. Experiment & Improvement Documentation | ✅ Pass | Experiment records in `experiments/` required for each RL candidate before Kaggle submission. |
| V. Local Self-Play as Primary Evaluation Loop | ✅ Pass | All candidates evaluated ≥50 games vs agent_v38 before submission. |
| VI. Self-Contained Agent Files | ✅ Pass | Exported agent inlines weights as base64+numpy; no local module imports. |

**Result**: All gates pass. Proceeding to implementation.

---

## Project Structure

### Documentation (this feature)

```text
specs/011-rl-optimize-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
rl/
├── env.py               # OrbitWarsEnv: gymnasium wrapper over kaggle-environments
├── obs.py               # encode_obs(): variable-length → fixed-size padded vector
├── ppo.py               # CleanRL-style PPO training loop (single file)
├── dqn.py               # DQN training loop with prioritized replay
├── a2c.py               # A2C training loop (PPO variant, simpler)
├── export.py            # Dump trained weights → base64 numpy blob for embedding
├── checkpoints/         # Saved .pt checkpoints (gitignored if large)
└── logs/                # Training CSV logs

agent_v39.py             # PPO RL agent (first exported candidate)
agent_v40.py             # DQN RL agent (if PPO passes; else A2C)
agent_v41.py             # Best combined or next candidate

experiments/
├── 011-rl-ppo-baseline.md
├── 011-rl-dqn-baseline.md
└── 011-rl-a2c-baseline.md
```

**Structure Decision**: New `rl/` directory for all training scaffolding, keeping repo root clean for agent files. `rl/` files are never submitted to Kaggle. Agent files follow existing `agent_vNN.py` naming convention.

---

## Phase 0: Research

*All unknowns from Technical Context resolved below.*

### Decision 1: RL Algorithm Selection

**Decision**: Try three algorithms in parallel — PPO (primary), DQN (comparison), A2C (ablation). Promote whichever reaches ≥55% vs agent_v38 first; if multiple pass, promote the highest scorer.

**Rationale**:

- PPO is the most proven algorithm for multi-agent competitive games with long horizons (~200 turns). On-policy nature aligns well with self-play (always training on current policy vs. current opponent). GAE handles long-horizon credit assignment better than DQN's 1-step TD.
- DQN has better sample efficiency per interaction — important because kaggle-environments Python simulation is slow (~0.5–2 seconds/episode). If simulation is the bottleneck, experience replay lets DQN reuse each episode more times.
- A2C is a simplified PPO without the clipping loss — useful as an ablation to verify that PPO's clipping adds value. Runs faster per update.

**Alternatives considered**: SAC/TD3 (continuous action spaces only — not applicable), REINFORCE (too high variance, impractical), RLlib (too complex and fights variable-length obs design).

### Decision 2: Observation Encoding

**Decision**: Sorted fixed-size padded vector.

- Max 12 planets (7 features each: owner_enc×3, x, y, ships_norm, production_norm)
- Max 30 fleets (5 features each: owner_enc×3, x, y, ships_norm)
- Max 10 comets (3 features each: x, y, ships_norm)
- Global features: player_id, angular_velocity, turn_number
- Total: 12×7 + 30×5 + 10×3 + 3 = **84 + 150 + 30 + 3 = 267 features**
- Padding mask: 12 + 30 + 10 = **52 boolean mask bits**
- **Final observation vector: 319 floats**

Sorting: planets by angular position (canonical reference), fleets by distance from nearest own planet, comets by path_index (time-to-expiry).

Owner encoding: 3-bit one-hot (self=100, enemy=010, neutral=001).

**Alternatives considered**: Attention/transformer entity encoder — better long-term but requires custom PyTorch arch and more complex SB3 integration. Deferred to a future round if MLP approach hits ceiling.

### Decision 3: Action Space

**Decision**: Factored discrete action — two independent heads:

1. **Source planet**: Discrete(12) — which of the agent's owned planets to send from
2. **Target planet**: Discrete(12) — which planet to send to
3. **Ship fraction**: Discrete(5) — what fraction of surplus ships to send (0.25, 0.5, 0.75, 1.0, 0=no-op)

Total flat space would be 12×12×5 = 720. Factored heads reduce effective space and training difficulty. Invalid actions (source not owned, source == target, no surplus ships) are masked to zero probability before softmax.

**Action masking**: A boolean mask is computed each turn from observation and applied to logits before sampling. Prevents wasted gradient on illegal actions.

### Decision 4: Training Loop & Self-Play

**Decision**: CleanRL-style single-file training scripts (`rl/ppo.py`, `rl/dqn.py`, `rl/a2c.py`) with periodic opponent checkpointing.

Self-play schedule:

1. **Episodes 0–200**: Train vs built-in `"random"` opponent (warm-up)
2. **Episodes 200–500**: Train vs agent_v38 (first strong opponent)
3. **Episodes 500+**: Train 50% vs latest checkpoint, 50% vs agent_v38 (self-play mix)

Checkpoint every 200 episodes. Keep last 5 checkpoints + best-so-far.

### Decision 5: Policy Export

**Decision**: Inline numpy weights via base64-encoded pickle (Option A from research).

For an MLP policy (2–3 layers, 256 units), the forward pass is simple enough to reimplement as numpy matrix multiplications. No torch required at inference time. This satisfies Principle VI and keeps inference fast (<1ms).

Export script (`rl/export.py`):

1. Load checkpoint `.pt`
2. Extract weight tensors as numpy arrays
3. `pickle.dumps` + `base64.b64encode`
4. Write embedded agent template with hardcoded WEIGHTS_B64 string

### Decision 6: Reward Signal

**Decision**: Use `reward_signal.py`'s `compute_reward()` output directly during training, but **inline the reward constants into the training script** (not imported from `reward_signal.py` in the agent file itself). The agent file never calls `compute_reward` at inference — it uses the trained policy.

The existing blended reward (capture bonus + production delta + ship delta + terminal signal) provides a rich per-turn signal; no additional shaping needed for baseline experiments.

---

## Phase 1: Design & Data Model

### Key Entities

See [data-model.md](data-model.md) for full entity specifications.

**Summary**:

- `OrbitWarsEnv` — gymnasium wrapper; manages episode lifecycle, obs encoding, action decoding
- `ObsEncoder` — stateless function: raw kaggle obs → 319-float numpy vector + 52-bool action mask
- `PolicyNetwork` — PyTorch MLP; input 319 floats → source logits (12), target logits (12), fraction logits (5)
- `Checkpoint` — `.pt` file: `{policy_state_dict, episode, score_vs_v38, timestamp}`
- `ExportedAgent` — `agent_vNN.py` file: hardcoded WEIGHTS_B64 + numpy inference loop

### Interface Contracts

No external API. The agent interface is defined by Kaggle:

```python
def agent(obs, config) -> list[dict]:
    # Returns list of fleet dispatch commands:
    # [{"source": int, "destination": int, "num_ships": int}, ...]
```

The training scripts in `rl/` are internal tools; no external contracts needed.

### Implementation Phases

**Phase A — Environment Wrapper** (prerequisite for all training)

1. Implement `rl/obs.py`: `encode_obs(obs) -> (np.ndarray[319], np.ndarray[52])`
2. Implement `rl/env.py`: `OrbitWarsEnv(gymnasium.Env)` using kaggle trainer API
3. Smoke test: run 1 episode, verify obs shape and reward signal are non-trivial

**Phase B — PPO Baseline** (first candidate, highest priority)

1. Implement `rl/ppo.py`: CleanRL PPO with action masking, GAE, 2 parallel envs
2. Train 1,000 episodes vs agent_v38; verify reward curve is increasing
3. Export checkpoint → `agent_v39.py`; run `eval.py` 50 games vs agent_v38
4. Record result in `experiments/011-rl-ppo-baseline.md`

**Phase C — DQN Comparison** (second candidate)

1. Implement `rl/dqn.py`: DQN with prioritized experience replay, action masking
2. Train 1,000 episodes; compare wall-clock time and win-rate curve vs PPO
3. Export → `agent_v40.py` (if PPO passed) or replace v39 (if PPO failed)
4. Record result in `experiments/011-rl-dqn-baseline.md`

**Phase D — A2C Ablation** (third candidate, optional if PPO+DQN both pass)

1. Implement `rl/a2c.py`: PPO without clipping (A2C); validate that PPO clipping helps
2. Export → `agent_v41.py` if better than v39/v40
3. Record result in `experiments/011-rl-a2c-baseline.md`

**Phase E — Promotion & Submission** (gate: ≥55% vs agent_v38)

1. Run `diagnose_v9.py` on best RL agent (0 sun/OOB requirement)
2. Verify self-containment: `grep -n "^from \|^import "` against Principle VI allowlist
3. `make submit MESSAGE="RL PPO agent, X% vs v38"`
4. Update SUBMISSIONS.md with returned score
5. Update README.md Agents table; update Makefile `AGENT` if RL agent beats v38 locally

---

## Complexity Tracking

No constitution violations. No complexity justification needed.
