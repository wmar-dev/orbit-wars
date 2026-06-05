# Replay Analysis: slawekbiel_agent — 2026-06-04

**Replays analyzed**: 7 games  
**Win rate**: 0%  
**Median divergence turn**: 8 (min: 1, max: 17)  
**All games ended by turn 110** — slawekbiel dominates every game start to finish

---

## Behavioral Differences Observed

### 1. Turn-0 dispatch: opponent launches immediately, we wait in 2/7 games

At turn 0 the opponent dispatches in 71% of games (avg 0.71 dispatches/turn) vs our 57%. More importantly, when the opponent dispatches on turn 0 it sends **8.8 ships on average**; we send 8.2. This is a minor difference in itself, but the opponent's early dispatch consistently reaches a neutral planet 1–3 turns before ours, creating the 2× planet-count trigger that the divergence metric catches at turns 1–8. In game 003 (div=1), the opponent dispatched turn 0 and we didn't — by turn 1 the ship ratio was 6:13 (our ships drained, opponent stacked from fleet return).

### 2. Mid-game (turns 30–50): opponent dispatches 2–3× more per turn than us

Between turns 30–49 the opponent averages **0.92 dispatches/turn vs our 0.43** — more than 2× our rate. In multiple individual turns (35, 38, 43, 45, 47) the opponent fires 1.0–1.71 dispatches while we fire 0.14–0.29. This is the window where the opponent's planet advantage compounds: each additional planet adds production, which is immediately reinvested into more dispatches. Our agent appears to be waiting for a larger accumulation threshold before sending.

### 3. Opponent uses larger fleets when it matters (turns 20–30)

Between turns 20–30, the opponent's average dispatch size jumps to **27–64 ships** while ours stays at **10–20 ships**. Example: turn 24 — opponent average dispatch is 64 ships; ours is 14.7. This means the opponent captures higher-garrison neutral and enemy planets that we would pass over or wait to afford. The opponent is willing to drain a planet heavily; we garrison conservatively.

### 4. Ship-per-planet ratio diverges after turn 50

In turns 0–50 both agents hold roughly equal ships-per-planet (~30.8 vs 25.2 — actually we're marginally higher, meaning we're sitting on ships). By turns 50–100 the opponent holds **51.2 ships/planet vs our 43.9**, and by turns 100–200 the gap explodes: **91.4 vs 56.1**. This confirms the opponent is not just capturing more planets — it is also more efficiently converting those planets' production into active fleet power.

### 5. We dispatch far more in the 100–200 range — but it's too late

Strangely, in turns 100–200 **we dispatch more** (0.375/turn vs 0.083/turn for the opponent). The opponent has essentially stopped sending fleets because it has already won — it holds 9.8 planets to our 15.7 at that point (we expanded late when there was nothing left to contest). Our late-game dispatch activity is desperate mopping-up, not strategic.

---

## What Happens at the Divergence Turn

The divergence is **entirely an early-game expansion speed problem**. In the 5 games with divergence at turns 1–9, the pattern is identical: the opponent dispatches on turn 0 or turn 2 and captures a neutral planet **1–3 turns before we do**. With 2 planets to our 1, its production advantage immediately compounds. By the time we capture our second planet (often the same neutral we were targeting), the opponent is already attacking a third. In game 000 (div=8): our agent dispatched on turn 0 (sending 8 ships to a distant target), then sat for 7 turns accumulating ships while the opponent captured turn 8. We had 54 ships stockpiled on our home planet — plenty to have captured 2 neutrals by then.

The core failure: **we accumulate ships on home planets for 5–15 turns instead of dispatching them at smaller sizes toward cheap nearby neutrals.** The opponent fires smaller, more frequent fleets and compounds the production advantage from turn 2 onward.

---

## Candidate Improvements

### Candidate A: Lower the early-game dispatch threshold

**Observation**: In turns 0–30, we dispatch 0.38/turn with avg 13 ships each. The opponent dispatches 0.56/turn with avg 20 ships. But our home planet accrues 50+ ships (game 000: 54 ships on home planet at turn 8) while only 1 neutral was captured. We are waiting until we can afford something — but the cheapest nearby neutrals cost far less than we are holding.

**Hypothesis**: Our garrison floor or ROI threshold causes us to wait for a guaranteed-capture fleet rather than sending a minimal fleet immediately. Reduce the early-game minimum fleet size (or the ROI threshold for neutral captures specifically) so that small fleets are dispatched in turns 1–10 toward the nearest neutral planets, even if the margin is thin.

**Predicted effect**: Planet count in turns 0–50 rises from 3.39 to ~4.0+, closing the gap with the opponent (3.72). Divergence turn should move from median 8 to 20+.

**Risk**: Sending too-small fleets to neutrals could result in failed captures if the neutral gains garrison faster than expected, or if the opponent intercepts. May need a floor of "dispatch if guaranteed capture within N turns."

---

### Candidate B: Increase dispatch frequency in turns 30–50 (multi-planet attack)

**Observation**: In turns 30–50 the opponent fires 0.92 dispatches/turn vs our 0.43. In specific turns (38, 43, 45) the opponent sends 1.0–1.71 fleets while we send 0–0.29. At turn 38 in game 000 our agent had 152 ships across 4 planets — enough to send multiple fleets simultaneously — but dispatched only 1. The opponent sent 3 that turn.

**Hypothesis**: Our agent's `_single_sender_coordination` logic serialises dispatches — only one planet sends per turn to avoid double-targeting. This is conservative. Relax this constraint: allow 2 planets to dispatch simultaneously if they target different planets and each source retains garrison above the floor.

**Predicted effect**: Dispatch rate in turns 30–50 rises from 0.43 to ~0.7–0.9/turn, better matching opponent aggression. Ship-per-planet ratio in turns 50–100 closes from 43.9/51.2 toward parity.

**Risk**: Two simultaneous dispatches may over-commit if a defence need emerges mid-flight. The garrison floor should still be respected per sender.

---

### Candidate C: Send larger fleets toward enemy planets in the mid-game

**Observation**: In turns 20–30 the opponent's average dispatch is 27–64 ships; ours is 10–20. The opponent is willing to drain a planet to 1× garrison to capture a high-value target. Our fleet sizing is conservative — we compute garrison floor and hold back a buffer. Result: we can afford a capture but pass on it.

**Hypothesis**: The garrison defense buffer (`production × 2` added in v50) may be too conservative in the early-mid game. When we are not under active threat (no enemy fleets within N turns of our planets), reduce the garrison buffer to `production × 1` to free up ships for attack.

**Predicted effect**: Average dispatch size in turns 20–40 increases from ~15 to ~25–35 ships. Planet count gap narrows in turns 30–50. Risk: if an enemy fleet is already en route and we've drained our garrison, we lose a planet. Condition: only reduce buffer when no incoming enemy fleet is detected.

---

## Next Step

**Top priority: Candidate A** — the divergence at median turn 8 is the most acute gap. A single extra neutral planet captured by turn 10 completely changes the production curve for the rest of the game. Run `/speckit-specify` with Candidate A to create the next improvement spec.

```
/speckit-specify Lower the early-game minimum fleet size for neutral captures: dispatch toward the nearest neutral planet immediately (turns 0-15) even with a small fleet, rather than waiting to accumulate a large garrison.
```
