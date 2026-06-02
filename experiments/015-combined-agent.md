# Experiment 015: Combined Agent — Round 015 Results

**Date**: 2026-06-01
**Base agent**: agent_v47.py
**New best agent**: agent_v50.py

---

## Round 015 Individual Candidate Results

| Candidate | File | Win rate vs v47 | Result |
|---|---|---|---|
| C1: ROI scoring mismatch fix | agent_v48.py | 54% (27W/23L) | FAIL (< 56%) |
| C2: Endgame ROI normalization | agent_v49.py | 48% (24W/26L) | FAIL |
| **C3: Garrison defense buffer** | **agent_v50.py** | **62% (31W/19L)** | **PASS** |
| C4: Sender pre-screening | agent_v51.py | 16% (8W/42L) | FAIL — severe regression |
| C5: Friendly fleet sufficiency | agent_v52.py | 44% (22W/28L) | FAIL |
| C6: Persistent campaign target | agent_v53.py | 28% (14W/36L) | FAIL — severe regression |

Only **C3** passed the 56% threshold.

---

## Combination Attempt: C3 + C1 (agent_v54)

C1 was marginal at 54% and directionally positive; tested in combination with C3.

| Eval | Win Rate | Record |
|---|---|---|
| agent_v54 vs agent_v47 | 58% | 29W/21L |

Result: 58% — below C3 alone (62%). C1 weakens C3 marginally. C3-only promoted.

---

## Final Evaluation: agent_v50 (C3 only)

| Eval | Win Rate | Record | SC target |
|---|---|---|---|
| vs agent_v47 | 62% | 31W/19L | ≥ 56% ✅ |
| vs agent_v38 | 76% | 38W/12L | ≥ 72% ✅ |

---

## Conclusion

**Winner: agent_v50.py — 62% vs agent_v47, 76% vs agent_v38.**

C3 (garrison defense buffer) is the sole passing candidate. The fix is minimal (3 lines) but high impact: when the threat floor equals the inbound enemy fleet exactly, the planet exits the battle at 0 ships and is immediately recaptured. Adding `production × 2` as a buffer prevents this vulnerability and gives the planet a meaningful recovery window.

**Failed candidates post-mortems**:
- C4 (sender pre-screening) and C6 (campaign target) caused severe regressions by interfering with the single-sender coordination mechanism. These require architectural changes, not bolt-on additions.
- C5 (fleet sufficiency) has the same geometry false-positive problem as round 014's race-filtering experiment (v44): fleet angle alignment is not target-specific.
- C2 (endgame normalization) and C1 (ROI mismatch) show no significant signal at 50 games; may retest in combination in a future round.
