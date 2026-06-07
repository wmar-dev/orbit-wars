"""
Orbit Wars - Unified Evaluation Harness

Subcommands:
  h2h        Head-to-head 2-player evaluation
  4p         4-player evaluation (agent vs 3 opponents)
  opponents  Sweep against known opponent agents

Usage:
  uv run python eval.py h2h [--agent0 PATH] [--agent1 PATH] [--games N] [--jobs N] [--swap] [--verbose] [--reward-log PATH]
  uv run python eval.py 4p  [--agent PATH] [--opponent PATH|random] [--games N] [--jobs N] [--reward-log PATH]
  uv run python eval.py opponents [--agent PATH] [--opponent SLUG] [--games N]
"""

import argparse
import json
import math
import multiprocessing
import statistics
import sys
import time
import importlib.util

from kaggle_environments import make
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet


KNOWN_OPPONENTS = [
    ("sigmaborov",      "opponent_agents/sigmaborov_agent.py"),
    ("dylanxue04",      "opponent_agents/dylanxue04_agent.py"),
    ("yusufmurtaza",    "opponent_agents/yusufmurtaza_agent.py"),
    ("slawekbiel",      "opponent_agents/slawekbiel_agent.py"),
    ("adilshamim8",     "opponent_agents/adilshamim8_agent.py"),
    ("melccoro",        "opponent_agents/melccoro_agent.py"),
    ("rahulchauhan016", "opponent_agents/rahulchauhan016_agent.py"),
]


def load_agent(path):
    if path in ("random", "do_nothing"):
        return path
    module_name = path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod  # Python 3.14: needed for dataclass __module__ resolution
    spec.loader.exec_module(mod)
    return mod.agent


def _make_obs_collector(inner_agent, obs_list):
    def wrapped(obs):
        obs_list.append(obs if isinstance(obs, dict) else {
            "planets": obs.planets,
            "fleets": obs.fleets,
            "player": obs.player,
            "step": obs.step,
        })
        return inner_agent(obs)
    return wrapped


def _make_verbose_wrapper(inner_agent, label, move_log):
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


def _make_timing_wrapper(inner_agent, timings):
    def wrapped(obs):
        t0 = time.perf_counter()
        moves = inner_agent(obs)
        elapsed = (time.perf_counter() - t0) * 1000
        timings.append(elapsed)
        return moves
    return wrapped


# ── h2h ──────────────────────────────────────────────────────────────────────

def _run_h2h_game(args):
    agent0_path, agent1_path, seed, swap, verbose, collect_rewards, collect_timing = args
    agent0_fn = load_agent(agent0_path)
    agent1_fn = load_agent(agent1_path)

    should_swap = swap and (seed % 2 == 1)
    p0_fn = agent1_fn if should_swap else agent0_fn
    p1_fn = agent0_fn if should_swap else agent1_fn

    move_log = []
    obs_lists = [[], []]
    timings_p0 = []
    timings_p1 = []

    if collect_timing:
        p0_fn = _make_timing_wrapper(p0_fn, timings_p0)
        p1_fn = _make_timing_wrapper(p1_fn, timings_p1)

    if collect_rewards:
        p0_fn = _make_obs_collector(p0_fn, obs_lists[0])
        p1_fn = _make_obs_collector(p1_fn, obs_lists[1])

    if verbose:
        p0_fn = _make_verbose_wrapper(p0_fn, "P0", move_log)
        p1_fn = _make_verbose_wrapper(p1_fn, "P1", move_log)

    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run([p0_fn, p1_fn])

    final = env.steps[-1]
    r0 = final[0].get("reward") or 0.0
    r1 = final[1].get("reward") or 0.0

    r_agent0 = r1 if should_swap else r0
    r_agent1 = r0 if should_swap else r1

    reward_records = []
    if collect_rewards:
        import reward_signal
        final_rewards = [r0, r1]
        num_turns = max(len(obs_lists[0]), len(obs_lists[1]))
        for turn in range(num_turns):
            for player in range(2):
                hist = obs_lists[player]
                if turn >= len(hist):
                    continue
                prev_obs = hist[turn - 1] if turn > 0 else None
                curr_obs = hist[turn]
                is_terminal = turn == len(hist) - 1
                rw = reward_signal.compute_reward(
                    prev_obs, curr_obs, player,
                    final_rewards=final_rewards if is_terminal else None,
                )
                rw["game_id"] = seed
                rw["seed"] = seed
                rw["step"] = turn
                rw["player"] = player
                reward_records.append(rw)

    return seed, r_agent0, r_agent1, move_log, reward_records, timings_p0, timings_p1


