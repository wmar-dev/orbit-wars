# CLI Contracts: Mid-Game Reward Signals

**Feature**: 008-mid-game-rewards | **Date**: 2026-05-30

## reward_signal.py (Python module API)

Not invoked directly from the CLI. Imported by eval harnesses and agent files.

```python
# Public API
from reward_signal import compute_reward, RewardConfig, zero_reward

compute_reward(
    prev_obs: dict | None,   # observation from previous turn (None on turn 0)
    curr_obs: dict,          # observation from current turn
    player: int,             # player index to compute reward for
    final_rewards: list[float] | None = None,  # game-end rewards (non-None on terminal turn only)
    num_players: int = 2,
) -> dict                    # TurnReward dict (capture_bonus, production_delta, ship_delta, terminal, total)
```

Raises `ValueError` if `curr_obs` is missing required fields (`planets`, `fleets`, `player`, `step`).

---

## eval.py (extended)

```
uv run python eval.py [options]

Options (existing):
  --agent0 PATH     Path to agent 0 file (default: agent_v30.py)
  --agent1 PATH     Path to agent 1 file (default: agent_v30.py)
  --games N         Number of games to run (default: 20)
  --seed N          Starting seed (default: 0)
  --verbose         Print per-turn move logs
  --jobs N          Parallel workers (default: 1)

New option:
  --reward-log PATH Write per-turn, per-player rewards to a .jsonl file.
                    One JSON object per line; schema matches TurnReward.
                    No effect on win/loss output or exit code.
```

Exit codes: unchanged (0 = success).

---

## eval4.py (extended)

```
uv run python eval4.py [options]

Options (existing):
  --agent0 PATH     Path to agent 0 file
  --agent1 PATH     Path to agent 1 file (used for all 3 opponent slots)
  --games N         Number of games (default: 20)
  --seed N          Starting seed (default: 0)
  --jobs N          Parallel workers (default: 1)

New option:
  --reward-log PATH Write per-turn, per-player rewards to a .jsonl file.
                    Produces 4 rows per turn (one per player).
```

---

## reward_analysis.py

```
uv run python reward_analysis.py [options]

Required:
  --log PATH        Path to .jsonl reward log file

Options:
  --games N         Limit analysis to first N games (default: all)
  --player N        Show breakdown for a specific player index (default: all)

Output: Markdown-formatted summary to stdout.

Sections:
  - Overall: avg total reward by winner vs. loser
  - By phase: Early (turns 1-20), Mid (21-60), Late (61+)
    - Per phase: avg total, avg capture_bonus, avg production_delta, avg ship_delta
  - Top-reward turns: top 5 highest-reward events (game, turn, player, component)

Exit codes:
  0   Success
  1   Log file not found or parse error
```
