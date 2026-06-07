# Replay Analysis: agent_v66 vs agent_v64 — 2026-06-07

**Replays analyzed**: 1 game (seed=42)
**Win rate**: 0% (loss by turn 157)
**Divergence turn**: ~30 (opponent reaches 1.5× our ships)

## Behavioral Differences Observed

1. **Planet control gap**: We average 1.7 planets in turns 0–50; v64 averages 4.3. By turns 50–100, we drop to 1.4 while v64 surges to 17.7. We lose all planets by turn 100.

2. **Dispatch throughput**: We dispatch 0.92 fleets/turn (144 total over 157 turns) with 72/157 turns doing nothing. v64 dispatches an estimated 5–10 fleets/turn based on visible in-flight fleet counts (avg 37.8 fleets in turns 50–100 vs our 25.6 in-flight — though our fleeting is largely random).

3. **Fleet size**: 117/144 dispatches send only 1–3 ships. We never commit significant force to any target. v64's fleet sizes are unknown but their total ship count of 5630 by turn 157 vs our 1 suggests each dispatch is substantially larger.

4. **Expansion**: v64 captures all neutral planets by turn ~80. We never capture a single planet from v64 (all our captures are from neutral planets early on).

## What Happens at the Divergence Turn

By turn 30, v64 already has 1.5× our total ships. The gap widens monotonically: v64 captures every neutral planet first, uses the production advantage to out-fleet us, and rolls up our planets one by one. Our policy never mounts a counter-attack because it never accumulates enough ships on any single planet to send a meaningful force.

## Candidate Improvements

### Candidate A: Increase dispatch throughput
**Observation**: We dispatch 0.92 fleets/turn with 46% idle turns. v64 dispatches 5–10× more.
**Hypothesis**: The action mask filters out most of our 5 fleet slots because no planet has enough surplus. With PPO's untrained initialization, the policy can't accumulate surplus because it sends ships immediately at random targets.
**Predicted effect**: With proper exploration, the policy would learn to conserve ships on a few planets and send large fleets. This requires either (a) behavioral cloning from v64 to bootstrap, or (b) a curriculum starting vs random where small dispatches actually succeed.
**Risk**: Larger networks still won't learn without a useful gradient.

### Candidate B: Terminal-only reward
**Observation**: The blended reward (capture + production + ship delta) gives tiny signals per turn. PPO's advantage normalization may not help when 99% of episodes end in loss.
**Hypothesis**: Removing per-turn reward and using only terminal win/loss would force the policy to optimize for the only signal that matters.
**Predicted effect**: Slower learning initially but potentially more focused gradient.
**Risk**: Sparse reward could prevent any learning at all.

### Candidate C: Curriculum learning (start vs random, then v64)
**Observation**: The policy never experiences winning states against v64, so PPO has no positive examples to reinforce.
**Hypothesis**: Training vs random until >80% win rate, then vs v38, then v64 would expose the policy to progressively stronger opponents, creating a useful learning gradient.
**Predicted effect**: The policy would learn basic strategies (accumulate ships, capture neutrals) in easier environments and refine them against stronger opponents.
**Risk**: Longer total training time. May still plateau against v64.

## Next Step

Recommend Candidate C (curriculum) as the most promising: fix the reward to be terminal-only AND train with a curriculum. This addresses the fundamental issue of never seeing winning states.
