# Data Model: Agent Lookahead Decision Search

**Date**: 2026-06-05 | **Branch**: `021-lookahead-search`

## Entities

### _SimPlanet

Represents the state of a planet within the forward simulator. Stripped-down version of the game's `Planet` namedtuple — only fields needed for simulation.

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Planet identifier (matches game observation) |
| `owner` | int | Owner player index; -1 = neutral |
| `ships` | float | Current ship count (float for production accumulation) |
| `production` | float | Ships produced per turn |

**Constraints**:
- `production >= 0` (neutral planets have production=0 per spec 018)
- `ships >= 0` always; arrival resolution may set to near-zero before clamping
- `owner` is -1, 0, or 1 (2-player game)

**State transitions**:
- Each sim step: if `owner >= 0`, `ships += production`
- On fleet arrival: see `_SimFleet` resolution rules

---

### _SimFleet

Represents an in-transit fleet within the forward simulator.

| Field | Type | Description |
|-------|------|-------------|
| `owner` | int | Fleet owner player index |
| `target_id` | int | Planet ID the fleet is heading toward |
| `ships` | int | Ship count carried by the fleet |
| `eta` | int | Steps remaining until arrival (≥1 at creation) |

**Constraints**:
- `ships >= 1`
- `eta >= 0`; fleets with `eta == 0` are resolved at step start before production

**State transitions**:
- Each sim step: `eta -= 1`
- If `eta <= 0` after decrement: resolve arrival against target planet

**Arrival resolution**:
- Friendly (`fleet.owner == planet.owner`): `planet.ships += fleet.ships`
- Hostile, fleet wins (`fleet.ships > planet.ships`): `planet.owner = fleet.owner; planet.ships = fleet.ships - planet.ships`
- Hostile, fleet loses or ties: `planet.ships -= fleet.ships` (planet keeps owner)

---

### _SimState

Container for a complete forward-simulation snapshot. Mutable during `step()` calls; cloned via `copy()` before simulating a candidate.

| Field | Type | Description |
|-------|------|-------------|
| `planets` | list[_SimPlanet] | All planets in the game |
| `fleets` | list[_SimFleet] | All in-transit fleets |
| `_idx` | dict[int, int] | Planet ID → index in `planets` list (cache for O(1) lookup) |

**Key operations**:

- `step()` — advance one turn: apply production, decrement ETAs, resolve arrivals
- `score(player, transit_weight)` — evaluate state for `player` (production advantage + weighted in-transit ships)
- `copy()` — deep copy for branch simulation (O(planets + fleets))

**Score formula**:
```
score = (sum(p.production for p in planets if p.owner == player)
       - sum(p.production for p in planets if 0 <= p.owner != player))
      + transit_weight × (sum(f.ships for f in fleets if f.owner == player)
                        - sum(f.ships for f in fleets if 0 <= f.owner != player))
```

---

### ActionSet

One candidate fleet-dispatch decision for a single turn. Not a class — represented as a list of tuples.

| Element | Type | Description |
|---------|------|-------------|
| `src_id` | int | Source planet ID |
| `target_id` | int | Target planet ID |
| `ships` | int | Number of ships dispatched |
| `eta` | int | Steps until arrival (computed from distance / fleet_speed) |

Stored as `list[tuple[int, int, int, int]]`. Empty list = hold-all (no dispatches this turn).

---

### _MCTSNode (internal, dict-based)

Used only when `SEARCH_STRATEGY == "mcts"`. The MCTS tree is a `dict[node_id, dict]` rather than a class, to avoid object allocation overhead.

| Key | Type | Description |
|-----|------|-------------|
| `score_sum` | float | Accumulated score from all rollouts through this node |
| `visits` | int | Number of times this node has been visited |
| `children` | list[int] | Node IDs of child nodes |
| `action` | ActionSet | The action set that led to this node from its parent |
| `state` | _SimState | Game state at this node |

**UCB1 formula**:
```
ucb1 = (score_sum / visits) + MCTS_C × sqrt(ln(parent_visits) / visits)
```
Unvisited children have infinite UCB1 (always expanded first).

---

### SearchResult

Return type of all three search strategies. Represented as a plain `list[list]` (same format as game `moves`).

Each element: `[planet_id, angle, ship_count]` — the standard game move format.

---

## Constants and Tunable Parameters

All tunable parameters are defined at the top of `agent_v60.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `SEARCH_STRATEGY` | `"beam"` | Algorithm selector: `"beam"` \| `"mcts"` \| `"nply"` |
| `SEARCH_DEPTH` | `10` | Turns to simulate forward |
| `TRANSIT_WEIGHT` | `0.1` | In-transit ships weighting in score function |
| `SEARCH_TIMEOUT_MS` | `800` | Hard wall-clock cutoff per turn (milliseconds) |
| `BEAM_K` | `3` | Top-K target candidates per mine for beam search |
| `MCTS_C` | `1.41` | UCB1 exploration constant (≈√2) |
| `NPLY_BEAM_WIDTH` | `8` | Max branches kept at each N-ply level |

---

## Initialization Flow

```
live observation
    │
    ▼
_build_sim_state()       ← converts raw obs into _SimState
    │
    ▼
_greedy_moves()          ← computes v58-style greedy decisions (baseline + fallback)
    │
    ▼
_lookahead_search()      ← dispatches to beam / mcts / nply based on SEARCH_STRATEGY
    │                       returns best ActionSet as game moves list
    ▼
agent() returns moves    ← if timeout at any point → returns greedy_moves
```
