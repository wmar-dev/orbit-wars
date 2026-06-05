# Opponent Agents

Downloaded from Kaggle Orbit Wars competition discussions/notebooks.

| File | Author | Description | vs agent_v56 (20 games) |
| --- | --- | --- | --- |
| `sigmaborov_agent.py` | sigmaborov | Tactical heuristic — orbit-lead, comet prediction, waypoint sun avoidance | 100% W (20-0-0) |
| `dylanxue04_agent.py` | dylanxue04 | Stellar Nexus v5 — crash exploit, let-them-fight, blood-in-water, total war endgame | 100% W (20-0-0) |
| `yusufmurtaza_agent.py` | yusufmurtaza01 | Physics-complete v8 — arrival ledger, timeline simulator, multi-source swarm missions | 100% W (20-0-0) |
| **`slawekbiel_agent.py`** | **slawekbiel** | **Producer — PyTorch tensor planner, garrison timeline sim, multi-source wave coordination, regroup** | **0% W (0-0-20) — beats us** |
| `rahulchauhan016_agent.py` | rahulchauhan016 | Target score 2000+ (multi-cell notebook, not directly importable) | notebook only |
| `melccoro_agent.py` | melccoro | Ablation study notebook — 12 agent variants (not a single submission agent) | notebook only |
| `adilshamim8_agent.py` | adilshamim8 | Orbit Wars 101 intro notebook | notebook only |
| `hoangson1506_agent.py` | Hoangson1506 | Simple nearest-planet attacker (GitHub) | not runnable (PyTorch RL class) |

## Quick eval

```bash
# From repo root — test agent_v56 vs each opponent (20 games each)
python eval_opponents.py
```
