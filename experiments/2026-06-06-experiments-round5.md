# Experiments Round 5 — 2026-06-06

**Branch**: `025-experiments-round-5`
**Baseline**: agent_v64 (MULTI_TURN_PLAN_ENABLED, 54% vs v63)

---

## P1 — Multi-Source Coordinated Attack (DISCARDED)

**Toggle**: `MULTI_SOURCE_ENABLED`
**Hypothesis**: Beam search candidates with 2+ sources targeting the same enemy planet will enable coordinated attacks that break large garrisons no single source can handle alone.
**Change**: Added `_build_target_to_sources_map` helper and multi-source candidate block in `_gen_beam_candidates`, gated by toggle.
**Self-play result**: 12% vs v64 (50 games, --swap) — well below 52% threshold.
**Conclusion**: Multi-source coordination is actively harmful. Combined attacks replace two good individual dispatches with one over-concentrated attack, leaving other targets undefended. The beam search cannot compensate because the greedy dispatch seeds it — and the greedy dispatch over-commits to the shared target. DISCARDED.

---

## P2 — Fleet-Size-Optimized Dispatch (DISCARDED)

**Toggle**: `FLEET_SIZE_OPT_ENABLED`
**Hypothesis**: The current 2-pass `_enemy_fleet_size` underestimates ships_needed for distant high-production targets. Iterative convergence (5 passes) will compute the true self-consistent fleet size, improving capture success rate.
**Change**: Replaced `_enemy_fleet_size` with iterative convergence loop (max 5 iterations). Added oversend formula for targets with production ≥ 8 and distance > 40. Added fleet_speed cache. Added production-aware neutral capture sizing.
**Self-play result**: 10% vs v64 (50 games, --swap) after fixing a catastrophic neutral capture sizing bug (was 2%). Baseline = 54%.
**Conclusion**: The iterative convergence gives a higher ships_needed value, over-committing ships to each target. The original 2-pass correction is a better heuristic — it underestimates slightly, which is fine because the beam search compensates by evaluating the full game state. The fleet_speed cache was separately verified as harmless (neutral behavior change). DISCARDED.

---

## P3 — 4-Player State Adaptation (DISCARDED)

**Toggle**: `FFA_ADAPT_ENABLED`
**Hypothesis**: Adjusting garrison floor factor (1.2× for 3 opponents, 0.8× for 1 opponent) will improve 4-player FFA performance. The high garrison prevents over-extension in 4-player, while the low garrison enables aggressive endgame play.
**Change**: Added `_count_opponents` helper. Modified `_greedy_moves` gff computation and SPLINTER_WINDOW to use opponent-dependent multipliers.
**Self-play result**: 48% vs v64 (50 games, --swap) — slightly below threshold. Effectively neutral.
**Conclusion**: The adaptation is tuned for 4-player FFA but evaluated on 2-player head-to-head games (where opponent count is always 1). The 0.8× multiplier in endgame makes the agent slightly more aggressive but not enough to move the needle. A 4-player-only eval might show improvement but the agent needs to pass 2-player first. DISCARDED.

---

## P4 — Endgame Elimination Focus (DISCARDED)

**Toggle**: `ENDGAME_FOCUS_ENABLED`
**Hypothesis**: When only 1 opponent remains, removing neutral planets from the target list will focus all firepower on eliminating the last opponent.
**Change**: Filter targets to `owner >= 0` when opponent count ≤ 1. Reduce garrison floor by 0.85×.
**Self-play result**: 0% vs v64 (50 games, --swap) — catastrophic failure.
**Conclusion**: The filter removes all neutral planets, so if the opponent has few planets, the target list becomes empty. The agent sends no ships in endgame and loses every game. This approach is fundamentally flawed — neutrals should be deprioritized, not removed. DISCARDED.

---

## Combined Evaluation

All four experiments failed their individual evals. No combined evaluation run.

**Overall result**: No improvement over v64 baseline. Agent_v65 remains functionally equivalent to v64 (all v65 toggles set to False).
