# 4-Player Baseline Diagnosis

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Purpose

Establish 4-player baselines for agent_v8 and agent_v20 to diagnose the leaderboard regression
(v8 is current leaderboard best; v15 submitted and regressed; nothing after v15 submitted).

## Results

| Agent | Wins (rank 1) | Win rate | Avg rank | Games |
|-------|--------------|----------|----------|-------|
| agent_v8 vs 3× random | 18 | 90% | 1.10 | 20 |
| agent_v20 vs 3× random | 20 | 100% | 1.00 | 20 |

## Analysis

Agent_v20 is **stronger** than agent_v8 against random opponents in 4-player (100% vs 90%). This means the leaderboard regression is NOT caused by a 4-player weakness against random-level opponents.

The leaderboard regression from v8 → v15 must be explained by performance against stronger (non-random) opponents. Possible explanations:
- **Hypothesis A** (single-sender conservatism): Single-sender coordination reduces aggression. Against weak opponents this is fine; against skilled opponents who pressure from multiple angles, single-sender can't respond.
- **Hypothesis B** (safety guard over-filtering): Less likely — both v8 and v20 dominate random opponents, so safety guards don't appear to block valid moves against simple opponents.
- **Hypothesis C** (ROI formula mismatch): Against random, any reasonable scoring wins. Against skilled opponents, the ROI formula may under-value certain strategic captures.

## Conclusion

4-player mechanics are not the primary lever to improve leaderboard performance. The regression is most likely related to behavior against skilled (non-random) opponents, not 4-player dynamics per se. Continue optimizing 2-player performance as the primary path to leaderboard improvement.
