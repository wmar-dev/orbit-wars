# Research: Beat the Getting Started Agent

**Date**: 2026-05-29
**Feature**: Production-weighted targeting agent

## Decision 1: Target Scoring Function

**Decision**: Score each non-owned target planet as `production / distance`, where distance
is the Euclidean distance from the launching planet to the target's current position. Select
the highest-scoring target per owned planet each turn.

**Rationale**: Production/distance is the canonical "value per travel cost" heuristic for
resource-accumulation strategy games. It favors nearby high-production planets over distant
low-production ones — exactly the failure mode of nearest-sniper (which ignores production
entirely). The formula is O(1) per planet pair, adds no latency overhead, and the intent
is immediately readable from the code.

**Alternatives considered**:
- `production² / distance` — overweights production, sometimes ignores closer planets that
  are nearly as good; less intuitive
- `(production - ships_needed) / distance` — accounts for capture cost but introduces
  negative scores for heavily garrisoned planets, requiring filtering logic
- Purely highest-production (ignore distance) — degenerates to always attacking the
  farthest high-value planet, wasting fleet travel time early game

---

## Decision 2: Ships to Send Per Attack

**Decision**: Send exactly `target.ships + 1` ships — the minimum needed for guaranteed
capture. Same as the getting-started agent.

**Rationale**: Keeps the diff small and focused on the targeting improvement. Sending
minimum ships preserves garrison for defense and future launches. More sophisticated
allocation (e.g., partial fleets, reserves) is a separate optimization deferred to later
experiments per the constitution's RL-first principle.

**Alternatives considered**:
- Send 50% of garrison — simpler but can fail to capture heavily defended planets
- Send all ships — aggressive but leaves owned planets undefended

---

## Decision 3: Orbiting Planet Position Prediction

**Decision**: Use current observed position (`planet.x`, `planet.y`) for angle calculation,
not a predicted future position.

**Rationale**: For the first experiment, position prediction adds significant complexity
(requires integrating `angular_velocity` over estimated travel time). The getting-started
agent also uses current position, so this is not a regression. Prediction is a meaningful
improvement to explore in a future experiment.

**Alternatives considered**:
- Predict position N turns ahead using `angular_velocity` — more accurate targeting but
  requires estimating fleet travel time, which depends on fleet size (non-trivial formula)

---

## Decision 4: Evaluation Harness Design

**Decision**: Standalone `eval.py` script that runs N games between two agent files loaded
via `importlib`, prints per-game results and final win rate to stdout.

**Rationale**: `importlib` allows swapping agent files by path argument without modifying
code. Stdout-only output keeps the harness simple (per clarification Q2). The script extends
the existing `kaggle_environments` workflow already established in the Makefile.

**Alternatives considered**:
- Extend `Makefile` test target directly — less flexible for comparing arbitrary agent pairs
- pytest fixture — over-engineered for a script-based experiment workflow

---

## Decision 5: Speed Optimizations

**Decision**: Apply these micro-optimizations while preserving readability:
1. Pre-filter owned and target planets once per turn (not per planet)
2. Use `math.hypot` instead of manual sqrt for distance (faster in CPython)
3. Avoid list comprehensions inside inner loops; use direct iteration
4. Skip turns with no valid targets immediately (early return)

**Rationale**: The turn budget is 1 second for a game with up to ~40 planets and ~N fleets.
Pure Python is fast enough at this scale without vectorization. These micro-opts cut constant
overhead without obscuring the algorithm. NumPy or similar is explicitly out of scope
(no pre-computed tables, per spec Assumptions).

**Alternatives considered**:
- NumPy vectorized scoring — faster but violates readability goal and adds a dependency
- Caching distance calculations — premature; planet positions change each turn for orbiting planets
