# Replay Analysis: slawekbiel_agent — 2026-06-13 (Round 7)

**Replays analyzed**: 5 games (`replays/replay_slawekbiel_agent_20260613_222153_00{0..4}.json`)
**Win rate**: 0.0% (0/5) — consistent with the full T004 sweep (0/20)
**Median divergence turn**: 9 (range 8-64; 4/5 games diverge at turn 8-11)

## Summary Statistics

```
Games analyzed: 5
Win rate (our agent): 0.0%

Per-turn-bucket averages (our agent / opponent):
  Turn 0-50     : planets 2.8 / 4.3   ships 114 / 130   dispatches/turn 0.42 / 0.53
  Turn 50-100   : planets 4.7 / 14.2   ships 251 / 716   dispatches/turn 0.32 / 0.92
  Turn 100-200  : planets 2.1 / 12.1   ships 180 / 534   dispatches/turn 0.00 / 0.94
  Turn 200+     : planets 0.0 / 0.0   ships 0 / 0   dispatches/turn 0.00 / 0.00

Per-game outcomes:
  game 000: LOSS  end=88   divergence=8   dispatches=[17, 49]
  game 001: LOSS  end=95   divergence=11  dispatches=[89, 62]
  game 002: LOSS  end=127  divergence=64  dispatches=[21, 64]
  game 003: LOSS  end=105  divergence=9   dispatches=[56, 28]
  game 004: LOSS  end=86   divergence=8   dispatches=[48, 111]
```

## Behavioral Differences Observed

1. **Opening-move latency**: `slawekbiel_agent` issues its first dispatch on turn **1** in 4/5 games (using its entire ~10-14-ship starting fleet to grab a cheap nearby neutral). `agent_v64` issues its first dispatch on turns **4, 5, 7, 8, 8** respectively — a 3-7 turn delay. In the one game where both wait (game 002, turn 17), the divergence turn is also a huge outlier (64) rather than ~9, suggesting the early-rush gap is *the* dominant driver of the typical fast loss.

