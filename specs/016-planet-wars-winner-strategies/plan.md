# Implementation Plan: Planet Wars Winner Strategies

**Branch**: `016-planet-wars-winner-strategies` | **Date**: 2026-06-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/016-planet-wars-winner-strategies/spec.md`

## Summary

Implement four heuristic improvements derived from the 2010 Google AI Challenge Planet Wars winner (bocsimacko), evaluate each independently and in combinations, and select the best variant for Kaggle submission. The four techniques are: (A) surplus with in-flight commitment tracking, (B) redistribution (ship consolidation to frontline), (C) spatial penalty scoring, and (D) departure cooldown. Each isolated variant is screened at 50 games; survivors advance to 200-game evaluation; the winner gets 400 games before any submission decision.

## Technical Context

**Language/Version**: Python 3.11 (via uv)

**Primary Dependencies**: `kaggle-environments` ≥ 1.28.0; `eval.py` harness with `--jobs N` parallel workers

**Storage**: Flat agent files at repo root (`agent_vNN.py`); experiment logs in `experiments/`

**Testing**: `uv run python eval.py --agent0 <new> --agent1 agent_v56.py --games N --jobs 8`

**Target Platform**: Kaggle Orbit Wars sandbox (single-file submission, Python 3.x, 1 s/turn)

**Project Type**: Game AI agent (heuristic rule-based, single-file)

**Performance Goals**: Win rate ≥ 55% vs agent_v56 at 95% statistical confidence

**Constraints**: Agent must run in < 1 s/turn; single self-contained `.py` file (Constitution VI Option A); no external deps beyond `math` + `kaggle_environments`

**Scale/Scope**: 9 agent variants total (4 solo + 4 combos + 1 full-combo), ~1,950 evaluation games total

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. RL First | We are improving the heuristic baseline, not bypassing RL. Constitution explicitly permits "heuristic rule-based logic as a baseline or opponent seed." RL path remains open. | ✅ Pass |
| II. Fair Play | All changes are in-bounds game strategy; no engine exploitation | ✅ Pass |
| III. Manual Submissions | Plan specifies no automated submission; any submit is manual after human review | ✅ Pass |
| IV. Documentation | Each variant will have a dated experiment log before eval runs | ✅ Pass |
| V. Local Self-Play | Every variant is eval'd locally vs v56 before any submission | ✅ Pass |
| VI. Package Completeness | All variants are Option A (single self-contained file) | ✅ Pass |
| VII. 95% Confidence Gate | Statistical plan: 50-game screen → 200-game eval → 400-game final. See Statistical Plan below. | ✅ Pass |

## Statistical Plan

Detecting a small improvement requires more games than the baseline 20-game minimum:

| Stage | Games | Purpose | Decision Threshold |
|-------|-------|---------|-------------------|
| **Screen** | 50 | Eliminate clearly harmful variants | Drop if win rate < 45% |
| **Evaluate** | 200 | Rank surviving variants, detect ≥ 8% improvements | Advance if score ≥ 54% (±3.5% CI at 95%) |
| **Final** | 400 | Confirm best variant, detect ≥ 5% improvement | Submit if score ≥ 53% (±2.5% CI at 95%) |

Run evals with `--jobs 8` (parallel) for speed. Use `score` (draws = 0.5) rather than raw win rate for ranking.

## Project Structure

### Documentation (this feature)

```text
specs/016-planet-wars-winner-strategies/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
# Solo experiment variants
agent_v57_surplus.py        # Variant A: in-flight commitment surplus
agent_v57_redistrib.py      # Variant B: redistribution to frontline
agent_v57_spatial.py        # Variant C: spatial penalty scoring
agent_v57_cooldown.py       # Variant D: 1-turn departure cooldown

# Combination variants (to be built after solo screen results)
agent_v57_ab.py             # A + B: surplus + redistribution
agent_v57_ac.py             # A + C: surplus + spatial penalty
agent_v57_bc.py             # B + C: redistribution + spatial penalty
agent_v57_abc.py            # A + B + C: three main improvements
agent_v57_full.py           # A + B + C + D: all four

