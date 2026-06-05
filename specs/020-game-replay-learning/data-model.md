# Data Model: Game Replay Learning

## Entities

### Replay (root object, one file per game)

Stored as a single JSON object.

| Field | Type | Description |
| --- | --- | --- |
| `version` | `string` | Schema version, e.g. `"1.0"` |
| `recorded_at` | `string` | ISO 8601 timestamp of recording |
| `agents` | `[string, string]` | Agent names/labels, index = player index |
| `opponent_file` | `string` | Path to opponent agent file |
| `outcome` | `Outcome` | Winner, end turn, final state summary |
| `turns` | `TurnRecord[]` | Ordered list, one entry per game turn |

---

### Outcome

| Field | Type | Description |
| --- | --- | --- |
| `winner` | `int \| null` | Player index of winner, or `null` for draw |
| `end_turn` | `int` | Turn number at game end (≤ 500) |
| `final_planets` | `[int, int]` | Planet count per player at end turn |
| `final_ships` | `[int, int]` | Total ship count per player at end turn |
| `divergence_turn` | `int \| null` | First turn with 2× advantage; `null` if never reached |
| `total_dispatches` | `[int, int]` | Total fleet dispatches per player across entire game |

---

### TurnRecord

One entry per turn, per game.

| Field | Type | Description |
| --- | --- | --- |
| `turn` | `int` | Turn number (0-indexed) |
| `planets` | `PlanetSnapshot[]` | State of all planets at start of this turn |
| `fleets` | `FleetSnapshot[]` | All in-flight fleets visible this turn |
| `moves` | `[MoveRecord, MoveRecord]` | Actions taken by each player this turn (index = player index) |
| `planet_counts` | `[int, int]` | Planets owned per player at this turn |
| `ship_totals` | `[int, int]` | Total ships (planets + in-flight) per player at this turn |

---

### PlanetSnapshot

| Field | Type | Description |
| --- | --- | --- |
| `id` | `int` | Planet ID |
| `x` | `float` | X position |
| `y` | `float` | Y position |
| `radius` | `float` | Planet radius |
| `owner` | `int \| null` | Player index, or `null` for neutral |
| `ships` | `float` | Ship count on planet |
| `production` | `float` | Production rate |

---

### FleetSnapshot

| Field | Type | Description |
| --- | --- | --- |
| `id` | `int` | Fleet ID |
| `owner` | `int` | Player index |
| `ships` | `float` | Ship count in fleet |
| `source` | `int` | Source planet ID |
| `destination` | `int \| null` | Destination planet ID (if determinable) |
| `eta` | `int` | Turns until arrival |

---

### MoveRecord

| Field | Type | Description |
| --- | --- | --- |
| `player` | `int` | Player index |
| `dispatches` | `Dispatch[]` | List of fleet sends this turn (may be empty) |

---

### Dispatch

| Field | Type | Description |
| --- | --- | --- |
| `source_planet_id` | `int` | Planet ships launched from |
| `angle` | `float` | Launch angle in radians |
| `ships` | `float` | Ships sent |

---

## State Transitions

```
game starts
  → TurnRecord recorded (turn 0)
  → agent shims called → MoveRecord captured
  → env advances state
  → TurnRecord recorded (turn 1)
  → ... repeat until game ends ...
game ends
  → Outcome computed from final TurnRecord
  → Replay written to disk as JSON
```

## Validation Rules

- `turns` length must equal `outcome.end_turn + 1`
- `moves` always has exactly 2 entries (one per player)
- `planet_counts[i] + ship_totals[i]` relationships are informational; the raw per-turn planet/ship snapshots are authoritative
- `divergence_turn` must be ≤ `outcome.end_turn` if not null
