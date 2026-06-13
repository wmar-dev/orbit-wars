# Experiments Round 6 — Phase C (agent_v67)

**Baseline**: `agent_v64.py` (Round 6 baseline, see `experiments/2026-06-13-round6-baseline-matrix.md` — beats `agent_v58.py` 52.0% and `agent_v60.py` 60.0% h2h, 50 `--swap` games each)
**Fork**: `agent_v67.py` = copy of `agent_v64.py` with 2 independent toggle-gated candidates from `experiments/2026-06-13-replay-analysis.md`
**Pass threshold**: ≥52.0% win rate over 50 `--swap` games vs `agent_v64.py`

## Candidate 1: Affordable Fallback Target (`CANDIDATE_1_ENABLED`)

**Hypothesis**: In `_greedy_moves`, when a planet's best-ROI target is unaffordable (`mine.ships < ships_needed`) and splinter dispatch doesn't apply, the planet is currently skipped entirely for the turn. Falling back to the best target we *can* afford (any owner type, any step — generalizing `SPLINTER_DISPATCH_ENABLED`'s early-game/neutral-only restriction) was expected to reduce idle ship stockpiling, narrowing the dispatch-frequency gap observed in the loss game's turns 82-89 (25% vs opponent's 62.5%).

**Change**: Added `_best_affordable_target()` helper; when the best-ROI target is unaffordable, search all `roi_scores` candidates for the highest-blended-score target with `ships_needed <= mine.ships`, and dispatch there instead of skipping the planet.

**Result**: `uv run python eval.py h2h --agent0 agent_v67.py(CANDIDATE_1_ENABLED=True) --agent1 agent_v64.py --games 50 --jobs 4 --swap` → **6.0% (3/50 wins) — FAIL** (severe)

**Conclusion**: **DISCARDED.** The 6% result is far below even a "neutral" outcome, indicating the fallback isn't just unhelpful but actively harmful. Most likely explanation: many "best target unaffordable" cases are actually situations where `MULTI_TURN_PLAN_ENABLED`'s beam-search "skip" candidate (wait-and-accumulate) is the *correct* choice — the lookahead search already evaluates waiting vs. dispatching to alternatives and picks waiting because it scores better over the `SEARCH_DEPTH=10` horizon. Greedily forcing a dispatch to a lower-ROI "affordable" target at the `_greedy_moves` stage short-circuits this, repeatedly committing ships to low-value captures (small neutrals, marginal enemy planets) instead of building toward a high-value target — compounding into a large disadvantage. Do not revisit this direction without first disabling `MULTI_TURN_PLAN_ENABLED` to isolate the interaction.

## Candidate 2: Relative-Strength Garrison Scaling (`CANDIDATE_2_ENABLED`)

**Hypothesis**: The existing `DYNAMIC_GARRISON_ENABLED` floor (`gff = 1.0 + 1.5 * min(step/400, 1.0)`) depends only on elapsed time, not on whether we're ahead or behind in the ship race. In the loss game, the opponent/ours ship-total ratio grew from ~1.14 (turn 77, planet parity) to ~1.38 (turn 90, just before our agent committed a 111-ship near-total dispatch that was punished by a 193-ship counter-attack the following turn). Scaling `gff` up by `min(ratio, 1.5)` whenever the opponent's total ships exceed ours was expected to preserve larger garrisons in losing positions, preventing near-total dispatches at the worst possible time.

**Change**: After computing `gff`, sum total ships (planets + in-flight fleets) for `player` vs. all other owners. If `total_opp > total_mine`, multiply `gff *= min(total_opp / total_mine, RELATIVE_STRENGTH_GFF_CAP=1.5)`.

**Result**: `uv run python eval.py h2h --agent0 agent_v67.py(CANDIDATE_2_ENABLED=True) --agent1 agent_v64.py --games 50 --jobs 4 --swap` → **48.0% (24/50 wins) — FAIL** (statistically indistinguishable from even — `[EVEN]`)

**Conclusion**: **DISCARDED.** The change is roughly neutral (48% vs. baseline's implicit 50%), not a clear regression like Candidate 1, but it does not meet the ≥52% bar. Raising the garrison floor when behind reduces offensive surplus precisely when the agent most needs to counter-attack to recover — for every game where it prevented a punishing counter-attack (as hypothesized from the loss-game trace), it likely cost tempo in another game where the higher floor delayed a recovery push. Net effect: a wash. A more targeted, *local* (per-planet, threat-detection-based) garrison adjustment — rather than this *global* ship-ratio scaling — might fare better, but is a different candidate for a future round.

## Combination (T016)

**N/A** — neither candidate reached the 52% pass threshold, so per the protocol no combined evaluation was run. Both `CANDIDATE_1_ENABLED` and `CANDIDATE_2_ENABLED` remain `False` in `agent_v67.py`, making it functionally identical to `agent_v64.py` (same precedent as `agent_v65.py`, where all 4 Round 5 candidates were discarded and `v65 ≡ v64`).

## Outcome

Round 6 Phase C produced no improvement over the Round 6 baseline. `agent_v64.py` remains the strongest available heuristic agent (per `experiments/2026-06-13-round6-baseline-matrix.md`: beats `agent_v58.py` 52.0% and `agent_v60.py` 60.0% h2h). `agent_v67.py` is kept as a record of this round's discarded experiments (toggles default `False`). README's Agents table and the Makefile's `AGENT`/`RENDER_AGENT` are updated to reflect `agent_v64.py` as the current best (T018/T019), since `<BASELINE> = agent_v64.py != agent_v58.py`.
