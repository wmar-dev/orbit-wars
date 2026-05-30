# CLI Contract: eval.py — Experiment Evaluation with Reward Logging

**Feature**: 009-fix-comet-fleet-targeting | **Date**: 2026-05-30

This contract documents the `eval.py` command interface as used in this feature's experiment workflow. The eval harness itself is **not modified**; this documents the calling convention.

---

## Standard Evaluation (Win-Rate Gate)

```bash
uv run python eval.py \
  --agent0 <candidate>.py \
  --agent1 agent_v32.py \
  --games 50 \
  --jobs 4
```

**Required flags**:

| Flag | Value | Purpose |
|------|-------|---------|
| `--agent0` | `<candidate>.py` | Agent under test (candidate mechanic) |
| `--agent1` | `agent_v32.py` | Fixed baseline (bugs corrected) |
| `--games` | `50` | Sample size for pass/fail gate |
| `--jobs` | `4` | Parallel workers (adjust to available cores) |

**Output**: Win/loss/draw per game + aggregate win rate. Pass if agent0 win rate ≥ 55%.

---

## Reward-Augmented Evaluation (Secondary Signal)

```bash
uv run python eval.py \
  --agent0 <candidate>.py \
  --agent1 agent_v32.py \
  --games 50 \
  --jobs 4 \
  --reward-log experiments/009-candidate-<X>.jsonl
```

**Additional flag**:

| Flag | Value | Purpose |
|------|-------|---------|
| `--reward-log` | `experiments/009-candidate-<X>.jsonl` | Writes per-turn, per-player rewards to JSON Lines file |

**Reward log format**: One JSON object per line:
```json
{"game_id": 0, "seed": 0, "step": 42, "player": 0,
 "capture_bonus": 0.3, "production_delta": 0.1, "ship_delta": -0.05,
 "terminal": null, "total": 0.18}
```

---

## Reward Analysis (Post-Run)

```bash
uv run python reward_analysis.py experiments/009-candidate-<X>.jsonl
```

Reports:
- Mean per-turn reward by player across all games
- Mean reward delta (agent0 − agent1); positive = candidate better mid-game
- Breakdown by component (capture_bonus, production_delta, ship_delta)

**Interpretation**: Mean reward delta is **informational only**. It does not substitute for the 55% win-rate gate. A candidate with positive reward delta but <55% win rate is noted in the experiment record as "promising — revisit at higher N or in combination."

---

## Experiment Record Convention

For each candidate run, create `experiments/009-candidate-<X>.md` with:

```markdown
# Candidate <X> Retest — 009-fix-comet-fleet-targeting

**Date**: YYYY-MM-DD
**Hypothesis**: <why this candidate might pass vs. v32>
**Change**: <what differs from agent_v32>

## Self-Play Result (50 games, agent0 = candidate, agent1 = agent_v32)

- Win rate: XX.X%  (draws count as losses)
- Score:    XX.X%  (draws count as 0.5)
- Wins / Draws / Losses: W / D / L
- Mean reward delta (candidate - v32): ±X.XX

## Conclusion

**PASS / FAIL** (≥55% win rate gate)

<Narrative: what was learned, whether to promote, stack, or discard>
```