experiments/
└── 2026-06-01-planet-wars-winner-strategies.md   # Hypothesis + results log
```

**Structure Decision**: Flat agent files at repo root, consistent with all existing agent_vNN.py files. No new directories needed beyond the experiment log.

---

## Phase 0: Research

See [research.md](research.md).

### Key Decisions Resolved

**A. Surplus with in-flight commitment tracking**

The current agent computes `surplus = ships - garrison_floor`. It does not subtract ships already dispatched earlier in the same turn (within the `candidates` loop) or ships dispatched in prior turns that are still in flight. The fix: maintain a `committed` dict per planet that accumulates ships dispatched during the current turn, and subtract it from surplus before each subsequent dispatch decision.

Note: In-flight fleets from previous turns are not directly observable in the game state (we can't enumerate our own in-flight fleets from `obs`). The practical fix is intra-turn commitment tracking — ensuring that if planet X dispatches 50 ships in one action, the next candidate check for planet X sees only `ships - 50 - floor`, not `ships - floor`. This is a meaningful correctness fix even without full multi-turn tracking.

**B. Redistribution (ship consolidation)**

After processing all offensive candidates, any planet with surplus ships and no valid offensive target should consider sending ships to the nearest high-value friendly planet. Value of a friendly planet for redistribution purposes: `production * distance_to_nearest_enemy`. A planet closer to enemies is a higher-priority redistribution target. Redistribution fires only if the source has surplus > `redistribution_threshold` (default: 10 ships) above the garrison floor.

Guard: redistribution MUST NOT fire for a source planet that already dispatched an offensive fleet this turn.

**C. Spatial penalty scoring**

Modify the `_roi` function to subtract a small per-ship penalty proportional to the total enemy ships within a configurable `SPATIAL_RADIUS` (default: 30 units). Formula:

```
adjusted_roi = roi - SPATIAL_PENALTY_WEIGHT * sum(enemy_ships_within_radius)
```

Default `SPATIAL_PENALTY_WEIGHT = 0.01`. This discourages attacking deep into enemy territory when alternative targets exist at the flanks. Candidates with adjusted_roi < 0 are skipped.

**D. Departure cooldown**

Per-planet dict `_last_dispatch` (turn → last departure turn). If `step - _last_dispatch[planet_id] < COOLDOWN_TURNS`, skip that planet for offensive dispatch. Cooldown does NOT apply to comet evacuation or threat-response defense. Test values: 1 turn and 2 turns. Default: 1 turn.

Implementation note: `_last_dispatch` must be a module-level variable initialized once and updated each turn. Kaggle environments call the agent function once per turn.

**E. Evaluation parallelism**

`eval.py` already supports `--jobs N`. Use 8 jobs for all eval runs. Games at 50: ~1-2 min. At 200: ~4-8 min. At 400: ~8-15 min.

---

## Phase 1: Design & Contracts

See [data-model.md](data-model.md).

### Data Model

The agent is a single function — no persistent classes or storage. The "data model" is the per-turn state transformations.

**Committed ships dict** (Variant A):
- Key: planet_id (int)
- Value: ships dispatched this turn (int)
- Lifetime: created fresh each `agent()` call, used within the call

**Last dispatch dict** (Variant D):
- Key: planet_id (int)
- Value: last turn ships were dispatched (int)
- Lifetime: module-level, persists across turns
- Initialization: `{}` at module load time

**Redistribution candidate score** (Variant B):
- For each friendly planet `f`: `score = f.production * (1 / (min_dist_to_enemy + 1))`
- Source eligibility: `surplus > REDISTRIB_THRESHOLD` and no offensive dispatch this turn
- Target: highest-score friendly planet that is not the source

**Spatial radius lookup** (Variant C):
- For each candidate target `t`: sum all enemy planet ships where `dist(enemy, t) < SPATIAL_RADIUS`
- Pre-computed once per turn over all enemy planets

### Agent Context Update

The plan reference in CLAUDE.md is updated below.

### Interface Contracts

No external interface — the agent is a function called by the Kaggle environment. Contract: `agent(obs) -> list[list[int, float, int]]` (list of [planet_id, angle, ships]).

---

## Complexity Tracking

No constitution violations requiring justification. All changes are additive heuristics to an existing single-file agent.

---

## Experiment Schedule

### Solo Variants (run after implementation)

| Variant | Agent File | Eval Command | Screen (50g) | Full (200g) |
|---------|------------|-------------|--------------|-------------|
| A: Surplus | agent_v57_surplus.py | `eval.py --agent0 agent_v57_surplus.py --agent1 agent_v56.py --games 50 --jobs 8` | TBD | TBD |
| B: Redistrib | agent_v57_redistrib.py | (same pattern) | TBD | TBD |
| C: Spatial | agent_v57_spatial.py | (same pattern) | TBD | TBD |
| D: Cooldown-1 | agent_v57_cooldown.py | (same pattern) | TBD | TBD |

### Combination Variants (build after solo screen)

| Variant | Combines | Agent File | Screen (50g) | Full (200g) |
|---------|----------|------------|--------------|-------------|
| A+B | Surplus + Redistrib | agent_v57_ab.py | TBD | TBD |
| A+C | Surplus + Spatial | agent_v57_ac.py | TBD | TBD |
| B+C | Redistrib + Spatial | agent_v57_bc.py | TBD | TBD |
| A+B+C | Three main | agent_v57_abc.py | TBD | TBD |
| A+B+C+D | Full | agent_v57_full.py | TBD | TBD |

### Final Eval

Best-scoring variant from 200-game eval → 400-game confirmation vs v56.

If score ≥ 53% with 95% CI: document experiment, tag as candidate for Kaggle submission.
