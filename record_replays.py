"""Record games between our agent and an opponent, saving full per-turn replays to disk."""
import argparse
import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# T004: Agent recording shim
# ---------------------------------------------------------------------------

def _make_recording_shim(agent_fn, player_idx, move_log):
    """Wrap an agent callable to record its moves each turn without affecting gameplay."""
    def shim(obs, *args, **kwargs):
        moves = agent_fn(obs, *args, **kwargs) or []
        turn = obs["step"] if isinstance(obs, dict) else obs.step
        dispatches = [
            {"source_planet_id": int(m[0]), "angle": float(m[1]), "ships": float(m[2])}
            for m in (moves or [])
        ]
        move_log.append((int(turn), int(player_idx), dispatches))
        return moves
    return shim


# ---------------------------------------------------------------------------
# T005: Planet/ship count helpers
# ---------------------------------------------------------------------------

def _compute_planet_counts(planets_raw, n_players):
    """Return [count_player0, count_player1, ...] from raw planets list."""
    counts = [0] * n_players
    for p in planets_raw:
        owner = p[1]  # field index 1 = owner (-1 = neutral, 0/1 = player)
        if 0 <= owner < n_players:
            counts[owner] += 1
    return counts


def _compute_ship_totals(planets_raw, fleets_raw, n_players):
    """Return total ships (planets + in-flight fleets) per player."""
    totals = [0.0] * n_players
    for p in planets_raw:
        owner = p[1]
        if 0 <= owner < n_players:
            totals[owner] += p[5]  # field index 5 = ships
    for f in fleets_raw:
        owner = f[1]  # field index 1 = owner
        if 0 <= owner < n_players:
            totals[owner] += f[5]  # field index 5 = ships
    return [round(t, 2) for t in totals]


# ---------------------------------------------------------------------------
# T006: Divergence turn computation
# ---------------------------------------------------------------------------

def _compute_divergence_turn(turn_records):
    """Return first turn index where one player has 2× advantage in planets or ships."""
    for rec in turn_records:
        pc = rec["planet_counts"]
        sc = rec["ship_totals"]
        for a, b in [(pc[0], pc[1]), (pc[1], pc[0]), (sc[0], sc[1]), (sc[1], sc[0])]:
            if b == 0 and a > 0:
                return rec["turn"]
            if b > 0 and a / b >= 2.0:
                return rec["turn"]
    return None


# ---------------------------------------------------------------------------
# T007: Replay serializer
# ---------------------------------------------------------------------------

def _serialize_replay(agents, opponent_file, outcome, turn_records):
    """Build a full Replay dict matching the v1.0 schema."""
    return {
        "version": "1.0",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agents": list(agents),
        "opponent_file": opponent_file,
        "outcome": outcome,
        "turns": turn_records,
    }


# ---------------------------------------------------------------------------
# T008: Save replay to disk
# ---------------------------------------------------------------------------

_SESSION_TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _save_replay(replay_dict, out_dir, opponent_slug, game_idx):
    """Write replay JSON to {out_dir}/replay_{opponent_slug}_{ts}_{idx:03d}.json."""
    os.makedirs(out_dir, exist_ok=True)
    fname = f"replay_{opponent_slug}_{_SESSION_TS}_{game_idx:03d}.json"
    fpath = os.path.join(out_dir, fname)
    with open(fpath, "w") as f:
        json.dump(replay_dict, f, separators=(",", ":"))
    return fpath


# ---------------------------------------------------------------------------
# T009/T022: Agent loader (importlib + sys.modules fix for PyTorch agents)
# ---------------------------------------------------------------------------

def _load_agent(path):
    module_name = path.replace("/", "_").replace(".", "_").replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod  # register before exec (Python 3.14 dataclasses fix)
    spec.loader.exec_module(mod)
    return mod.agent


# ---------------------------------------------------------------------------
# T009–T013: Main game-recording loop
# ---------------------------------------------------------------------------

