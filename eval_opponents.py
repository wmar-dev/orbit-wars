"""Evaluate agent_v56 against downloaded opponent agents."""
import importlib.util
import sys
import argparse
from kaggle_environments import make
import agent_v56 as our_module

OUR_AGENT = our_module.agent

OPPONENTS = [
    ("sigmaborov", "opponent_agents/sigmaborov_agent.py"),
    ("dylanxue04", "opponent_agents/dylanxue04_agent.py"),
    ("yusufmurtaza", "opponent_agents/yusufmurtaza_agent.py"),
    ("slawekbiel", "opponent_agents/slawekbiel_agent.py"),
    # hoangson1506 is a PyTorch RL class, not a submission-format agent — skip
    # ("hoangson1506", "opponent_agents/hoangson1506_agent.py"),
]


def load_agent(path):
    module_name = path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses can resolve cls.__module__ (Python 3.14 fix)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod.agent


def play_games(our_agent, opp_agent, n_games, swap=True):
    wins = draws = losses = 0
    env = make("orbit_wars")
    for i in range(n_games):
        # Alternate sides to remove positional bias
        if swap and i % 2 == 1:
            result = env.run([opp_agent, our_agent])
            our_idx = 1
        else:
            result = env.run([our_agent, opp_agent])
            our_idx = 0

        final = result[-1]
        rewards = [s["reward"] for s in final]
        our_reward = rewards[our_idx]
        opp_reward = rewards[1 - our_idx]

        if our_reward > opp_reward:
            wins += 1
        elif our_reward == opp_reward:
            draws += 1
        else:
            losses += 1

    return wins, draws, losses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--games", type=int, default=20)
    parser.add_argument("--opponent", default=None, help="Run only this opponent slug")
    args = parser.parse_args()

    opponents = OPPONENTS
    if args.opponent:
        opponents = [(n, p) for n, p in OPPONENTS if n == args.opponent]
        if not opponents:
            print(f"Unknown opponent: {args.opponent}")
            sys.exit(1)

    print(f"{'Opponent':<20} {'W':>4} {'D':>4} {'L':>4}  {'Win%':>6}")
    print("-" * 44)
    for name, path in opponents:
        try:
            opp = load_agent(path)
            w, d, l = play_games(OUR_AGENT, opp, args.games)
            total = w + d + l
            pct = 100 * w / total if total else 0
            print(f"{name:<20} {w:>4} {d:>4} {l:>4}  {pct:>5.1f}%")
        except Exception as e:
            print(f"{name:<20} ERROR: {e}")


if __name__ == "__main__":
    main()
