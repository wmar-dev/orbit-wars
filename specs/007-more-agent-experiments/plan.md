# Implementation Plan: Agent Improvement Experiments — Round 3

**Branch**: `007-more-agent-experiments` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-more-agent-experiments/spec.md`

## Summary

Run four isolated mechanic experiments (agent_v21–v24) against agent_v20 as the 2-player baseline (75% vs agent_v15), then stack all passing mechanics (≥ 55%) into agent_v25. In parallel, introduce 4-player-specific mechanics to address the likely cause of the leaderboard regression from v8 → v15 (all prior agents were optimized purely for 2-player self-play). A new `eval4.py` harness enables systematic 4-player win/rank measurement so future submissions are validated under leaderboard-realistic conditions.

Round 3 candidate mechanics:
- **Candidate I (v21)**: Reactive defense — dispatch targeted reinforcements to owned planets under imminent attack
- **Candidate J (v22)**: Smooth adaptive range — power-law range expansion/contraction based on ship ratio
- **Candidate K (v23)**: Enemy-territory priority — bias ROI score toward enemy-owned planets when winning
- **Candidate L (v24)**: Two-source coordinated attack — allow 2 planets to gang-up on unaffordable high-value targets

4-player-specific additions for the combined agent:
- **Candidate M**: Neutral-first expansion when behind (4P)
- **Candidate N**: Weakest-opponent targeting / focus-fire elimination (4P)

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: kaggle_environments (orbit_wars engine), eval.py (2-player harness — not modified), diagnose_v9.py (safety audit — not modified), new eval4.py (4-player harness)

**Storage**: N/A — agent files at repo root, experiment records in `experiments/`

**Testing**:
- 2-player: `eval.py --agent0 agent_vN.py --agent1 agent_v20.py --games 20 --seed 0`
- 4-player (visual): `make render4 RENDER_AGENT=agent_vN.py`
- 4-player (quantitative): `python eval4.py --agent agent_vN.py --opponent random --games 20` (new harness, see Phase 1)
- Safety: `diagnose_v9.py --agent agent_vN.py --games 20` on combined agent only

**Target Platform**: Local Python execution (Kaggle submission manual)

**Project Type**: Game AI agent scripts

**Performance Goals**:
- 2-player: each candidate ≥ 55% vs agent_v20; combined ≥ 65% vs agent_v20
- 4-player: combined agent achieves average rank ≤ 2.0 vs 3× random over 20 games (baseline established first)

**Constraints**: actTimeout 1 s/turn; eval.py and diagnose_v9.py unchanged; no safety guard removal; agent file must be self-contained Python (Kaggle submission format)

**Scale/Scope**: 5–10 agent files + eval4.py + 5–10 experiment records per round; 6+ eval runs × 20 games

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Reinforcement Learning First** | WAIVED (justified) | Heuristic iteration is the approved short-term method per prior rounds 001–006 precedent. RL remains the long-term path. |
| **II. Fair Play & Rules Compliance** | PASS | No engine bug exploitation; actTimeout respected; all agents build on the compliant agent_v20 base. |
| **III. Manual Submissions Only** | PASS | No automated submission. eval4.py is evaluation-only. |
| **IV. Experiment & Documentation Discipline** | PASS | FR-001 mandates experiment records before agent files. 4-player candidates (M, N) also require records. |
| **V. Local Self-Play as Primary Evaluation Loop** | PASS | 2-player self-play remains primary gate (20 games vs agent_v20). 4-player eval is supplementary diagnostic. |

**Complexity Tracking**: No violations. Principle I waived by pre-existing project precedent.

**Post-design re-check**: No new violations. Agent_v20 safety guards are inherited unchanged in all candidates (FR-007).

## Project Structure

### Documentation (this feature)

```text
specs/007-more-agent-experiments/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
agent_v20.py             # Immutable baseline — never modified
agent_v21.py             # Candidate I: reactive defense dispatch
agent_v22.py             # Candidate J: smooth adaptive range
agent_v23.py             # Candidate K: enemy-territory priority when winning
agent_v24.py             # Candidate L: two-source coordinated attack
agent_v25.py             # Combined agent (all ≥55% 2-player mechanics)

