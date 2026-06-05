# Quickstart: Game Replay Learning

## Record games against slawekbiel

```bash
# Record 20 games (default) — saves to replays/
python record_replays.py --opponent opponent_agents/slawekbiel_agent.py

# Record more games with explicit count
python record_replays.py --opponent opponent_agents/slawekbiel_agent.py --games 50

# Use a different agent as "ours"
python record_replays.py --opponent opponent_agents/slawekbiel_agent.py --our-agent agent_v56.py
```

## Print a statistics summary

```bash
# All replays
python analyze_replays.py

# Filter to slawekbiel replays only
python analyze_replays.py --opponent slawekbiel
```

## Analyze replays and get improvement suggestions (Claude skill)

Inside a Claude Code session:

```
/analyze-replay replays/replay_slawekbiel_*.json
```

Or just:

```
/analyze-replay
```
(analyzes all `replays/*.json` files)

The skill will:
1. Print per-turn-bucket statistics for both agents
2. Identify behavioral differences
3. Propose 1–3 candidate improvements
4. Write findings to `experiments/YYYY-MM-DD-replay-analysis.md`

## Replay file location

```
replays/
├── replay_slawekbiel_20260604_221500_001.json
├── replay_slawekbiel_20260604_221500_002.json
└── ...
```

Files are gitignored (can be large). Re-record anytime with `record_replays.py`.

## Iteration loop

```
record_replays.py → /analyze-replay → read experiment entry →
/speckit-specify <candidate hypothesis> → implement → eval → repeat
```
