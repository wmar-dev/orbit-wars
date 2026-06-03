# Implementation Plan: Early Expansion Experiments from Replay 78539022

**Branch**: `018-replay-neutral-fleet-experiments` | **Date**: 2026-06-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/018-replay-neutral-fleet-experiments/spec.md`

## Summary

Replay 78539022 reveals that agent_v57 dispatched its first fleet 6 steps later than the opponent (step 12 vs step 6) because it selected the highest-ROI neutral planet (Planet 16, 30 ships) but couldn't afford to send it, and — due to a silent skip in the targeting loop — never fell back to the cheaper affordable neutral (Planet 8, 18 ships). This caused a cascade: P1 captured 3 planets by step 20, P0 only 2. The plan implements three experiment variants that fix this root cause and probe related scoring improvements, each benchmarked against agent_v57 over 50 games.

## Technical Context

**Language/Version**: Python 3.x (uv-managed venv)

**Primary Dependencies**: `kaggle-environments` (orbit_wars environment), standard library only in agent files

**Storage**: Experiment records in `experiments/` as `.md`; eval results optionally in `.jsonl`

**Testing**: `uv run python eval.py --agent0 <variant> --agent1 agent_v57.py --games 50 --jobs 4`

**Target Platform**: Kaggle Orbit Wars sandbox (Python, no external deps beyond `kaggle_environments`)

**Project Type**: Game agent / competition entry

**Performance Goals**: Win rate ≥ 5pp above agent_v57 baseline (55%+ in 50-game eval)

**Constraints**: Each agent file must be self-contained (Python stdlib + `kaggle_environments` only); `actTimeout` = 1 second/turn

**Scale/Scope**: 3 experiment variants, 50–100 games per variant, 1 submission candidate

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. RL First | ✅ Pass | Heuristic agents are explicitly permitted as baselines; no RL infra changes |
| II. Fair Play | ✅ Pass | No rule exploits; all changes operate within observation/action API |
| III. Manual Submissions | ✅ Pass | Experiments are local only; submission is manual after evaluation |
| IV. Experiment Documentation | ✅ Pass | All variants will have experiment `.md` files in `experiments/` before eval |
| V. Local Self-Play ≥20 games | ✅ Pass | 50 games per variant exceeds the 20-game minimum |
| VI. Submission Package | ✅ Pass | Agent files use stdlib + `kaggle_environments` only; no local imports |
| VII. 95% Confidence Gate | ✅ Pass | 50-game eval for initial screening; 100-game eval before any submission candidate |

## Project Structure

### Documentation (this feature)

```text
specs/018-replay-neutral-fleet-experiments/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: root cause analysis and experiment decisions
├── data-model.md        # Phase 1: entity definitions and variant matrix
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
agent_v57.py             # Baseline (unchanged)
agent_v58_fallback.py    # Experiment A: affordability fallback in targeting loop
agent_v58_efficiency.py  # Experiment B: growth-efficiency scoring + fallback
agent_v58.py             # Experiment C: best variant promoted to main agent

experiments/
└── 2026-06-02-replay-78539022-early-expansion.md   # Experiment doc (all variants)
```

**Structure Decision**: Single-project layout. Each variant is a standalone `.py` file at repo root matching existing conventions (agent_vNN.py). No new directories needed.

## Implementation Detail

### Experiment A — Affordability Fallback

**Location**: [agent_v57.py:380-413](../../agent_v57.py#L380)

**Change**: After computing `roi_scores`, sort descending by blended key, then iterate through candidates until finding one where `mine.ships >= ships_needed`. Dispatch to that candidate and break, rather than picking unconditionally and then skipping on unaffordability.

```python
# BEFORE (picks best ROI target unconditionally):
best_roi, best_target, bx, by = max(roi_scores, key=blended_key)
if best_target.owner == -1:
    ships_needed = best_target.ships + 1
if mine.ships < ships_needed:
    continue  # skips entire mine

# AFTER (falls back through sorted candidates until affordable):
sorted_candidates = sorted(roi_scores, key=blended_key, reverse=True)
dispatched = False
for roi, t, bx, by in sorted_candidates:
    if t.owner == -1:
        ships_needed = t.ships + 1
    else:
        ships_needed, bx, by = _enemy_fleet_size(...)
        # re-validate path safety for enemy targets
    if mine.ships >= ships_needed:
        # dispatch
        dispatched = True
        break
```

This is a surgical change (~15 lines). All other logic (path safety, orbit lead, comet handling) is preserved.

### Experiment B — Growth-Efficiency Scoring

**Location**: Same block, replaces `blended_key` comparator for neutral targets.

**Change**: For neutral planet candidates, replace ROI with `growth_efficiency = t.production / t.ships`. For enemy targets, keep existing ROI. The rationale: ROI formula's `t.production * travel` term in the denominator overstates neutral difficulty since neutrals appear to be static garrisons (not growing while neutral).

```python
def _growth_efficiency(t):
    if t.owner == -1:
        return t.production / max(t.ships, 1)
    return 0.0  # enemy planets use existing ROI

# Use growth_efficiency as primary key, ROI as secondary for same-tier planets
```

Experiment B includes the Experiment A fallback as well (both changes active).

### Experiment C — Combined (Best Candidate)

Whichever single variant (A or B) shows better 50-game win rate against agent_v57 becomes `agent_v58.py`. If A and B are statistically tied (within 3pp), run a 100-game A-vs-B evaluation to break the tie. Document the outcome in the experiment log.

### Evaluation Protocol

```bash
# Experiment A
uv run python eval.py --agent0 agent_v58_fallback.py --agent1 agent_v57.py --games 50 --jobs 4

# Experiment B
uv run python eval.py --agent0 agent_v58_efficiency.py --agent1 agent_v57.py --games 50 --jobs 4

# If both pass (+3pp), head-to-head
uv run python eval.py --agent0 agent_v58_fallback.py --agent1 agent_v58_efficiency.py --games 100 --jobs 4
```

Record results in `experiments/2026-06-02-replay-78539022-early-expansion.md`.

## Phase 0 Research: Complete

See [research.md](research.md).

Key findings:
1. Root cause is a dispatch skip bug (no fallback when best target unaffordable), not a scoring formula problem
2. Neutral planets appear to be static garrisons (don't grow while neutral) — fleet sizing `ships + 1` is correct
3. ROI formula's denominator overcounts neutral difficulty, creating mild bias toward expensive high-growth planets
4. Parallel expansion should emerge naturally from the fallback fix without explicit multi-target logic

## Phase 1 Design: Complete

See [data-model.md](data-model.md).

Key decisions:
- `AffordableCandidate` pattern: filter targets to `mine.ships >= ships_needed` before final selection
- `GrowthEfficiencyScore`: `production / ships` as simpler neutral scoring alternative
- 3 variants: fallback-only, efficiency+fallback, combined winner
- No new infrastructure needed; all experiments use existing `eval.py` harness

## Complexity Tracking

No constitution violations.
