# Candidate L Retest — 009-fix-comet-fleet-targeting

**Date**: 2026-05-30

## Hypothesis

Candidate L (two-source coordinated attack, 40% score vs v20 — FAIL) adds a two-source
fallback when the highest-ROI skipped target can be jointly afforded by two planets. With
v32's better baseline (more ships captured via accurate targeting), there might be more
surplus available for joint attacks.

## Change vs agent_v32

After the main single-sender offense loop, added a two-source fallback: collect targets
where no single source could afford the capture, find the best-ROI among them, check if
top-2 surplus sources can jointly afford it, and if so send `ceil(needed/2)` from each.

## Self-Play Result (50 games, agent0=cand_L, agent1=agent_v32)

- Agent0 wins: 10
- Agent1 wins: 40
- Draws: 0
- Win rate: **20.0%** (draws count as losses)
- Score: **20.0%** (draws count as 0.5)
- Mean reward delta (cand_L - v32): **-0.0750**

## Conclusion

**FAIL** — 20% score and -0.0750 reward delta. The result is worse than prior (40% vs v20).
Root cause: The two-source fallback fires even when both sources were already the best senders
for individually affordable targets. Locking two sources onto one target in the same turn
abandons two other potential captures. The reward delta of -0.0750 confirms this — the agent
loses ships through inefficient joint allocation. This mechanic will NOT be included in agent_v33.
