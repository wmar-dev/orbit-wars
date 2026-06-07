# Quickstart: Experiments Round 4

**Date**: 2026-06-06 | **Plan**: [plan.md](plan.md)

## Setup

```bash
make install        # ensure kaggle-environments installed
```

## Smoke Test (Single Game)

```bash
# Verify agent_v64 runs without errors
python -c "
from kaggle_environments import make
env = make('orbit_wars', configuration={'seed': 42}, debug=True)
from agent_v64 import agent
env.run([agent, 'main.py'])
final = env.steps[-1]
for i, s in enumerate(final):
    print(f'Player {i}: reward={s[\"reward\"]}, status={s[\"status\"]}')
"
```

Smoke test should complete without exceptions and print four player results.

## Experiment 1: Opponent Model v3 (P1)

```bash
# Toggle ON vs v63 baseline
python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing
```

Expected: ≥52% win rate, p99 timing < 100ms.

## Experiment 2: Multi-Turn Planning (P2)

```bash
# Toggle ON vs v63 baseline
python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing
```

Expected: ≥52% win rate, at least one "skip" candidate generated per turn.

## Experiment 3: Phase Detection (P3)

```bash
# Toggle ON vs v63 baseline
python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing
```

Expected: ≥52% win rate.

## Opponent Sweep

For any passing experiment:

```bash
python eval.py agent_v64.py agents/slawekbiel/main.py --games 20
python eval.py agent_v64.py agents/sigmaborov/main.py --games 20
python eval.py agent_v64.py agents/dylanxue04/main.py --games 20
python eval.py agent_v64.py agents/yusufmurtaza/main.py --games 20
```

Expected: >0% win rate vs slawekbiel (gap begins to close), no regression on other opponents.

## Combined Configuration

Run with all passing experiments enabled:

```bash
python eval.py agent_v64.py agent_v63.py --games 50 --swap --timing
```

## Timing Benchmark

```bash
python eval.py agent_v64.py agent_v63.py --games 10 --timing
```

Check p50/p95/p99 in output. Expected: p99 stays under 100ms.
