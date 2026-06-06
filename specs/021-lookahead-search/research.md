# Research: Agent Lookahead Decision Search

**Date**: 2026-06-05 | **Branch**: `021-lookahead-search`

## Decision 1: Root cause of v59_beam underperformance

**Decision**: Redesign candidate generation to vary *target assignments*, not just hold/dispatch masks.

**Rationale**: `agent_v59_beam.py` generates candidates as subsets of greedy dispatches (greedy, greedy-minus-one-mine, hold-all). The search never tests whether a mine should attack a different target — only whether it should hold back. This is a much weaker question than true lookahead. The simulation returns greedy or a lazier version of greedy, not genuinely better play.

**Alternatives considered**:
- Keep v59_beam candidate generation, tune depth/breadth: rejected because the candidate space is fundamentally too narrow (hold-or-dispatch binary mask)
- Full target enumeration cross-product: rejected because exponential in number of mines (impractical for M>3)

---

## Decision 2: Candidate generation strategy for beam search

**Decision**: Linear candidate set — vary one mine's target at a time. Generate M × (K-1) + 2 candidates total (M mines, K alternatives per mine, plus hold-all and greedy-all).

**Rationale**: With 5 mines and K=3, this produces 5 × 2 + 2 = 12 candidates. Each is simulated SEARCH_DEPTH turns forward. The linear fan-out is fast, fully time-bounded, and explores the most impactful individual decisions (which mine targets what) without combinatorial explosion.

**Alternatives considered**:
- Two-mine variation: 5^2 × 2^2 = 100 candidates — feasible but adds overhead; could be added as a tuning option
- Random sampling from cross-product: this is essentially MCTS without UCB1; added as a separate strategy

---

## Decision 3: MCTS implementation approach

**Decision**: Lightweight dict-based tree with UCB1 selection; rollout uses simplified greedy (each mine dispatches to nearest non-owned planet with surplus).

**Rationale**: Full `agent_v58` greedy is expensive during rollout (~0.3ms/turn including orbit-lead). The simplified greedy (nearest-planet, surplus check only) runs in ~0.03ms/turn — 10x faster — and is accurate enough for rollout scoring. UCB1 constant C=sqrt(2) is the standard theoretical value for zero-sum games and a reasonable starting point.

**Alternatives considered**:
- Full greedy rollout: too slow, limits MCTS to <50 iterations within budget
- Pure random rollout: high variance, requires many more iterations to converge; revisit if simplified greedy shows instability

---

## Decision 4: N-ply exhaustive pruning strategy

**Decision**: Beam pruning — at each ply level, enumerate top-2 targets per mine, then keep only the top-NPLY_BEAM_WIDTH (8) branches by intermediate score before expanding the next level.

**Rationale**: With beam pruning width=8 and depth=3, worst case is 8 branches × 2^M candidates per level → ~512 simulations total (fast). Without pruning, 2^(M×D) = 2^15 = 32,768 simulations at depth=3 with M=5 (too slow). Beam width=8 is a conservative starting value; can be tuned up if timing allows.

**Alternatives considered**:
- Alpha-beta: not applicable here since both players move simultaneously each turn, not alternately
- Minimax with opponent model: would require modeling opponent moves at each depth level, doubling branching factor; deferred to future experiment

---

## Decision 5: In-transit ship weighting

**Decision**: `TRANSIT_WEIGHT = 0.1` (initial). Ships in transit count as 10% of their face value toward the score.

**Rationale**: A fleet of 50 ships in transit for 20 turns will arrive and capture a planet worth ~3 production. The production advantage gained is 3/turn going forward. So 50 ships ≈ 60 production-turns of future value at a discount. TRANSIT_WEIGHT=0.1 weights 50 ships as 5 production-equivalent — a conservative estimate. This is a tunable parameter; the depth study will reveal sensitivity.

**Alternatives considered**:
- TRANSIT_WEIGHT=0: pure production score (current v59_beam behavior); produces optimistic scores when large fleets are in transit
- TRANSIT_WEIGHT=1.0: ships and production treated equally; overcounts ships since they are one-time gains not recurring production
- Arrival-discounted weighting (ships × eta / max_eta): more accurate but adds computation; revisit if TRANSIT_WEIGHT tuning is insufficient

---

## Decision 6: Opponent modeling during rollout

**Decision**: Start with no-opponent model (opponent planets accumulate production, no opponent dispatches). Compare against simplified-greedy opponent model as a separate tuning experiment (User Story 3).

**Rationale**: No-opponent model is the fastest and simplest baseline. It's optimistic (we gain planets unchallenged) but provides a clean signal for algorithm comparison. If beam vs MCTS vs N-ply rankings are consistent under no-opponent, the opponent model choice is secondary. If rankings flip, opponent modeling matters and the greedy model should be enabled.

**Alternatives considered**:
- Full `agent_v58` greedy as opponent model: too slow during rollout (adds ~0.3ms per rollout step per opponent mine)
- Simplified greedy: nearest planet, surplus-only — adds ~0.03ms overhead; acceptable; will be compared in User Story 3

---

## NEEDS CLARIFICATION: None

All ambiguities from the spec clarification session have been resolved through design decisions above.
