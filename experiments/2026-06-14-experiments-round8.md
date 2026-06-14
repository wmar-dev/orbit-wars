# Experiments — Round 8 (Advanced Agent Techniques)

**Baseline**: `agent_v68.py` (frozen, current best — 64% vs `agent_v64`, 0% vs `slawekbiel_agent`)
**Working file**: `agent_v69.py` (fork of `agent_v68.py`)
**Replay analysis**: [2026-06-14-round8-replay-analysis.md](2026-06-14-round8-replay-analysis.md) — confirmed ranking A > C > B

## Candidate A — Global coordinated allocation (`GLOBAL_ALLOC_ENABLED`)

**Design**: Replace the per-planet greedy target-claiming loop in `_greedy_moves` with a joint
(source, target) assignment (`_global_alloc_moves`). All (source, target) pairs with a safe
path are scored with the same per-source-normalized ROI/reward blend as the per-planet path.
Pairs are assigned highest-score-first; a source whose top pick is claimed by a higher-scoring
pair is redirected to its next-best remaining target. A source whose best-remaining target is
unaffordable or path-unsafe (post enemy-reinforcement check) gives up entirely for the turn —
mirroring the per-planet path's behavior exactly (with `MULTI_DISPATCH_ENABLED=False`, an
unaffordable `best_target` causes an immediate `continue` *before* the splinter-dispatch block,
making splinter dead code in `agent_v68`; `_global_alloc_moves` intentionally does not
resurrect it, to keep Candidate A an isolated change).