eval4.py                 # New: 4-player evaluation harness

experiments/
├── 2026-05-30-candidate-i-reactive-defense.md
├── 2026-05-30-candidate-j-smooth-adaptive-range.md
├── 2026-05-30-candidate-k-enemy-priority.md
├── 2026-05-30-candidate-l-two-source-attack.md
├── 2026-05-30-candidate-m-4p-neutral-expansion.md
├── 2026-05-30-candidate-n-4p-focus-fire.md
└── 2026-05-30-combined-agent-v25.md

eval.py                  # Unchanged — 2-player harness
diagnose_v9.py           # Unchanged — safety diagnostic
```

**Structure Decision**: Flat repo root for agent scripts (matches all prior agents v2–v20). New eval4.py at repo root alongside eval.py.

---

## Phase 0: Research

> Output: `specs/007-more-agent-experiments/research.md`

All design decisions are documented in [research.md](research.md). Key decisions summarized:

### D-001: Reactive Defense Dispatch (Candidate I)

Each turn, before computing offensive moves, scan all incoming enemy fleets from `obs.fleets` (or equivalent). For each owned planet P:
- Compute `projected_garrison = P.ships + P.production * arrival_turns` where `arrival_turns = fleet.distance_remaining / fleet_speed(fleet.ships)`.
- If `projected_garrison < incoming_fleet.ships`, dispatch reinforcement from the nearest owned planet Q with `surplus = Q.ships - garrison_floor(Q) > 0` and `surplus + projected_garrison ≥ incoming_fleet.ships`.
- The source Q is excluded from offensive dispatch this turn.
- Differs from failed Candidate C (10% vs v10): Candidate C defended broadly (any threat); this only fires on planets that will *certainly be lost* without intervention, and only if reinforcement is actually sufficient.

**Risk**: obs structure may not expose fleets directly; fallback is reading `obs.get("fleets", [])` and handling missing key gracefully (no-op if key absent).

### D-002: Smooth Adaptive Range (Candidate J)

```python
own_total = sum(p.ships for p in my_planets)
enemy_total = sum(p.ships for p in planets if p.owner not in (-1, player))
ratio = own_total / max(1, enemy_total)
range_factor = max(1.5, min(3.5, 2.0 * ratio ** 0.25))
```

Applied per source planet (replaces fixed `RANGE_FACTOR = 2.0`). In 4-player: `enemy_total` sums all opponent-owned planets (not neutral). The `** 0.25` exponent gives gentler response than Candidate G's hard step-function (which scored 0% vs v15).

### D-003: Enemy-Territory Priority (Candidate K)

```python
def _roi_k(t, bx, by, mine, player):
    base = _roi(t, bx, by, mine)
    if t.owner != -1 and t.owner != player:  # enemy-owned
        return base * 1.5
    return base
