"""
Orbit Wars - 4-Player Evaluation Harness

Tests a single agent in slot 0 against three identical opponents (slots 1-3).
Reports per-game rank (1=best, 4=worst) and aggregate average rank and win rate.

Usage:
    uv run python eval4.py [--games N] [--agent PATH] [--opponent PATH|random] [--jobs N]
    uv run python eval4.py ... [--reward-log PATH]  # write per-turn rewards to .jsonl
"""

import argparse
import importlib.util
import json
import multiprocessing

from kaggle_environments import make


def load_agent(path):
    if path in ("random", "do_nothing"):
        return path
    spec = importlib.util.spec_from_file_location("agent_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def _make_obs_collector(inner_agent, obs_list):
    """Wraps an agent to capture per-turn observations for reward logging."""
    def wrapped(obs):
        obs_list.append(obs if isinstance(obs, dict) else {
            "planets": obs.planets,
            "fleets": obs.fleets,
            "player": obs.player,
            "step": obs.step,
        })
        return inner_agent(obs)
    return wrapped


def _run_game(args):
    """Run a single 4-player game. Agent under test occupies slot 0."""
    agent_path, opponent_path, seed, collect_rewards = args
    agent_fn = load_agent(agent_path)
    opp_fn = load_agent(opponent_path)

    obs_lists = [[], [], [], []]
    if collect_rewards:
        players = [agent_fn, opp_fn, opp_fn, opp_fn]
        # opp_fn is shared — wrap separate collectors per slot
        wrapped_players = [_make_obs_collector(players[i], obs_lists[i]) for i in range(4)]
    else:
        wrapped_players = [agent_fn, opp_fn, opp_fn, opp_fn]

    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run(wrapped_players)

    final = env.steps[-1]
    rewards = [s.get("reward") or 0.0 for s in final]

    # Rank: 1 = winner; ties share the better rank.
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


def run_evaluation(agent_path, opponent_path, num_games, jobs, reward_log_path=None):
    ranks = []
    wins = 0
    collect_rewards = reward_log_path is not None
    game_args = [(agent_path, opponent_path, s, collect_rewards) for s in range(num_games)]

    pool = None
    if jobs > 1:
        pool = multiprocessing.Pool(processes=min(jobs, num_games))
        results = pool.imap_unordered(_run_game, game_args)
    else:
        results = (_run_game(a) for a in game_args)

    pending = {}
    next_to_print = 0
    reward_file = open(reward_log_path, "w") if reward_log_path else None

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

    avg_rank = sum(ranks) / len(ranks) if ranks else 0.0
    win_rate = wins / num_games * 100

    print()
    print(f"--- Results ({num_games} games, 4-player) ---")
    print(f"Agent ({agent_path}) vs 3x {opponent_path}")
    print(f"Wins (rank 1):  {wins}")
    print(f"Win rate:       {win_rate:.1f}%")
    print(f"Average rank:   {avg_rank:.2f}  (1=best, 4=worst; random baseline ~2.5)")
    if reward_log_path:
        print(f"Reward log written to: {reward_log_path}")


def main():
    parser = argparse.ArgumentParser(description="Orbit Wars 4-player evaluator")
    parser.add_argument("--games", type=int, default=20, help="Number of games to play")
    parser.add_argument("--agent", default="agent_v20.py", help="Agent under test (slot 0)")
    parser.add_argument("--opponent", default="random", help="Opponent path or 'random' (slots 1-3)")
    parser.add_argument("--jobs", type=int, default=1, help="Parallel worker processes")
    parser.add_argument(
        "--reward-log", metavar="PATH", default=None,
        help="Write per-turn, per-player rewards to a .jsonl file (4 rows per turn)",
    )
    args = parser.parse_args()

    run_evaluation(args.agent, args.opponent, args.games, args.jobs, args.reward_log)


if __name__ == "__main__":
    main()
