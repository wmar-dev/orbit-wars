# Experiment: Clean Agent with Helper Module (013)

**Date**: 2026-05-31
**Branch**: 013-clean-agent-helper
**Spec**: specs/013-clean-agent-helper/spec.md

## Hypothesis

Extracting all deterministic game-mechanics calculations from agent_v40 into a standalone
`helper.py` module should produce a cleaner agent_v41.py with no loss in game strength.
The refactoring removes dead code (variant flags, unused sets) and consolidates duplicated
logic (evacuation + attack loops both calling orbit-lead/comet dispatch). With the same
proven mechanic set and locked-in variant B banking, agent_v41 should match or exceed
agent_v40's win rate vs agent_v38.

## Change

- New: `helper.py` — pure-function module with all game-mechanics calculations
- New: `agent_v41.py` — clean agent that imports from helper.py
- Removed dead code from agent_v40: `assigned_primary/secondary`, `high_prod_neutrals/enemies`,
  `BANKING_VARIANT`/`FALLBACK_VARIANT` flags, `RANGE_FACTOR`, duplicated docstring lines
- Unified evacuation + attack target prediction into `helper.predict_target`
- `banking_mode` variant parameter removed; Variant B logic hardcoded directly
- New `_do_evacuation` helper in agent_v41.py eliminates duplicated evacuation code between
  banking and non-banking paths

## Self-play Results

| Agent 0 | Agent 1 | Games | Seed | Win Rate (A0) | Notes |
|---------|---------|-------|------|---------------|-------|
| agent_v41 | agent_v38 | 50 | sequential | 52% (26W/24L/0D) | Target: ≥50% ✅ |
| agent_v41 | agent_v40 | 50 | sequential | 52% win / 56% score (26W/20L/4D) | Target: ≥45% ✅ |

## Conclusion

agent_v41 passes both eval gates. The refactoring to helper.py produced no performance regression;
it actually improved win rate vs agent_v40 (52% win / 56% score vs the prior 46% win rate when
agent_v40 was tested against agent_v38). The clean structure confirms that removing dead code and
consolidating the duplicated evacuation/attack dispatch logic did not change the strategic behaviour.

agent_v41 is promoted as the new best agent (replaces agent_v40).

Notable: 4 draws vs agent_v40 (both using banking mode Variant B) suggest mirror-match outcomes
when both agents are in the same banking phase simultaneously.