def record_games(our_agent_path, opponent_path, n_games, out_dir):
    from kaggle_environments import make

    our_agent_fn = _load_agent(our_agent_path)
    opp_agent_fn = _load_agent(opponent_path)

    our_name = os.path.splitext(os.path.basename(our_agent_path))[0]
    opp_name = os.path.splitext(os.path.basename(opponent_path))[0]
    print(f"Our agent : {our_name}")
    print(f"Opponent  : {opp_name}")
    print(f"Games     : {n_games}")
    print(f"Output    : {out_dir}/")
    print()

    opponent_slug = opp_name

    for game_idx in range(n_games):
        move_log = []

        # T013: alternate sides each game
        our_player = 0 if game_idx % 2 == 0 else 1
        opp_player = 1 - our_player

        shim_our = _make_recording_shim(our_agent_fn, our_player, move_log)
        shim_opp = _make_recording_shim(opp_agent_fn, opp_player, move_log)

        if our_player == 0:
            agents_list = [shim_our, shim_opp]
            agent_names = [our_name, opp_name]
        else:
            agents_list = [shim_opp, shim_our]
            agent_names = [opp_name, our_name]

        env = make("orbit_wars")
        turn_records = []
        error_msg = None

        try:
            result = env.run(agents_list)
        except Exception as e:
            error_msg = str(e)
            result = env.steps  # partial steps if available

        # T010: extract TurnRecord from each step
        # Build move lookup: {(turn, player_idx): [dispatches]}
        move_lookup = {}
        for (turn, pidx, dispatches) in move_log:
            move_lookup[(turn, pidx)] = dispatches

        for step in result:
            obs = step[0]["observation"]
            turn_num = int(obs["step"])
            planets_raw = obs.get("planets", [])
            fleets_raw = obs.get("fleets", [])

            planets = [
                {
                    "id": int(p[0]),
                    "owner": None if p[1] == -1 else int(p[1]),
                    "x": float(p[2]),
                    "y": float(p[3]),
                    "radius": float(p[4]),
                    "ships": float(p[5]),
                    "production": float(p[6]) if len(p) > 6 else 0.0,
                }
                for p in planets_raw
            ]
            fleets = [
                {
                    "id": int(f[0]),
                    "owner": int(f[1]),
                    "x": float(f[2]),
                    "y": float(f[3]),
                    "angle": float(f[4]),
                    "ships": float(f[5]),
                    "eta": int(f[6]),
                }
                for f in fleets_raw
            ]

            moves = [
                {"player": p, "dispatches": move_lookup.get((turn_num, p), [])}
                for p in range(2)
            ]

            planet_counts = _compute_planet_counts(planets_raw, 2)
            ship_totals = _compute_ship_totals(planets_raw, fleets_raw, 2)

            turn_records.append({
                "turn": turn_num,
                "planets": planets,
                "fleets": fleets,
                "moves": moves,
                "planet_counts": planet_counts,
                "ship_totals": ship_totals,
            })

        # T011: compute Outcome
        final_step = result[-1]
        rewards = [s["reward"] for s in final_step]
        if rewards[0] > rewards[1]:
            winner_abs = 0  # absolute player index in this game
        elif rewards[1] > rewards[0]:
            winner_abs = 1
        else:
            winner_abs = None

        # Convert absolute player index → our_player/opp_player perspective
        if winner_abs is None:
            winner_relative = None
        elif winner_abs == our_player:
            winner_relative = 0  # 0 = our agent won
        else:
            winner_relative = 1  # 1 = opponent won

        final_obs = final_step[0]["observation"]
        final_planets_raw = final_obs.get("planets", [])
        final_fleets_raw = final_obs.get("fleets", [])
        final_planet_counts = _compute_planet_counts(final_planets_raw, 2)
        final_ship_totals = _compute_ship_totals(final_planets_raw, final_fleets_raw, 2)

        # Reorder final counts/totals to our/opp perspective
        our_final_planets = final_planet_counts[our_player]
        opp_final_planets = final_planet_counts[opp_player]
        our_final_ships = final_ship_totals[our_player]
        opp_final_ships = final_ship_totals[opp_player]

        total_dispatches_abs = [0, 0]
        for rec in turn_records:
            for mv in rec["moves"]:
                total_dispatches_abs[mv["player"]] += len(mv["dispatches"])

        our_dispatches = total_dispatches_abs[our_player]
        opp_dispatches = total_dispatches_abs[opp_player]

        divergence_turn = _compute_divergence_turn(turn_records)
        end_turn = turn_records[-1]["turn"] if turn_records else 0

        outcome = {
            "winner": winner_relative,
            "end_turn": end_turn,
            "final_planets": [our_final_planets, opp_final_planets],
            "final_ships": [our_final_ships, opp_final_ships],
            "divergence_turn": divergence_turn,
            "total_dispatches": [our_dispatches, opp_dispatches],
        }
        if error_msg:
            outcome["error"] = error_msg

        replay = _serialize_replay(
            agents=[our_name, opp_name],
            opponent_file=opponent_path,
            outcome=outcome,
            turn_records=turn_records,
        )
        fpath = _save_replay(replay, out_dir, opponent_slug, game_idx)

        w = "WIN " if winner_relative == 0 else ("LOSS" if winner_relative == 1 else "DRAW")
        print(f"  Game {game_idx+1:>3}/{n_games}: {w}  divergence={divergence_turn}  end={end_turn}  → {os.path.basename(fpath)}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Record Orbit Wars games as replay JSON files.")
    parser.add_argument("--opponent", required=True, help="Path to opponent agent .py file")
    parser.add_argument("--games", type=int, default=20, help="Number of games to record (default: 20)")
    parser.add_argument("--out-dir", default="replays", help="Directory to write replay files (default: replays/)")
    parser.add_argument("--our-agent", default="agent_v56.py", help="Path to our agent file (default: agent_v56.py)")
    args = parser.parse_args()

    record_games(
        our_agent_path=args.our_agent,
        opponent_path=args.opponent,
        n_games=args.games,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
