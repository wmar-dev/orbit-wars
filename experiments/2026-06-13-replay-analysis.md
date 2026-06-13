# Replay Analysis: agent_v60 (fallback opponent) — 2026-06-13

> **Opponent note**: `opponent_agents/slawekbiel_agent.py` could not be loaded (`ModuleNotFoundError: No module named 'torch'`; torch is not installed and not in `pyproject.toml`/`uv.lock` for this Python 3.14 environment). Per `research.md`'s documented fallback, `agent_v60.py` (the Round 6 baseline-matrix runner-up) was used as the opponent instead.

**Replays analyzed**: 5 games (`agent_v64` vs `agent_v60`, `--swap` alternation, via `record_replays.py`)
**Win rate**: 80.0% (4-1)
**Median divergence turn**: 9 (n=1 loss) — **see caveat below; this trigger is noisy and not the real story of the loss.**

## Behavioral Differences Observed

1. **Planet-count lead emerges from parity after turn ~100.** Aggregated across all 5 games, planet counts are near-even through turn 100 (Turn 0-50: 2.9 vs 2.9; Turn 50-100: 10.8 vs 10.5), then diverge sharply: Turn 100-200 averages 18.5 (us) vs 11.6 (opponent) — a 60% lead — and Turn 200+ averages 24.2 vs 8.4, a ~2.9x lead.

2. **Ship totals track the planet gap and amplify it.** Turn 200+ ship totals are 1241 (us) vs 358 (opponent) — a ~3.5x gap, larger than the 2.9x planet-count gap, indicating per-planet ship accumulation also favors us once the planet lead is established.

3. **Dispatch-rate gap widens with game length, in aggregate.** Our dispatch rate exceeds the opponent's at every bucket past turn 50: 0.82 vs 0.72 (turns 50-100), 1.08 vs 0.60 (turns 100-200), 1.44 vs 0.39 (turns 200+) — up to a 3.7x gap late-game. However, this pattern **inverts during the contested mid-game window of the one loss** (see below), where the opponent out-dispatches us.

4. **The sole loss featured a single-turn 23% ship-total collapse coincident with a near-total dispatch.** In `replay_round6_4.json`, our agent sent a 111-ship dispatch from one planet at turn 90 (planet 15, angle 1.67). At turn 91, the opponent launched 3 simultaneous fleets (92+64+37 = 193 ships) from 3 different planets while we dispatched nothing; our ship total dropped from 533 → 409 (-23%) and our planet count dropped from 8 → 7 in that single turn.

## What Happens at the Divergence Turn

**Caveat on `divergence_turn=9`**: the loss game's computed divergence turn (9) is triggered by a 2.0x ratio in *home-planet garrison* ships (6 vs 12) immediately after both sides' first attack wave (turn 5) and second wave (turn 8). Both planets started symmetric (10 ships, +4/turn production) and sent waves of similar size (16 vs 13 ships); the resulting garrison ratio crossing 2.0x is an artifact of slightly different first-wave fleet sizes, not a meaningful strategic signal — planet counts remain 1/1 at this point.

**The real divergence window is turns ~77-100.** At turn 77, the game was at exact planet parity (11/11) with ships only 14% apart (479 vs 545 — opponent ahead). Over the next ~13 turns:

- Turns 82-89 (8 turns): our agent dispatched on only 2/8 turns (25%) while the opponent dispatched on 5/8 (62.5%, several multi-fleet turns). During this stretch the opponent's ship total grew from 675 → 786 (+16%) while ours shrank 693 → 613 (-12%), and we net-lost a planet (9 → 9, but with churn — captured one back at turn 83 after losing two at turn 82).
- Turn 90-91: we committed 111 ships (near the full garrison of planet 15) in a single offensive dispatch; the opponent answered with a 3-source, 193-ship coordinated counter that captured a planet and cost us 124 ships in one turn (8/13 → 7/14 planets, 533/736 → 409/775 ships).
- By turn 100, the parity at turn 77 (11/11, 479/545) had become a 4-planet, ~140-ship deficit (9/13, 562/701) — which then compounded for the rest of the game into a 0/25 wipeout by turn 155.

## Candidate Improvements

