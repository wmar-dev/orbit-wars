# Quickstart: Agent Experiments Round 3

## Prerequisites

```bash
uv run python -c "from kaggle_environments import make; print('OK')"
```

## Create the Experimental Agent

```bash
cp agent_v62.py agent_v63.py
```

Toggle the experiments by editing `agent_v63.py` constants at the top of the file (lines 40-47).

## Run Experiments

### 1. Defense Interceptor Evaluation

```bash
# Control: interceptor OFF
# Edit agent_v63.py → set DEFENSE_INTERCEPT_ENABLED = False
# Then vs baseline v62:
uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap

# Then restore: set DEFENSE_INTERCEPT_ENABLED = True
```

### 2. Deep Search Evaluation

```bash
# Edit SEARCH_DEPTH and/or BEAM_K in agent_v63.py
# Test depth=15:
uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap

# Test depth=20:
# (edit SEARCH_DEPTH=20)
uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap

# Test beam width=5:
# (edit BEAM_K=5, restore SEARCH_DEPTH=10)
uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap
```

### 3. Corrected Weighted Eval

```bash
# Set WEIGHTED_EVAL_FIXED_ENABLED = True (leave other toggles same as v62)
uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap
```

### 4. Combined Configuration

```bash
# Enable all passing experiments
uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap
```

### 5. Opponent Sweep

```bash
uv run python eval.py opponents --agent agent_v63.py --games 20
```

## Record Results

All results go in:

```
experiments/2026-06-06-experiments-round3.md
```

See the experiment schema in [data-model.md](data-model.md) for the required format.

## Submit to Kaggle

```bash
# Only if combined win rate > 50% vs v62
make submit MESSAGE="agent_v63: experiments round 3, XX% vs v62"
```

## Common Options

- Use `--swap` for all head-to-head evals (each agent plays both sides equally)
- Use `--games N` to change sample size (default 50)
- Use `--verbose` to see per-turn move logs