**Debugging note**: an initial implementation fell through to a splinter-style rescue for
unaffordable targets, which `agent_v68` never reaches. This produced a 22–24% self-play result
(severe apparent regression) that was actually "Candidate A + accidental splinter revival", not
Candidate A alone. Verified via direct `_greedy_moves` comparison on identical turn-0 state
(seed=0): `agent_v68` → `[]`, buggy `agent_v69` → a 9-ship dispatch. After removing the
splinter fallback (matching `agent_v68`'s give-up-on-unaffordable behavior), the two agree
exactly for the single-source case.

**Isolation**: only `GLOBAL_ALLOC_ENABLED=True`; `DEEP_SEARCH_ENABLED=False`, `REGROUP_ENABLED=False`.

| Eval | Result | Bar | Verdict |
|------|--------|-----|---------|
| T007 — self-play vs `agent_v68` (50 games, `--swap`) | **56.0%** (28/50) | ≥52% | PASS |
| T008 — benchmark vs `slawekbiel_agent` (30 games, `--swap`) | **0.0%** (0/30) | ≥0% (no regression) | PASS (ties v68; misses SC-001 stretch >0%) |
| T009 — timing (10-game `--timing` sample) | p50=3.0ms p95=9.1ms p99=12.4ms | < budget, zero forfeits | PASS |

**Candidate A verdict: PASS** — beats `agent_v68` 56.0% in self-play, ties (does not regress) the
0% benchmark, zero timing/safety violations.

## Candidate B — Deeper time-bounded search (`DEEP_SEARCH_ENABLED`)

**Design**: `_deep_search` wraps the existing `_gen_beam_candidates` candidate list in an anytime
iterative-deepening loop (`_score_state_at_depth`): re-score the SAME candidate list at
progressively larger simulation depths, starting at `SEARCH_DEPTH=10` and incrementing by
`DEEP_SEARCH_DEPTH_STEP=10` each pass, keeping the best-scoring candidate from the deepest pass
that completes within `DEEP_SEARCH_BUDGET_MS=700`. Falls back to the greedy move set if no pass
completes (FR-010 graceful degradation).

**Isolation**: only `DEEP_SEARCH_ENABLED=True`; `GLOBAL_ALLOC_ENABLED=False`, `REGROUP_ENABLED=False`.

| Eval | Result | Bar | Verdict |
|------|--------|-----|---------|
| T011 — timing (3-game `--verbose` dense-board sample) | p99=700.1ms, all games completed cleanly (exit 0), zero forfeits/exceptions | < actTimeout, zero forfeits | PASS |
| T012 — self-play vs `agent_v68` (50 games, `--swap`) | **44.0%** (22/50) | ≥52% | **FAIL** |
| T013 — benchmark vs `slawekbiel_agent` (30 games, `--swap`) | **0.0%** (0/30) | ≥0% (no regression) | PASS (ties v68; no SC-001 gain) |

**Analysis**: A 3-game preview during T011 happened to show 3/3 wins (noise from n=3). The
50-game T012 result (44.0%) is a clear regression below even the 50/50 equivalence point — deeper
iterative-deepening search is making `agent_v69` play *worse* than the depth-10 baseline. This is
consistent with a classic search-pathology pattern: `_score_state_at_depth`'s forward simulation
doesn't model the opponent's actual responses (it continues the opponent's existing fleets/production
with no new adversarial dispatches), so deeper passes extrapolate further into an increasingly
unrealistic future and can "confidently" prefer a candidate that a shallower, more-accurate-by-proxy
depth-10 search would have correctly avoided.

**Candidate B verdict: FAIL** — safe (zero timing/forfeit violations, T011/T013 pass) but loses
self-play 44.0% vs the ≥52% bar. `DEEP_SEARCH_ENABLED` stays `False` and is excluded from the
Phase 6 combination, per the negative-result precedent (Rounds 5/7).

## Candidate C — Regroup/reinforcement repositioning (`REGROUP_ENABLED`)

**Design**: `_regroup_moves` ranks owned planets by "stress" (`sum(enemy.ships / (dist+1) for
enemy in enemy_planets)`, enemy-owned planets only) and dispatches a planet's integer surplus
above the garrison floor (when ≥ `REGROUP_MIN_SURPLUS=3.0` and not already dispatching this
turn) toward the highest-stress owned planet that is more stressed than itself, over a
`_path_safe` orbital-lead path.

**Isolation**: only `REGROUP_ENABLED=True`; `GLOBAL_ALLOC_ENABLED=False`, `DEEP_SEARCH_ENABLED=False`.

| Eval | Result | Bar | Verdict |
|------|--------|-----|---------|
| T016 — self-play vs `agent_v68` (50 games, `--swap`) | **8.0%** (4/50) | ≥52% | **FAIL** (severe) |
| T017 — benchmark vs `slawekbiel_agent` (30 games, `--swap`) | **0.0%** (0/30) | ≥0% (no regression) | PASS (ties v68; no SC-001 gain) |

**Root-cause analysis (T016's severe 8% regression)**: file-based debug logging (`/tmp/regroup_debug.log`,
removed after diagnosis) on a single seed=0 game showed `_regroup_moves` firing every ~3 turns,
sending 9 ships from planet 20 (our actively-expanding front — captured planet 21, then kept
growing surplus to launch new attacks in `agent_v68`) *backward* to planet 12 (our quiet starting
planet, idle since turn 12). The verbose harness's angle→nearest-non-own-planet mapping
mis-displayed these regroup moves as repeated "Planet 20 → Planet 21 (ships=9)" attacks —
in reality, planet 20's surplus was being drained to planet 12 every 3 turns and then sitting
unused (planet 12 never dispatches again).

Why: with typically only **one enemy-owned planet** on the board in the early/mid game,
`stress(p) = enemy.ships / (dist(p, enemy_home) + 1)` reduces to "inverse distance to the
enemy's home planet" — a static geometric property. Here planet 12 (idle) is marginally closer
to the enemy home (stress=0.27) than planet 20 (actively expanding, stress=0.26), so
`_regroup_moves` always picks planet 12 as "front" and bleeds planet 20's surplus into it. The
heuristic conflates "geometrically close to the opponent's home" with "needs reinforcement,"
when it should track "actively expanding / under real pressure." This starves the active
expansion front of the growing surplus it needs to launch follow-up attacks, while the
opponent's undisturbed surplus snowballs — directly explaining the 8% result.

This is a **design flaw in the stress heuristic**, not a small mechanical bug like Candidate A's
splinter confound — a real fix would require redefining "front" using dispatch activity / capture
recency rather than static inverse-distance-to-enemy-home, which is out of scope for an isolated
toggle this round.

**Candidate C verdict: FAIL** — ties (does not regress) the benchmark, but a severe 8.0% self-play
result, far below the ≥52% bar. `REGROUP_ENABLED` stays `False` and is excluded from the Phase 6
combination, per the negative-result precedent (Rounds 5/7).

## Combination + re-verification

Only **Candidate A** passed (Candidates B and C both FAIL). Per tasks.md's adoption rule, the
"combination" of all passing candidates is therefore Candidate A alone:
`GLOBAL_ALLOC_ENABLED=True`, `DEEP_SEARCH_ENABLED=False`, `REGROUP_ENABLED=False` — the same
config as Candidate A's isolated eval (T007/T008).

| Eval | Result | Bar | Verdict |
|------|--------|-----|---------|
| T019 — combined self-play vs `agent_v68` (50 games, `--swap`) | **56.0%** (28/50) | ≥52% | PASS (identical config/seeds to T007, reproduced exactly) |
| T020 — combined benchmark vs `slawekbiel_agent` (30 games, `--swap`) | **0.0%** (0/30) | ≥0% (no regression) | PASS (identical config/seeds to T008, reproduced exactly; ties v68) |
| T021 — opponents sweep (20 games each) | sigmaborov 100%, dylanxue04 100%, yusufmurtaza 100%, slawekbiel 0% (3 opponents have pre-existing syntax errors, unrelated to our agent) | no regression | PASS |

**Adoption decision (T022)**: combo ≥52% self-play (56.0%) AND no benchmark regression (0.0%,
ties `agent_v68`) → **adopt `agent_v69` as the new current best**, with
`GLOBAL_ALLOC_ENABLED=True`, `DEEP_SEARCH_ENABLED=False`, `REGROUP_ENABLED=False`.

## Conclusion

Round 8 ships **`agent_v69`** as the new current best, carrying **Candidate A (global coordinated
allocation)** only:

- **vs `agent_v68`** (50-game `--swap` self-play): **56.0%** (28/50) — beats the previous best.
- **vs `slawekbiel_agent`** (30-game `--swap` benchmark): **0.0%** (0/30) — ties `agent_v68`'s 0%;
  the SC-001 stretch goal (>0%) was not met.
- **Opponents sweep**: 100% vs the three reachable downloaded opponents, no regressions.
- **Safety/timing**: zero sun/OOB/forfeit issues across all evals; p99 turn time ≈12.4ms, far
  under budget.

Candidates B (deeper iterative-deepening search) and C (regroup/reinforcement repositioning) were
both implemented, evaluated in isolation, and **rejected**:

- **Candidate B** (44.0% self-play, FAIL): deeper search degraded play — a search-pathology
  pattern where `_score_state_at_depth`'s forward simulation (which doesn't model the opponent's
  real responses) extrapolates further into an increasingly unrealistic future at greater depths.
- **Candidate C** (8.0% self-play, severe FAIL): the "stress" heuristic (inverse-distance to
  enemy-owned planets) reduces to "distance to the enemy's home planet" when only one enemy
  planet exists (the common early/mid-game case), and repeatedly drained our actively-expanding
  front planet's surplus into a quiet rear planet — crippling expansion momentum.

Both remain in `agent_v69.py` as dead code behind `False` toggles, documented here as negative
results (mirroring Rounds 5/7). `slawekbiel_agent` remains an unbeaten 0% benchmark and the
primary target for future rounds — likely requiring a structural change (e.g., a genuinely
adversarial opponent model in the forward sim, addressing Candidate B's root cause) rather than
another allocation/positioning tweak.
