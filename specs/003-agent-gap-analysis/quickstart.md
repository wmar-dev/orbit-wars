# Quickstart: Running the Experiments

**Feature**: 003-agent-gap-analysis | **Date**: 2026-05-29

## Prerequisites

```bash
uv sync   # install kaggle-environments if not already present
```

## Run isolated experiments (in parallel across terminals or tmux panes)

Each command is independent — run all four simultaneously:

```bash
# Terminal 1 — orbit-lead targeting
uv run python eval.py --agent0 agent_v4.py --agent1 agent_v3.py --games 20 --jobs 4

# Terminal 2 — comet opportunism
uv run python eval.py --agent0 agent_v5.py --agent1 agent_v3.py --games 20 --jobs 4

# Terminal 3 — defensive reinforcement
uv run python eval.py --agent0 agent_v6.py --agent1 agent_v3.py --games 20 --jobs 4

# Terminal 4 — fleet-speed scoring + fast-fleet send
uv run python eval.py --agent0 agent_v7.py --agent1 agent_v3.py --games 20 --jobs 4
```

## Run combined agent (after isolated results are known)

```bash
uv run python eval.py --agent0 agent_v8.py --agent1 agent_v3.py --games 20 --jobs 4
```

## Confirm win rate threshold

Pass = agent0 win rate ≥ 55% over 20 games (11+ wins).

## Verbose debugging (single game)

```bash
uv run python eval.py --agent0 agent_v4.py --agent1 agent_v3.py --games 1 --verbose
```

## Verify a single agent runs without error

```bash
uv run python agent_v4.py
```

The `if __name__ == "__main__":` block at the bottom of each agent runs one game vs
`main.py` on seed 42 and prints final rewards.

## Reproduce agent_v3 baseline

```bash
uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 10 --jobs 4
# Expected: ~90% win rate for agent_v3
```
