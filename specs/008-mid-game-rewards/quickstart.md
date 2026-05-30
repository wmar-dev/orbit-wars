# Quickstart: Mid-Game Reward Signals

**Feature**: 008-mid-game-rewards | **Date**: 2026-05-30

## Step 1: Collect a reward log

Run 50 games between `agent_v30` and `agent_v3`, saving per-turn rewards:

```bash
uv run python eval.py \
  --agent0 agent_v30.py \
  --agent1 agent_v3.py \
  --games 50 \
  --seed 0 \
  --jobs 4 \
  --reward-log rewards_v30_vs_v3.jsonl
```

Output: `rewards_v30_vs_v3.jsonl` (one JSON object per turn per player).

## Step 2: Inspect the reward log

Each line of the `.jsonl` file looks like:

```json
{"game_id": 0, "seed": 0, "step": 3, "player": 0, "capture_bonus": 0.12, "production_delta": 0.06, "ship_delta": -0.02, "terminal": null, "total": 0.07}
```

## Step 3: Run replay analysis

```bash
uv run python reward_analysis.py \
  --log rewards_v30_vs_v3.jsonl \
  > analysis_v30_vs_v3.md
```

Check that `agent_v30` (the winner) has higher average reward across all phases.

## Step 4: Evaluate the reward-guided agent

```bash
uv run python eval.py \
  --agent0 agent_v31.py \
  --agent1 agent_v30.py \
  --games 50 \
  --seed 0 \
  --jobs 4 \
  --reward-log rewards_v31_vs_v30.jsonl
```

Target: `agent_v31` wins ≥ 55% (≥ 28/50 games).

## Step 5: Record the experiment

Create `experiments/2026-05-30-reward-signal-baseline.md`:

```markdown
## Hypothesis
Blending reward-signal estimates into ROI target scoring (REWARD_ALPHA=0.3)
will improve win rate vs. agent_v30 by rewarding planet-capture-dense strategies.

## Change
- Added reward_signal.py (W_CAPTURE=0.5, W_PRODUCTION=0.3, W_SHIP=0.2)
- agent_v31.py: REWARD_ALPHA=0.3, blends reward estimate with ROI per target

## Self-play result
Win rate vs. agent_v30 over 50 games: XX% (PASS/FAIL at 55%)

## Conclusion
[Decision and observations]
```

## Tuning reward weights

Edit the constants block at the top of `reward_signal.py`:

```python
W_CAPTURE    = 0.5   # increase to reward aggressive expansion
W_PRODUCTION = 0.3   # increase to reward production-rate growth
W_SHIP       = 0.2   # increase to reward ship-count preservation
CAPTURE_SCALE = 10.0
PROD_SCALE    = 5.0
SHIP_SCALE    = 20.0
```

Edit `REWARD_ALPHA` in `agent_v31.py` to control heuristic/reward blend ratio.