### Candidate A: Affordable Fallback Target
**Observation**: In `_greedy_moves` (agent_v64.py), each of our planets computes a single best-ROI target (`best_target`); if `mine.ships < ships_needed` for that target, the agent either tries splinter dispatch (only `step <= SPLINTER_WINDOW=30` and only if `best_target.owner == -1`) or otherwise `continue`s — skipping the planet entirely for the turn. During turns 82-89 of the loss game (well past `SPLINTER_WINDOW`), our agent dispatched on only 2/8 turns (25%) vs. the opponent's 5/8 (62.5%), while the opponent's ship total grew +16% (675→786) and ours shrank -12% (693→613) — consistent with ships sitting idle at planets whose best-ROI target was unaffordable.
**Hypothesis**: When the best-ROI target is unaffordable and splinter dispatch doesn't apply (or finds nothing), instead of skipping the planet, fall back to the best-scoring target among `candidates` for which `ships_needed <= mine.ships - floor` (i.e., something we *can* currently afford) — for any target type (neutral or enemy), at any step, not just `step <= 30`.
**Predicted effect**: Higher dispatch frequency during contested mid-game stretches (turns ~50-150), narrowing the 25% vs 62.5% gap seen in the loss's turn 82-89 window; should reduce ship stockpiling at planets that currently go idle because their #1 target is just out of reach.
**Risk**: Sending to a worse (affordable) target instead of waiting one more turn to afford the best target could waste ships on low-value captures, especially early-game where waiting 1-2 turns for the ideal target is often correct.
**Novelty check**: `SPLINTER_DISPATCH_ENABLED` (kept, v62+) is the closest existing mechanic but is restricted to `step <= 30` and `best_target.owner == -1` only — i.e., an early-game-only, neutral-only fallback. This candidate generalizes the "don't skip, send to something affordable" idea to the whole game and to enemy targets too. Not previously implemented in agent_v57-agent_v66 (the early-game-only/neutral-only restriction was never lifted in any later round) or proposed in prior experiments/ entries.

### Candidate B: Relative-Strength Garrison Scaling
**Observation**: At turn 77 of the loss game (planet parity, 11/11), the ship-total ratio was opponent/us ≈ 545/479 ≈ 1.14. By turn 90 — the turn our agent committed a 111-ship dispatch from planet 15 (near-emptying it) — the ratio had grown to 736/533 ≈ 1.38. One turn later the opponent's 3-fleet, 193-ship counter-attack cost us 124 ships (-23%) and a planet, the start of the decisive collapse. The existing `DYNAMIC_GARRISON_ENABLED` floor (`gff = 1.0 + 1.5 * min(step/400, 1.0)`) is purely a function of elapsed time — at turn 90 it evaluates to ~1.34 regardless of whether we're ahead or behind in the ship race.
**Hypothesis**: Compute the global ratio `R = total_ships_opponent / total_ships_ours` once per turn (from `obs["planets"]` + `obs["fleets"]`). When `R > 1` (we are behind in the ship race), scale up `gff` by an additional factor proportional to `R` (e.g., `gff *= min(R, 1.5)`), so planets retain larger garrisons — and therefore can't be near-emptied by a single offensive dispatch — precisely when we're already behind and most vulnerable to a punishing counter-attack.
**Predicted effect**: In contested/losing positions, larger per-planet garrisons should reduce the size and frequency of single-turn ship-total swings >20% against us (like the turn-90→91 -23% swing), at the cost of slightly smaller offensive dispatches while behind.
**Risk**: If `R > 1` persists for a long stretch (a genuinely losing game), permanently inflating the floor could starve offense entirely and turn a recoverable deficit into a guaranteed loss — i.e., it could help close games but worsen already-lost ones. The `min(R, 1.5)` cap limits this but doesn't eliminate it.
**Novelty check**: Distinct from `DYNAMIC_GARRISON_ENABLED` (time-based only), `PHASE_DETECTION_ENABLED` (discarded; scales by *fraction of planets owned*, not ship totals), and `THREAT_BUFFER_ENABLED` (discarded; adjusts buffer based on *local* per-planet incoming-fleet detection, not *global* ship-total ratio). A global relative-ship-strength signal driving the garrison floor has not been implemented in agent_v57-agent_v66 or proposed in prior experiments/ entries.

**Combination note**: Candidates A and B touch different parts of `_greedy_moves` (A: the "best target unaffordable" fallback near the end of the per-planet loop; B: the `gff`/`floor` computation near the top) and are expected to interact constructively — B raises the floor in losing positions (more ships retained), while A ensures retained-but-surplus ships still get dispatched to *some* affordable target rather than sitting idle.

## Next Step

Implement both candidates behind independent toggles (`CANDIDATE_1_ENABLED`, `CANDIDATE_2_ENABLED`) in `agent_v67.py` (forked from `agent_v64.py`, the Round 6 baseline), evaluate each independently via 50-game `--swap` h2h vs `agent_v64.py` (pass = ≥52%), then combine any passing candidates per `plan.md`'s R3 protocol.
