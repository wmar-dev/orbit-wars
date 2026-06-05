"""Head-to-head eval: agent_a vs agent_b, isolated load, side-alternating."""
import argparse
import importlib.util
import sys
from kaggle_environments import make


def load_agent(path):
    module_name = path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod.agent


def play_games(a, b, n_games, label_a, label_b):
    wins_a = draws = wins_b = 0
    for i in range(n_games):
        env = make("orbit_wars")  # fresh env each game for different seeds
        if i % 2 == 1:
            result = env.run([b, a])
            a_idx = 1
        else:
            result = env.run([a, b])
            a_idx = 0
        r = [s["reward"] for s in result[-1]]
        if r[a_idx] > r[1 - a_idx]:
            wins_a += 1
        elif r[a_idx] == r[1 - a_idx]:
            draws += 1
        else:
            wins_b += 1
    pct = 100 * wins_a / n_games
    tag = "WIN" if pct >= 60 else ("FAIL" if pct <= 40 else "EVEN")
    print(f"{label_a} vs {label_b}: {wins_a}W {draws}D {wins_b}L  ({pct:.0f}%)  [{tag}]")
    return wins_a, draws, wins_b


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_a")
    parser.add_argument("agent_b")
    parser.add_argument("--games", type=int, default=20)
    args = parser.parse_args()

    a = load_agent(args.agent_a)
    b = load_agent(args.agent_b)
    play_games(a, b, args.games, args.agent_a, args.agent_b)


if __name__ == "__main__":
    main()
