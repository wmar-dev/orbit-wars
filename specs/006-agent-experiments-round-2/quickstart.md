# Quickstart: Agent Experiments Round 2

**Branch**: `006-agent-experiments-round-2` | **Date**: 2026-05-30

## Prerequisites

```bash
# Verify baseline
uv run python eval.py --agent0 agent_v15.py --agent1 agent_v15.py --games 5
```

Expect ~50% win rate (self-play is symmetric). Any other result indicates a broken eval setup.

## Experiment Workflow (per candidate)

### Step 1 — Write experiment record first (Constitution IV)

```bash
# Create before writing any agent code
touch experiments/2026-05-30-candidate-e-orbit-lead-fix.md
```

Minimum required fields: Hypothesis, Change, Self-play result (fill after eval), Conclusion (fill after eval).

### Step 2 — Implement agent

Each candidate inherits agent_v15. Only the mechanic under test changes. See [data-model.md](data-model.md) for the exact formula per candidate.

### Step 3 — Evaluate

```bash
# 20 games, seeds 0–19
uv run python eval.py --agent0 agent_v16.py --agent1 agent_v15.py --games 20 --seed 0

# Optional: parallel jobs for speed (if supported)
uv run python eval.py --agent0 agent_v16.py --agent1 agent_v15.py --games 20 --seed 0 --jobs 4
```

Pass threshold: ≥55% win rate (≥11 wins out of 20).

### Step 4 — Record results and update README

Fill in the Self-play result and Conclusion in the experiment record. Update the README Agents table.

---

## All Candidates at a Glance

| Candidate | Agent | Command |
| --------- | ----- | ------- |
| E — speed-corrected orbit lead | agent_v16 | `eval.py --agent0 agent_v16.py --agent1 agent_v15.py --games 20 --seed 0` |
| F — transit-adjusted fleet sizing | agent_v17 | `eval.py --agent0 agent_v17.py --agent1 agent_v15.py --games 20 --seed 0` |
| G — adaptive range expansion | agent_v18 | `eval.py --agent0 agent_v18.py --agent1 agent_v15.py --games 20 --seed 0` |
| H — capture-ROI scoring | agent_v19 | `eval.py --agent0 agent_v19.py --agent1 agent_v15.py --games 20 --seed 0` |
| Combined | agent_v20 | `eval.py --agent0 agent_v20.py --agent1 agent_v15.py --games 20 --seed 0` |

---

## Combined Agent Diagnostic

Run this only after all candidates are evaluated and agent_v20 is built:

```bash
uv run python diagnose_v9.py --agent agent_v20.py --games 20
```

Expected: 0 sun losses, 0 OOB losses (SC-004).

---

## Debugging Orbit-Lead Accuracy (Candidate E)

To verify the orbit-lead fix is actually improving aim:

```bash
# Run with verbose to see fleet paths
uv run python eval.py --agent0 agent_v16.py --agent1 agent_v15.py --games 3 --verbose
```

Look for fleets that reach the predicted position but find the target planet slightly offset — this indicates the two-iteration refinement isn't fully converged and a third iteration may help.

---

## Decision Table

After all 4 candidates are evaluated:

| All pass ≥55%? | Build agent_v20 with all 4 |
| Only some pass? | Build agent_v20 with only passing mechanics |
| None pass? | No combined agent; document all results; re-hypothesize for round 3 |
| agent_v20 < 65%? | Test mechanic subsets to isolate regression; exclude lowest-margin mechanic |
