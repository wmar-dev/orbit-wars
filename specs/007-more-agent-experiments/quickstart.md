# Quickstart: Agent Improvement Experiments — Round 3

**Branch**: `007-more-agent-experiments` | **Date**: 2026-05-30

## Prerequisites

```bash
uv venv .venv
uv pip install --python .venv "kaggle-environments>=1.28.0"
```

## Running Experiments

### 2-Player Evaluation (primary gate)

```bash
# Evaluate a new candidate against agent_v20 (20 games, seeds 0-19)
uv run python eval.py --agent0 agent_v21.py --agent1 agent_v20.py --games 20 --seed 0

# Pass threshold: ≥55% win rate
```

### 4-Player Evaluation (supplementary diagnostic)

```bash
# Establish baseline: test agent vs 3 random opponents (20 games)
uv run python eval4.py --agent agent_vN.py --opponent random --games 20

# Compare against competent opponents: test agent vs 3× agent_v20
uv run python eval4.py --agent agent_vN.py --opponent agent_v20.py --games 20

# Diagnose regression: compare v8 vs v20 in 4-player
uv run python eval4.py --agent agent_v8.py --opponent random --games 20
uv run python eval4.py --agent agent_v20.py --opponent random --games 20

# Pass threshold for 4P mechanics: average rank ≤ 2.0
```

### Render a Game (visual inspection)

```bash
# 2-player visual render
make render2 RENDER_AGENT=agent_v21.py RENDER_OPPONENT=agent_v20.py

# 4-player visual render (all 4 slots use same agent)
make render4 RENDER_AGENT=agent_v21.py
```

### Safety Audit (run on combined agent only)

```bash
uv run python diagnose_v9.py --agent agent_v25.py --games 20
# Expected: 0 sun losses, 0 OOB losses
```

## Experiment Workflow (per candidate)

1. Write experiment record in `experiments/YYYY-MM-DD-candidate-[name].md` (do this FIRST)
2. Create agent file `agent_vN.py` (copy from agent_v20.py, add mechanic, update docstring)
3. Run 2-player eval: `eval.py --agent0 agent_vN.py --agent1 agent_v20.py --games 20`
4. Record result in experiment file (PASS if ≥55%)
5. Run 4-player visual: `make render4 RENDER_AGENT=agent_vN.py` (optional, for qualitative inspection)
6. Update README.md Agents table

## Building the Combined Agent (agent_v25)

1. Identify all candidates with ≥55% vs agent_v20
2. Stack mechanics in integration order (from plan.md Phase 0 D-005):
   - Adaptive range (J)
   - 4P opponent ranking (M, N)
   - Reactive defense (I)
   - Enemy-priority ROI (K) + 4P multipliers
   - Two-source attack (L) as fallback
3. Run: `eval.py --agent0 agent_v25.py --agent1 agent_v20.py --games 20` (target ≥65%)
4. Run: `eval4.py --agent agent_v25.py --opponent random --games 20` (target avg rank ≤ 2.0)
5. Run: `diagnose_v9.py --agent agent_v25.py --games 20` (must be 0 sun/OOB losses)
6. Update README.md (bold the new best agent if it passes all gates)

## Round Iteration Protocol

If agent_v25 does not beat agent_v20 by ≥65%:
1. Test mechanic subsets to find regressions
2. Revise failing hypotheses — write new experiment records
3. Begin Round 4: candidates become v26–v29, combined is v30
4. Repeat until a new best combined agent exists
