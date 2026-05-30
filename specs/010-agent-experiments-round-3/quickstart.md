# Quickstart: Agent Improvement Experiments — Round 6

**Branch**: `010-agent-experiments-round-3` | **Date**: 2026-05-30

## Prerequisites

- Python 3.11+, `kaggle_environments` installed
- `eval.py`, `diagnose_v9.py`, `reward_signal.py` at repo root (unchanged)
- Current branch: `010-agent-experiments-round-3`
- Baseline: `agent_v33.py` (60% vs agent_v32, 50 games)

## Experiment Workflow

### Step 1: Write experiment record BEFORE coding

For each candidate, create the experiment record first:

```bash
# Example for Candidate S
touch experiments/010-candidate-S-fleet-dedup.md
# Fill in: hypothesis, change description, pass threshold (≥55% vs agent_v33)
```

### Step 2: Implement candidate agent

Each candidate is a standalone `.py` file built on `agent_v33.py`:

```bash
cp agent_v33.py agent_v34.py  # Candidate S (fleet dedup)
cp agent_v33.py agent_v35.py  # Candidate T (transit sizing)
cp agent_v33.py agent_v36.py  # Candidate U (threat garrison)
cp agent_v33.py agent_v37.py  # Candidate V (winning throttle)
```

Edit each file to add the specific mechanic. Update the docstring listing what was added.

### Step 3: Evaluate each candidate

```bash
# Standard 50-game evaluation
python eval.py --agent0 agent_v34.py --agent1 agent_v33.py --games 50 --seed 0
python eval.py --agent0 agent_v35.py --agent1 agent_v33.py --games 50 --seed 0
python eval.py --agent0 agent_v36.py --agent1 agent_v33.py --games 50 --seed 0
python eval.py --agent0 agent_v37.py --agent1 agent_v33.py --games 50 --seed 0
```

**Pass threshold**: ≥55% score (score = wins + 0.5×draws / 50)

**Borderline (50–55%)**: Extend to 100 games before excluding:
```bash
python eval.py --agent0 agent_vN.py --agent1 agent_v33.py --games 100 --seed 0
```

### Step 4: Build combined agent from passing mechanics

After identifying passing candidates, create `agent_v38.py` combining all of them:

```bash
# Combined agent (built on agent_v33 + all passing mechanics)
# Stack mechanics in order: fleet parse → threat floor → garrison factor → transit sizing → dedup
```

```bash
python eval.py --agent0 agent_v38.py --agent1 agent_v33.py --games 50 --seed 0
```

**Combined pass gate**: ≥65% score over 50 games.

### Step 5: Safety audit

```bash
python diagnose_v9.py --agent agent_v38.py --games 50 --seed 0
# Required: 0 sun losses, 0 OOB losses
```

### Step 6: Update README and Makefile

After promotion, update:
1. `README.md` — Agents table: add all new agents (v34–v38), bold the new best
2. `Makefile` — Set `AGENT` and `RENDER_AGENT` to the new best agent file

### Step 7: Submit to leaderboard (manual)

```bash
make submit
# Record in SUBMISSIONS.md: agent version, submission ID, score, date
```

## Score Calculation Reference

```
score = (wins + 0.5 × draws) / total_games

# Examples:
# 30W 0D 20L → 30/50 = 60% (PASS)
# 27W 2D 21L → 28/50 = 56% (PASS)
# 25W 0D 25L → 25/50 = 50% (borderline, extend to 100)
# 20W 0D 30L → 20/50 = 40% (FAIL)
```

## If No Candidate Passes

Document all results in experiment records, skip combined agent, revise hypotheses for Round 7. Typical next steps:
- Diagnose what game situations each candidate lost in (render a losing game)
- Consider mechanics that interact differently with production² ROI + no-range-limit
- Identify whether the problem is 2-player or 4-player specific
