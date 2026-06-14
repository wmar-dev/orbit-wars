# Replay Analysis: slawekbiel_agent — 2026-06-14

**Replays analyzed**: 5 games (`agent_v68` vs `opponent_agents/slawekbiel_agent.py`, fresh capture via `record_replays.py`)
**Win rate**: 0% (0/5)
**Median divergence turn**: 6 (range 1–32)

## Behavioral Differences Observed

1. **Mid-game expansion snowball (turns 50–100) is the single largest gap in the dataset.** `slawekbiel_agent` averages 15.1 planets and 782 ships in this bucket vs our 4.9 planets and 240 ships — a **3.1x planet gap** and **3.3x ship gap**. This is where the game is effectively decided.
2. **Dispatch rate inverts between the opening and midgame, in opposite directions for the two agents.** Our dispatch rate drops from 0.55/turn (0–50) to 0.30/turn (50–100); `slawekbiel_agent`'s rises from 0.50/turn to 0.93/turn. The opponent ramps aggression exactly when we throttle back — almost a mirror image.
3. **The opening (turns 0–50) is roughly even or slightly in our favor**: 140 ships / 3.4 planets (us) vs 132 ships / 4.2 planets (opponent). The failure is not in opening play — it emerges entirely in the 50–100 turn window.
4. **At the divergence turn, the opponent frequently commits large, decisive single dispatches** (21–71 ships — often its entire fleet) while our concurrent dispatches are smaller (8–16 ships): e.g. game 002 turn 11 (opp dispatches 21), game 003 turn 6 (opp dispatches 25/30), game 004 turn 31 (opp dispatches 71, essentially its whole fleet).
5. **Late-game (100–200) shows both sides' planet counts receding from their bucket-2 peaks** (15.1→6.7 opponent, 4.9→2.6 us) — consistent with 4/5 games ending by turn ~100 (the snowball from bucket 2 finishes the game before bucket 3 fully populates).

## What Happens at the Divergence Turn

Across the 4 early-divergence games (turns 1, 6, 6, 7), the pattern is consistent: by a few turns after divergence, `slawekbiel_agent` either captures a second planet alone (game 000: planet count 1→2 for the opponent at turn 6 while we remain at 1) or both sides capture simultaneously but the opponent commits a markedly larger fleet to do it (games 002/003: opponent dispatches 21–30 ships vs our 8–12). Game 001 diverges immediately — the opponent dispatches its *entire* starting garrison (10 ships) on turn 0, one turn before our first dispatch, and by turn 6 holds 54 total ships vs our 12 while planet counts remain tied at 1. Game 004 (the one long game, divergence=32) shows the same shape late: the opponent throws 71 ships (its whole fleet) from one planet at turn 31, captures a second planet by turn 35, while our ship total collapses from 72→19 without any capture — we lost a fight rather than expanding.

## Candidate Confirmation / Re-Ranking (vs research.md R1)

The evidence **confirms** R1's priority order without contradiction, and sharpens the mechanism for each:

- **Candidate A (Global coordinated allocation) — CONFIRMED, primary.** The 50–100 turn bucket's 3.1x planet / 3.3x ship gap *is* the expansion-snowball that global (source,target) scoring produces: the opponent commits to many simultaneous high-value targets while our per-planet greedy claim serializes and under-commits.
- **Candidate C (Regroup/reinforcement repositioning) — CONFIRMED, secondary.** The dispatch-rate inversion (ours 0.55→0.30, theirs 0.50→0.93) directly matches "idle rear-planet surplus not flowing toward active fronts" — exactly the gap a regroup gradient targets. This is a distinct, complementary mechanism to A (A picks better targets for active dispatches; C increases the *number* of ships available to dispatch from quiet planets).
- **Candidate B (Deeper time-bounded search) — NEUTRAL, hedge retained.** No directly observed metric in this replay set isolates "search depth" as the cause (the gap looks structural/allocation-driven, not move-quality-within-a-fixed-candidate-set). Retained per R1's rationale as an orthogonal technique class (SC-006) and a hedge if A/C wash.

**Ranking**: A > C > B — unchanged from research.md, evidence-confirmed.

## Next Step

Proceed to Phase 3 (Candidate A implementation) per tasks.md T006, with C and B as planned independent increments (T015, T010).
