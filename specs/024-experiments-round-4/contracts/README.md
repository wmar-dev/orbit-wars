# Contracts: Experiments Round 4

**Date**: 2026-06-06 | **Plan**: [plan.md](../plan.md)

## Interface Summary

The agent has one external contract — the `agent(obs)` function expected by the `kaggle-environments` game engine. This is an internal project (single-file agent), not a library or service, so no API/endpoint contracts exist.

## Agent Function Contract

```python
def agent(obs: dict) -> list[list[int | float]]:
    """Entry point called by kaggle-environments each turn.

    Args:
        obs: Game observation dictionary with keys:
            - player (int): Our player ID
            - planets (list): [id, owner, x, y, radius, ships, production]
            - fleets (list): [id, owner, x, y, angle, from_planet_id, ships]
            - initial_planets (list): Starting positions for orbit lead
            - angular_velocity (float): Planet rotation speed
            - step (int): Current turn number

    Returns:
        list of [from_planet_id, angle_radians, num_ships] moves.
        May be empty if no planets to dispatch from or no valid targets.
    """
```

## Invariant (contractual guarantee)

The agent file:
1. MUST NOT import modules outside Python stdlib + `kaggle_environments`
2. MUST complete within the `actTimeout` budget (1 second/turn, but safe target <800ms)
3. MUST NOT have side effects beyond returning the move list
4. MUST handle both `dict` and object-style observation access (Kaggle version compatibility)
