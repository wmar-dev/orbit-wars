# Research: Experiments Round 4

**Date**: 2026-06-06 | **Plan**: [plan.md](plan.md)

## Technical Decisions

### Agent Platform Approach

- **Decision**: Create `agent_v64.py` as copy of `agent_v63.py`, add new experiment toggles
- **Rationale**: Consistent with all prior round conventions. v63 remains frozen baseline. v64 serves as experimental platform with independent toggles.
- **Alternatives considered**: Modify v63 in-place (rejected — breaks baseline reproducibility), merge toggles into v62 (rejected — too many experiments, codebase drift)

### Opponent Model v3 Design

- **Decision**: `_sim_opponent_step_v3` will use `_greedy_moves`-style behavior on behalf of each opponent planet: ROI-based target selection with garrison floor checks, fleet speed scaling, and path safety filtering. Matches v62-level behavioral realism. Not a full beam search (too expensive).
- **Rationale**: The current v2 model (nearest-target, surplus-only) is unrealistically weak. Using a dispatch heuristic similar to our own greedy logic will produce more realistic opponent play in simulation, making beam search evaluations more accurate.
- **Alternatives considered**: Nearest-target with production-weighted target selection (simpler but still unrealistic), full beam search opponent (too expensive for N opponents × depth), opponent clone of our own agent (overfit — real opponents play differently)

### Multi-Turn Plan Generation Approach

- **Decision**: Add "zero-dispatch" candidates to `_gen_beam_candidates` — for each mine, generate an alternative where that mine sends 0 ships this turn. The beam search evaluates this against the normal dispatch. If waiting is better (ships accumulate for a bigger future send), the score will reflect that.
- **Rationale**: Minimal code change. Reuses existing beam search infrastructure. The skip candidate naturally competes with dispatch candidates — the search picks whichever scores higher.
- **Alternatives considered**: Full multi-turn tree search (too expensive, would require generating candidates at each simulated step), N-ply search with waiting moves (already have N-ply, making it aware of waiting is more complex)

### Phase Detection Approach

- **Decision**: Detect three phases based on owned-planet ratio (% of non-neutral planets owned).
  - **Expansion** (<40% owned): Normal behavior, GARRISON_FLOOR_FACTOR at 1.5× ramp to 400
  - **Mid-game** (40-80% owned): Reduce garrison floor factor ramp to free ships
  - **Elimination** (>80% owned): Further reduce garrison floor, disable splinter dispatch (send all surplus to opponent planets), prioritize attacks on remaining opponent(s)
- **Rationale**: Simple, low-risk scalar changes. Phase detection only adjusts existing constants — no new logic paths that could introduce bugs.
- **Alternatives considered**: Turn-based phases (too rigid — game pace varies), opponent-count-based phases (complements planet-ratio approach for elimination detection)

### Eval Methodology

- **Decision**: 50-game evals with `--swap` (25 per side) vs v63 baseline. ≥52% = KEEP, <50% = DISCARD. --timing flag for per-turn instrumentation. Opponent sweep (20 games each) for passing experiments.
- **Rationale**: Same methodology as round 3. 50 games provides reasonable statistical power. --swap cancels any first-player advantage. --timing ensures 800ms budget compliance.
- **Alternatives considered**: 100 games (more power but 2× time), 20 games (faster but less reliable — round 3 found 40-48% DISCARD results that were clear even at 50)
