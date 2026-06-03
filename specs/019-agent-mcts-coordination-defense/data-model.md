# Data Model: Agent Strategic Improvements

**Feature**: 019-agent-mcts-coordination-defense
**Date**: 2026-06-02

---

## Existing Entities (from agent_v58.py)

- **Planet** (runtime): `(id, owner, x, y, production, ships, radius)` — live observation
- **Fleet** (raw tuple): `(id, player, x, y, angle, source_planet_id, ships)`
- **threat** dict: `{planet_id: incoming_enemy_ships}` — computed each turn from fleet angles

---

## New Entities

### SimPlanet (beam search forward model)
Lightweight planet representation for simulation — no coordinates, no radius:
- `id`: int
- `owner`: int — -1/0/1
- `ships`: float — accumulated during simulation
- `production`: float

### SimFleet (beam search forward model)
In-transit fleet for simulation:
- `owner`: int
- `target_id`: int
- `ships`: int
- `eta`: int — steps until arrival (decremented each sim step)

### SimState
Complete game state for one simulation step:
- `planets`: list[SimPlanet]
- `fleets`: list[SimFleet]

Operations:
- `step()` → advances one turn: grow owned planet ships, decrement ETAs, resolve arrivals
- `score(player)` → float: `sum(p.production for p in planets if p.owner == player) - sum(p.production for p in planets if p.owner == opponent)`

### ActionSet
One candidate action plan for the current turn:
- `dispatches`: list of `(source_planet_id, target_planet_id, ships_to_send)`
- `score`: float — set after simulation
- `label`: str — human-readable label (e.g., "greedy", "swarm_p16", "defend_p8")

### ThreatEntry
Per-planet threat detail (extends the existing `threat` dict):
- `planet_id`: int
- `incoming_ships`: int
- `eta_steps`: int — estimated arrival of enemy fleet
- `can_hold`: bool — `planet.ships + planet.production * eta > incoming_ships`

### TargetCoverage
Tracks in-transit own fleets to prevent redundant dispatches:
- `target_id → ships_in_transit`: dict[int, int] — summed across all in-transit own fleets

---

## Variant Matrix

| Variant file | Base | Coordination | Defense | Beam search |
|---|---|---|---|---|
| `agent_v58.py` | baseline | no | no | no |
| `agent_v59_coord.py` | v58 | yes | no | no |
| `agent_v59_defense.py` | v58 | no | yes | no |
| `agent_v59_beam.py` | v58 | no | no | yes |
| `agent_v59.py` | v58 | yes | yes | yes |