def cmd_h2h(args):
    wins = [0, 0]
    draws = 0
    all_timings = []
    game_args = [
        (args.agent0, args.agent1, s, args.swap, args.verbose, args.reward_log is not None, args.timing)
        for s in range(args.games)
    ]

    pool = None
    if args.jobs > 1:
        pool = multiprocessing.Pool(processes=min(args.jobs, args.games))
        results = pool.imap_unordered(_run_h2h_game, game_args)
    else:
        results = (_run_h2h_game(a) for a in game_args)

    pending = {}
    next_to_print = 0
    reward_file = open(args.reward_log, "w") if args.reward_log else None

    try:
        for seed, r0, r1, move_log, reward_records, t0_list, t1_list in results:
            pending[seed] = (r0, r1, move_log, reward_records, t0_list, t1_list)
            while next_to_print in pending:
                r0, r1, move_log, reward_records, t0_list, t1_list = pending.pop(next_to_print)
                game_num = next_to_print + 1
                if r0 > r1:
                    wins[0] += 1
                    outcome = "A0 wins"
                elif r1 > r0:
                    wins[1] += 1
                    outcome = "A1 wins"
                else:
                    draws += 1
                    outcome = "Draw"
                swap_tag = " [swapped]" if args.swap and next_to_print % 2 == 1 else ""
                print(f"Game {game_num} (seed={next_to_print}){swap_tag}: {outcome}  [A0: {r0}  A1: {r1}]")
                if args.verbose and move_log:
                    for line in move_log[:10]:
                        print(line)
                if reward_file and reward_records:
                    for rec in reward_records:
                        reward_file.write(json.dumps(rec) + "\n")
                    reward_file.flush()
                next_to_print += 1
                if args.timing:
                    all_timings.extend(t0_list)
                    all_timings.extend(t1_list)
    finally:
        if reward_file:
            reward_file.close()

    if pool is not None:
        pool.close()
        pool.join()

    if args.timing and all_timings:
        all_timings.sort()
        n_t = len(all_timings)
        p50 = all_timings[n_t // 2]
        p95 = all_timings[int(n_t * 0.95)]
        p99 = all_timings[int(n_t * 0.99)]
        print(f"Timing (ms)   p50={p50:.1f}  p95={p95:.1f}  p99={p99:.1f}  (samples={n_t})")

    n = args.games
    win_rate = wins[0] / n * 100
    score = (wins[0] + 0.5 * draws) / n * 100
    tag = "WIN" if score >= 60 else ("FAIL" if score <= 40 else "EVEN")
    side_note = "side-alternating" if args.swap else "fixed sides"

    print()
    print(f"--- Results ({n} games, {side_note}) ---")
    print(f"Agent0 ({args.agent0}): {wins[0]} wins")
    print(f"Agent1 ({args.agent1}): {wins[1]} wins")
    print(f"Draws:                 {draws}")
    print(f"Win rate (agent0):     {win_rate:.1f}%  (draws = loss)")
    print(f"Score    (agent0):     {score:.1f}%  (draws = 0.5)  [{tag}]")
    if args.reward_log:
        print(f"Reward log:            {args.reward_log}")


# ── 4p ───────────────────────────────────────────────────────────────────────

def _run_4p_game(args):
    agent_path, opponent_path, seed, collect_rewards = args
    agent_fn = load_agent(agent_path)
    opp_fn = load_agent(opponent_path)

    obs_lists = [[], [], [], []]
    if collect_rewards:
        players = [agent_fn, opp_fn, opp_fn, opp_fn]
        wrapped_players = [_make_obs_collector(players[i], obs_lists[i]) for i in range(4)]
    else:
        wrapped_players = [agent_fn, opp_fn, opp_fn, opp_fn]

    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run(wrapped_players)

    final = env.steps[-1]
    rewards = [s.get("reward") or 0.0 for s in final]
    agent_reward = rewards[0]
    rank = 1 + sum(1 for r in rewards[1:] if r > agent_reward)

    reward_records = []
    if collect_rewards:
        import reward_signal
        num_turns = max(len(obs_lists[p]) for p in range(4))
        for turn in range(num_turns):
            for player in range(4):
                hist = obs_lists[player]
                if turn >= len(hist):
                    continue
                prev_obs = hist[turn - 1] if turn > 0 else None
                curr_obs = hist[turn]
                is_terminal = turn == len(hist) - 1
                rw = reward_signal.compute_reward(
                    prev_obs, curr_obs, player,
                    final_rewards=rewards if is_terminal else None,
                    num_players=4,
                )
                rw["game_id"] = seed
                rw["seed"] = seed
                rw["step"] = turn
                rw["player"] = player
                reward_records.append(rw)

    return seed, rank, agent_reward, reward_records


def cmd_4p(args):
    ranks = []
    wins = 0
    game_args = [
        (args.agent, args.opponent, s, args.reward_log is not None)
        for s in range(args.games)
    ]

    pool = None
    if args.jobs > 1:
        pool = multiprocessing.Pool(processes=min(args.jobs, args.games))
        results = pool.imap_unordered(_run_4p_game, game_args)
    else:
        results = (_run_4p_game(a) for a in game_args)

    pending = {}
    next_to_print = 0
    reward_file = open(args.reward_log, "w") if args.reward_log else None

    try:
        for seed, rank, reward, reward_records in results:
            pending[seed] = (rank, reward, reward_records)
            while next_to_print in pending:
                rank, reward, reward_records = pending.pop(next_to_print)
                game_num = next_to_print + 1
                ranks.append(rank)
                if rank == 1:
                    wins += 1
                print(f"Game {game_num} (seed={next_to_print}): rank={rank}  [reward={reward}]")
                if reward_file and reward_records:
                    for rec in reward_records:
                        reward_file.write(json.dumps(rec) + "\n")
                    reward_file.flush()
                next_to_print += 1
    finally:
        if reward_file:
            reward_file.close()

    if pool is not None:
        pool.close()
        pool.join()

    n = args.games
    avg_rank = sum(ranks) / len(ranks) if ranks else 0.0
    win_rate = wins / n * 100

    print()
    print(f"--- Results ({n} games, 4-player) ---")
    print(f"Agent ({args.agent}) vs 3x {args.opponent}")
    print(f"Wins (rank 1):  {wins}")
    print(f"Win rate:       {win_rate:.1f}%")
    print(f"Average rank:   {avg_rank:.2f}  (1=best, 4=worst; random baseline ~2.5)")
    if args.reward_log:
        print(f"Reward log:     {args.reward_log}")


# ── opponents ─────────────────────────────────────────────────────────────────

def _play_vs_opponent(our_agent_fn, opp_fn, n_games):
    wins = draws = losses = 0
    for i in range(n_games):
        env = make("orbit_wars", configuration={"seed": i}, debug=False)
        if i % 2 == 1:
            result = env.run([opp_fn, our_agent_fn])
            our_idx = 1
        else:
            result = env.run([our_agent_fn, opp_fn])
            our_idx = 0
        final = result[-1]
        rewards = [s["reward"] for s in final]
        our_r = rewards[our_idx]
        opp_r = rewards[1 - our_idx]
        if our_r > opp_r:
            wins += 1
        elif our_r == opp_r:
            draws += 1
        else:
            losses += 1
    return wins, draws, losses


def cmd_opponents(args):
    our_agent_fn = load_agent(args.agent)
    opponents = KNOWN_OPPONENTS
    if args.opponent:
        opponents = [(n, p) for n, p in KNOWN_OPPONENTS if n == args.opponent]
        if not opponents:
            known = [n for n, _ in KNOWN_OPPONENTS]
            print(f"Unknown opponent '{args.opponent}'. Known: {known}")
            sys.exit(1)

    print(f"Agent: {args.agent}  ({args.games} games each, side-alternating)")
    print()
    print(f"{'Opponent':<20} {'W':>4} {'D':>4} {'L':>4}  {'Win%':>6}  {'Tag'}")
    print("-" * 52)
    for name, path in opponents:
        try:
            opp = load_agent(path)
            w, d, l = _play_vs_opponent(our_agent_fn, opp, args.games)
            total = w + d + l
            pct = 100 * w / total if total else 0
            tag = "WIN" if pct >= 60 else ("FAIL" if pct <= 40 else "EVEN")
            print(f"{name:<20} {w:>4} {d:>4} {l:>4}  {pct:>5.1f}%   {tag}")
        except Exception as e:
            print(f"{name:<20} ERROR: {e}")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Orbit Wars - Unified Evaluation Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_h2h = sub.add_parser("h2h", help="Head-to-head 2-player evaluation")
    p_h2h.add_argument("--agent0", default="agent_v59.py")
    p_h2h.add_argument("--agent1", default="main.py")
    p_h2h.add_argument("--games", type=int, default=10)
    p_h2h.add_argument("--jobs", type=int, default=1, help="Parallel worker processes")
    p_h2h.add_argument("--swap", action="store_true", help="Alternate sides on odd games (removes positional bias)")
    p_h2h.add_argument("--verbose", action="store_true", help="Print per-turn move details")
    p_h2h.add_argument("--reward-log", metavar="PATH", default=None, help="Write per-turn rewards to .jsonl")
    p_h2h.add_argument("--timing", action="store_true", help="Report per-turn timing p50/p95/p99")

    p_4p = sub.add_parser("4p", help="4-player evaluation (agent vs 3 opponents)")
    p_4p.add_argument("--agent", default="agent_v59.py")
    p_4p.add_argument("--opponent", default="random", help="Opponent path or 'random' (slots 1-3)")
    p_4p.add_argument("--games", type=int, default=20)
    p_4p.add_argument("--jobs", type=int, default=1, help="Parallel worker processes")
    p_4p.add_argument("--reward-log", metavar="PATH", default=None, help="Write per-turn rewards to .jsonl")

    p_opp = sub.add_parser("opponents", help="Sweep against known opponent agents")
    p_opp.add_argument("--agent", default="agent_v59.py")
    p_opp.add_argument("--opponent", default=None, metavar="SLUG", help="Run only this opponent slug")
    p_opp.add_argument("--games", type=int, default=20)

    args = parser.parse_args()
    {"h2h": cmd_h2h, "4p": cmd_4p, "opponents": cmd_opponents}[args.cmd](args)


if __name__ == "__main__":
    main()
