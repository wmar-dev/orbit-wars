"""
Orbit Wars - Head-to-Head Evaluation Harness

Runs N games between two agent files and prints per-game results
and an aggregate win rate to stdout.

Usage:
    uv run python eval.py [--games N] [--agent0 PATH] [--agent1 PATH] [--verbose] [--jobs N]
"""

import argparse
import importlib.util
import math
import multiprocessing

from kaggle_environments import make
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet


def load_agent(path):
    spec = importlib.util.spec_from_file_location("agent_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def make_verbose_wrapper(inner_agent, label, move_log):
    """Wraps an agent to log its moves each turn for --verbose output."""
    turn = [0]

    def wrapped(obs):
        moves = inner_agent(obs)
        turn[0] += 1
        player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
        raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
        planets = {Planet(*p).id: Planet(*p) for p in raw_planets}

        for move in moves:
            from_id, angle, ships = move
            source = planets.get(from_id)
            if source is None:
                continue
            # Find the planet this fleet is heading toward (closest in that direction).
            best_target = None
            best_align = -1.0
            for pid, p in planets.items():
                if p.owner == player:
                    continue
                dx = p.x - source.x
                dy = p.y - source.y
                dist = math.hypot(dx, dy)
                if dist < 0.1:
                    continue
                # Dot product with unit fleet vector gives alignment score.
                align = (dx * math.cos(angle) + dy * math.sin(angle)) / dist
                if align > best_align:
                    best_align = align
                    best_target = p

            if best_target is not None:
                prod_score = best_target.production / (
                    math.hypot(best_target.x - source.x, best_target.y - source.y) + 1e-6
                )
                move_log.append(
                    f"  [{label}] Turn {turn[0]:3d} | "
                    f"Planet {from_id} → Planet {best_target.id} "
                    f"(prod={best_target.production}, "
                    f"dist={math.hypot(best_target.x-source.x, best_target.y-source.y):.1f}, "
                    f"score={prod_score:.3f}, ships={ships})"
                )
        return moves

    return wrapped


def _run_game(args):
    """Run a single game in a worker process. Must be module-level for pickling."""
    agent0_path, agent1_path, seed, verbose = args
    agent0_fn = load_agent(agent0_path)
    agent1_fn = load_agent(agent1_path)
    move_log = []

    if verbose:
        a0 = make_verbose_wrapper(agent0_fn, "P0", move_log)
        a1 = make_verbose_wrapper(agent1_fn, "P1", move_log)
    else:
        a0, a1 = agent0_fn, agent1_fn

    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run([a0, a1])

    final = env.steps[-1]
    r0 = final[0].get("reward") or 0.0
    r1 = final[1].get("reward") or 0.0
    return seed, r0, r1, move_log


def run_evaluation(agent0_path, agent1_path, num_games, verbose, jobs):
    wins = [0, 0]
    draws = 0
    game_args = [(agent0_path, agent1_path, s, verbose) for s in range(num_games)]

    pool = None
    if jobs > 1:
        pool = multiprocessing.Pool(processes=min(jobs, num_games))
        results = pool.imap_unordered(_run_game, game_args)
    else:
        results = (_run_game(a) for a in game_args)

    pending = {}
    next_to_print = 0

    for seed, r0, r1, move_log in results:
        pending[seed] = (r0, r1, move_log)
        while next_to_print in pending:
            r0, r1, move_log = pending.pop(next_to_print)
            game_num = next_to_print + 1
            if r0 > r1:
                wins[0] += 1
                result = "Player 0 wins"
            elif r1 > r0:
                wins[1] += 1
                result = "Player 1 wins"
            else:
                draws += 1
                result = "Draw"
            print(f"Game {game_num} (seed={next_to_print}): {result}  [P0: {r0}  P1: {r1}]")
            if verbose and move_log:
                p0_moves = [m for m in move_log if "[P0]" in m][:5]
                p1_moves = [m for m in move_log if "[P1]" in m][:5]
                for line in p0_moves + p1_moves:
                    print(line)
            next_to_print += 1

    if pool is not None:
        pool.close()
        pool.join()

    print()
    print(f"--- Results ({num_games} games) ---")
    print(f"Agent 0 ({agent0_path}): {wins[0]} wins")
    print(f"Agent 1 ({agent1_path}): {wins[1]} wins")
    print(f"Draws:                 {draws}")
    win_rate = wins[0] / num_games * 100
    print(f"Win rate (agent 0):    {win_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Orbit Wars head-to-head evaluator")
    parser.add_argument("--games", type=int, default=10, help="Number of games to play")
    parser.add_argument("--agent0", default="agent_v2.py", help="Path to agent under test")
    parser.add_argument("--agent1", default="main.py", help="Path to baseline agent")
    parser.add_argument("--verbose", action="store_true", help="Print per-turn move details")
    parser.add_argument("--jobs", type=int, default=1, help="Parallel worker processes (default: 1)")
    args = parser.parse_args()

    run_evaluation(args.agent0, args.agent1, args.games, args.verbose, args.jobs)


if __name__ == "__main__":
    main()
