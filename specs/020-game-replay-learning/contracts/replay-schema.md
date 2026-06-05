# Contract: Replay JSON Schema

**Version**: 1.0  
**Consumer**: `analyze_replays.py`, `/analyze-replay` skill  
**Producer**: `record_replays.py`

## File Location

```
replays/replay_{opponent}_{YYYYMMDD_HHMMSS}_{NNN:03d}.json
```

Example: `replays/replay_slawekbiel_20260604_221500_001.json`

## Top-Level Structure

```json
{
  "version": "1.0",
  "recorded_at": "2026-06-04T22:15:00",
  "agents": ["agent_v56", "slawekbiel"],
  "opponent_file": "opponent_agents/slawekbiel_agent.py",
  "outcome": { ... },
  "turns": [ ... ]
}
```

## Outcome Object

```json
{
  "winner": 1,
  "end_turn": 312,
  "final_planets": [2, 8],
  "final_ships": [45, 380],
  "divergence_turn": 87,
  "total_dispatches": [54, 112]
}
```

- `winner`: `0`, `1`, or `null` (draw)
- `divergence_turn`: first turn where either `planets[i] / planets[j] >= 2.0` or `ships[i] / ships[j] >= 2.0`

## Turn Record

```json
{
  "turn": 42,
  "planets": [
    {"id": 0, "x": 23.1, "y": 67.4, "radius": 4.0, "owner": 0, "ships": 12.0, "production": 2.0},
    {"id": 1, "x": 71.2, "y": 34.8, "radius": 3.5, "owner": 1, "ships": 8.5, "production": 1.5},
    {"id": 2, "x": 50.0, "y": 50.0, "radius": 5.0, "owner": null, "ships": 0.0, "production": 3.0}
  ],
  "fleets": [
    {"id": 0, "owner": 0, "ships": 10.0, "source": 0, "destination": 2, "eta": 3}
  ],
  "moves": [
    {"player": 0, "dispatches": [{"source_planet_id": 0, "angle": 1.047, "ships": 10.0}]},
    {"player": 1, "dispatches": []}
  ],
  "planet_counts": [3, 5],
  "ship_totals": [87, 203]
}
```

## Constraints

- `version` must be `"1.0"` for this schema
- `turns` is ordered by `turn` ascending, no gaps
- `owner` is `null` for neutral planets (not `"neutral"` or `-1`)
- `moves[i].player` must equal `i`
- All numeric fields are JSON numbers (float or int); never strings
- Missing optional fields (`destination` on fleets) may be `null`, never omitted

## CLI Contract: `record_replays.py`

```
python record_replays.py --opponent <path> [--games N] [--out-dir replays/] [--our-agent <path>]
```

| Argument | Default | Description |
| --- | --- | --- |
| `--opponent` | required | Path to opponent agent `.py` file |
| `--games` | `20` | Number of games to run |
| `--out-dir` | `replays/` | Directory to write replay JSON files |
| `--our-agent` | `agent_v56.py` | Path to our agent file |

Exit code 0 on success; non-zero if any game fails to record.

## CLI Contract: `analyze_replays.py`

```
python analyze_replays.py [--dir replays/] [--opponent <slug>] [--buckets 50,100,200]
```

Prints a summary table to stdout. No side effects.

| Argument | Default | Description |
| --- | --- | --- |
| `--dir` | `replays/` | Directory of replay JSON files to analyze |
| `--opponent` | all | Filter by opponent name slug |
| `--buckets` | `50,100,200,500` | Turn bucket boundaries for statistics |