```

Multiplier applies only when `own_total / enemy_total ≥ 1.5`. In 4-player: enemy-owned includes any of the other 3 players' planets, not just the closest opponent.

### D-004: Two-Source Coordinated Attack (Candidate L)

Single-sender coordination (Candidate D) assigns exactly one source per target and skips targets no source can afford. Two-source coordination allows:
1. Find the target with the highest ROI that no single source can send to (after garrison floor).
2. If the top-2 sources by surplus can together cover `target.ships + 1`, dispatch both simultaneously: each sends `ceil((target.ships + 1) / 2)` ships, both aimed at the predicted position.
3. Only apply when both sources are within `range_factor * nearest_dist`.
4. Does not conflict with single-sender for targets a single source can afford — single-sender takes precedence.

**Risk**: Two fleets arriving simultaneously may over-commit. Cap the joint send at `target.ships + 1` total; each source sends its proportional share.

### D-005: 4-Player Mechanics

**Candidate M — Neutral-first when losing (4P)**:
In 4-player, when the agent is the trailing player (`own_total < min(other_player_totals)`), add a 2× ROI multiplier for neutral planets (owner == -1). Rationale: Cheap neutral captures build production without triggering multi-opponent retaliation. Losing badly against multiple opponents means attacking anyone invites a second attacker.

**Candidate N — Focus-fire on leading opponent (4P)**:
In 4-player, identify the leading opponent: `max(other players by total ship count)`. Add a 1.3× ROI multiplier for planets owned by the leading opponent. Rationale: Eliminating the strongest opponent shifts the power balance; ignoring them lets them snowball. In 2-player this degenerates to Candidate K (1 opponent = always the "leader").

**Integration order in combined agent (agent_v25)**:
1. Identify player count: `n_players = len(set(p.owner for p in planets if p.owner >= 0))`
2. Compute ship ratio for range adjustment (J)
3. If 4-player: compute opponent rankings for M and N multipliers
4. Per-source: reactive defense check (I) → skip offensive if reinforcing
5. Compute ROI with enemy-priority bias (K) and 4P adjustments (M/N)
6. Single-sender assignment with two-source fallback (L)
7. Safety check (unchanged)

### D-006: eval4.py Design

Based on eval.py structure. Key changes:
- `env.run([agent, opponent, opponent, opponent])` — test agent in slot 0 vs 3 opponents
- Opponents: "random" (baseline), or a specified agent file path
- Metrics per game: rank (1 = winner, 4 = first eliminated), turns survived
- Aggregate: average rank, win rate (rank == 1), mean survival turns
- CLI: `python eval4.py --agent agent_vN.py --opponent random --games 20`

### D-007: 4-Player vs 2-Player Divergence Analysis

Why agent_v15 regresses on the leaderboard vs agent_v8:
- **Hypothesis A** (single-sender): Single-sender (Candidate D) reduces aggression. In 2-player this is optimal (avoids over-commitment). In 4-player, being slow means 3 opponents outpace you in territory.
- **Hypothesis B** (safety guards): OOB/sun/planet-obstruction guards from v9/v10 may filter out valid targets more often in 4-player maps (more planets, more potential obstructions).
- **Hypothesis C** (ROI formula): The ROI formula with `max(1, 100 - travel_turns)` discounts distant planets heavily. In 4-player maps (more planets, more spread out), this may cause the agent to ignore important far targets.
- **No definitive diagnosis yet** — eval4.py results on v8 vs v15 will quantify the gap.

---

## Phase 1: Design

> Outputs: `data-model.md`, `quickstart.md`

See [data-model.md](data-model.md) and [quickstart.md](quickstart.md).

### Agent Context Update

CLAUDE.md updated to reference this plan at `specs/007-more-agent-experiments/plan.md`.

### Key Design Decisions

**4-player player-count detection**: Read `obs.get("num_players", 2)` or infer from `len(set(p.owner for p in planets if p.owner >= 0)) + 1`. Use this to gate 4P-specific mechanics (M, N).

**Observation structure for fleets**: The orbit_wars engine exposes incoming fleets as `obs.fleets` (list of fleet dicts with `owner`, `ships`, `destination`, `distance_remaining`). Verify this in Phase 0 before implementing Candidate I. Fallback: if `obs.fleets` is absent or empty, Candidate I is a no-op for that turn.

**Garrison floor in 4-player**: The existing `GARRISON_FLOOR_FACTOR = 5` was tuned for 2-player. In 4-player, threats come from 3 directions; the garrison floor may need to increase. Test with factor = 7 in the 4P combined agent variant.

**Evaluation protocol for 4P candidates**:
- First run: agent_vN vs 3× random (20 games), establish baseline rank
- Second run: agent_v25 vs 3× agent_v20 (20 games), measure improvement over baseline
- Pass criterion for 4P mechanics: average rank ≤ 2.0 vs 3× random (i.e., wins more than loses in a 4-player field)