2. **Second-planet race, decided by turn ~9**: in 4/5 games, the `divergence_turn` (first time either side has ≥2x the other's planet count or ship total) lands at turn 8, 8, 9, or 11 — i.e., almost immediately after the opponent's turn-1 fleet arrives and converts into a second planet (e.g. game 000: opponent goes from 1→2 planets at turn 8 while we're still on 1; game 004: ships go 19 vs 39 at turn 8, a 2.05x gap, triggered purely by our planet 8 having just launched its first dispatch and dropped from 38→19 ships while the opponent's planet 11 has been compounding production since turn 2).

3. **Expansion-rate gap widens through the mid-game and we start *losing* planets, not just falling behind**: planets 2.8/4.3 (turn 0-50) → 4.7/14.2 (turn 50-100) → 2.1/12.1 (turn 100-200). Our planet count *drops* from 4.7 to 2.1 between these buckets while the opponent's keeps climbing — a 5.8x gap by turn 100+.

4. **We go essentially idle in the late game while the opponent keeps dispatching**: dispatches/turn fall from 0.42 (turn 0-50) to 0.32 (turn 50-100) to **0.00** (turn 100-200), while the opponent holds steady at 0.92-0.94/turn throughout turns 50-200. Once we fall behind, our agent stops acting almost entirely.

## What Happens at the Divergence Turn

At `divergence_turn - 10`..`divergence_turn`, the picture is consistent across games 000/001/003/004: both sides start at 1 planet each with ~10-14 ships. The opponent's turn-1 dispatch (its *entire* starting fleet, e.g. 12-14 ships) arrives around turn 8-10 and converts a nearby neutral planet (production 4-5) into its second planet. Meanwhile `agent_v64`'s home planet sits idle, accumulating ships from its own production (because its highest-ROI reachable target costs more ships than it currently has, and `SPLINTER_DISPATCH_ENABLED`'s surplus — `ships - floor` — isn't enough to afford even the cheapest neutral yet). By the time `agent_v64` finally dispatches (turn 4-8), it commits its *entire* accumulated fleet in one shot, immediately dropping its own ship total and triggering the 2x-ship-ratio divergence trip in the opponent's favor (e.g. game 004: ships go from [38,35] at turn 7 to [19,39] at turn 8 — purely because *we* just spent our fleet).

## Candidate Improvements

Both candidates implement the **same additive mechanism** — give an *idle* planet (one for which `_greedy_moves` proposed no dispatch this turn) an extra beam-search candidate that rushes its full fleet to the cheapest target it can outright afford (`mine.ships >= ships_needed`, no garrison/floor reservation) — applied to two **disjoint, non-overlapping turn ranges** so each can be evaluated independently and, if both pass, combined without interaction:

- Candidate 1: `step <= OPENING_RUSH_WINDOW` (opening, targets behavioral differences #1-#2)
- Candidate 2: `step > OPENING_RUSH_WINDOW` (established game, targets behavioral differences #3-#4)

`OPENING_RUSH_WINDOW = 20` — comfortably covers the observed first-dispatch turns (4-8, one outlier at 17) and the median divergence turn (9).

Both candidates are purely **additive to `_gen_beam_candidates`**: the existing greedy candidate and the `MULTI_TURN_PLAN_ENABLED` "skip" (wait-and-accumulate) candidate are untouched and still scored by the unchanged 10-turn forward-sim (`_beam_search`/`SEARCH_DEPTH=10`). The new "rush" candidate only gets chosen if its forward-simmed score beats "skip" and the greedy proposal — so waiting remains available and competitive whenever it's genuinely better. Neither candidate modifies `_greedy_moves`, `gff`, the garrison `floor`, or `SPLINTER_DISPATCH_ENABLED`.

### Candidate A (→ `CANDIDATE_1_ENABLED`): Opening rush
**Observation**: `slawekbiel_agent` dispatches its starting fleet at turn 1 in 4/5 games; `agent_v64` waits until turns 4-8, and the resulting second-planet race is decided by the median divergence turn of 9 — almost always in the opponent's favor.
**Hypothesis**: Give idle planets in turns 0-20 an additional beam candidate that immediately rushes the cheapest outright-affordable target (neutral or enemy) with the planet's full fleet. The forward-sim will only pick this if it actually beats waiting.
**Predicted effect**: Earlier second-planet captures, fewer turn-8-9 divergence losses, higher win rate vs `agent_v64` (which never considers this option for an idle home planet).
**Risk**: An early all-in rush could leave the home planet under-defended if an enemy fleet is inbound during the 0-20 turn window; mitigated by the 10-turn forward-sim, which would penalize the rush candidate's score if it leads to a lost planet within the sim horizon.

### Candidate B (→ `CANDIDATE_2_ENABLED`): Established-game rush
**Observation**: From turn 50 onward, `agent_v64`'s dispatch rate falls from 0.32/turn to 0.00/turn while `slawekbiel_agent` holds steady at ~0.93/turn; our planet count *drops* (4.7 → 2.1) over the same window instead of growing.
**Hypothesis**: The same idle-planet rush candidate, applied for `step > 20`, gives planets that `_greedy_moves` skipped (because their best-ROI target isn't affordable within the garrison floor) a chance to spend their full fleet on a cheaper target instead — keeping pressure on instead of going idle.
**Predicted effect**: Higher mid/late-game dispatch rate, slower planet-count decline, higher win rate vs `agent_v64`.
**Risk**: Could over-commit ships from planets that should stay garrisoned against a brewing attack; again mitigated by the 10-turn forward-sim score comparison against "skip".

### Novelty / Guardrail Check
- Neither candidate exists in `agent_v57.py`-`agent_v67.py` — there is currently no "idle planet → extra rush beam candidate" mechanism; the closest existing mechanism (`SPLINTER_DISPATCH_ENABLED`) only fires *inside* `_greedy_moves`'s per-planet loop when a target was already selected but unaffordable, is gated to `step <= 30` and neutral-only, and is a *replacement* of the greedy target rather than an *additional* beam-search alternative.
- **`avoids_prior_failure`** (Round 6 Candidate 1, "affordable fallback", 6% severe regression): that candidate generalized `SPLINTER_DISPATCH_ENABLED` so it always found *some* affordable target inside `_greedy_moves`, which short-circuited the `MULTI_TURN_PLAN_ENABLED` "skip" beam candidate's deliberate wait-and-accumulate option. Both of our candidates instead **add a new candidate to the beam search's list without touching the greedy proposal or the existing skip candidate** — "wait" remains a first-class, separately-scored option in every case. This directly avoids the prior failure mode.
- Round 6 Candidate 2 (global relative-strength garrison scaling, 48% wash, suggested a local/per-planet/threat-based alternative for a future round): not applicable — neither candidate touches `gff`, the garrison `floor`, or any relative-strength ratio.

## Next Step

Implement both candidates in `agent_v68.py` behind `CANDIDATE_1_ENABLED` / `CANDIDATE_2_ENABLED`, eval each independently vs `agent_v64` (50 games, `--swap`), combine passers, and re-check vs `slawekbiel_agent`.
