# Quickstart: Experiments Round 6

## Phase A — Resolve the baseline (run all 3, can parallelize)

```bash
uv run python eval.py h2h --agent0 agent_v58.py --agent1 agent_v60.py --games 50 --jobs 4 --swap
uv run python eval.py h2h --agent0 agent_v58.py --agent1 agent_v64.py --games 50 --jobs 4 --swap
uv run python eval.py h2h --agent0 agent_v60.py --agent1 agent_v64.py --games 50 --jobs 4 --swap
```

Record the three win rates in `experiments/2026-06-13-round6-baseline-matrix.md`. Pick the agent with the best aggregate record as `<BASELINE>`. If non-transitive, use the highest `SUBMISSIONS.md` Kaggle score as the tiebreaker.

## Phase B — Fresh replay analysis vs slawekbiel_agent

```bash
# Generate >=5 local games of <BASELINE> vs slawekbiel_agent, saving full step history.
# (Inline script — adapt agent path to <BASELINE>; mirrors how replays/<episode_id>.json are shaped.)
uv run python -c "
from kaggle_environments import make
import json
for i in range(5):
    env = make('orbit_wars', configuration={'seed': i})
    env.run(['<BASELINE>.py', 'opponent_agents/slawekbiel_agent.py'])
    with open(f'replays/replay_round6_{i}.json', 'w') as f:
        json.dump(env.toJSON(), f)
"
```

Then run the analysis skill:

```text
/analyze-replay replays/replay_round6_*.json
```

This writes `experiments/YYYY-MM-DD-replay-analysis.md` with ≥3 behavioral differences and exactly 2 candidate directions (per FR-003/FR-004). Confirm both candidates are distinct from mechanics already in `agent_v57`–`agent_v66`.

## Phase C — Implement, evaluate, combine

```bash
cp <BASELINE>.py agent_v67.py
# Add CANDIDATE_1_ENABLED / CANDIDATE_2_ENABLED toggles + gated logic per the Phase B findings.

# Candidate 1 alone:
uv run python eval.py h2h --agent0 agent_v67.py --agent1 <BASELINE>.py --games 50 --jobs 4 --swap

# Candidate 2 alone:
uv run python eval.py h2h --agent0 agent_v67.py --agent1 <BASELINE>.py --games 50 --jobs 4 --swap

# If either >= 52%, enable all passing candidates together and re-run:
uv run python eval.py h2h --agent0 agent_v67.py --agent1 <BASELINE>.py --games 50 --jobs 4 --swap --timing
```

Record all results in `experiments/2026-06-1X-experiments-round6.md`. If the combined (or single best) agent passes at ≥52% with p99 < 100ms and zero sun/OOB losses, update README's Agents table (bold the new best) and Makefile `AGENT`/`RENDER_AGENT` per `CLAUDE.md`. Otherwise, document the all-discarded result and confirm `<BASELINE>` is correctly reflected as current best.
