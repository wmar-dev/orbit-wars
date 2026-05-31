"""
T008: A2C (Advantage Actor-Critic) training for Orbit Wars — MLX backend.

Same architecture as PPO (rl/ppo.py) but plain policy gradient loss (no clipping).
Ablation to measure contribution of PPO clipping.

Usage:
    uv run python rl/a2c.py --episodes 1000 --opponent random
    uv run python rl/a2c.py --episodes 5000 --opponent agent_v38.py --resume
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from rl.env import OrbitWarsEnv
from rl.obs import OBS_SIZE
from rl.ppo import (PolicyNet, RolloutBuffer, get_opponent, _latest_checkpoint,
                     get_action_and_value, save_checkpoint, load_checkpoint,
                     _clip_grads, _save_torch_compat)

HIDDEN           = 256
GAMMA            = 0.99
LAM              = 0.95
ENT_COEF         = 0.01
VF_COEF          = 0.5
LR               = 3e-4
MAX_GRAD         = 0.5
ROLLOUT_STEPS    = 512
CHECKPOINT_EVERY = 200


def a2c_loss_fn(net, obs_b, act_b, logp_b, adv_b, ret_b, mask_b):
    _, new_lp, entropy, new_val = get_action_and_value(net, obs_b, mask_b, actions=act_b)
    pg_loss  = -(new_lp * adv_b).mean()
    vf_loss  = ((new_val - ret_b) ** 2).mean()
    ent_loss = -entropy.mean()
    loss = pg_loss + VF_COEF * vf_loss + ENT_COEF * ent_loss
    return loss, (pg_loss, vf_loss, ent_loss)


def train(args):
    ckpt_dir = Path(args.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    log_dir  = Path(__file__).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "a2c_train.csv"

    net       = PolicyNet()
    mx.eval(net.parameters())
    optimizer = optim.Adam(learning_rate=LR)
    loss_and_grad = nn.value_and_grad(net, a2c_loss_fn)

    start_episode = 0
    if args.resume:
        latest = _latest_checkpoint(ckpt_dir, "a2c")
        if latest:
            start_episode, _ = load_checkpoint(net, latest)
            print(f"Resumed from {latest} (episode {start_episode})")

    csv_exists = log_path.exists()
    csv_file   = open(log_path, "a", newline="")
    writer     = csv.writer(csv_file)
    if not csv_exists:
        writer.writerow(["episode", "ep_reward", "ep_steps", "elapsed_s", "opponent"])

    buf      = RolloutBuffer(ROLLOUT_STEPS, OBS_SIZE)
    episode  = start_episode
    opponent = get_opponent(episode, args.opponent, ckpt_dir)
    env      = OrbitWarsEnv(opponent=opponent, seed=args.seed)
    obs, _   = env.reset()
    ep_reward = 0.0
    ep_steps  = 0
    ep_start  = time.time()

    print(f"Starting A2C training (MLX GPU): {args.episodes} episodes")

    while episode < start_episode + args.episodes:
        buf.reset()
        for _ in range(ROLLOUT_STEPS):
            obs_mx  = mx.array(obs[None], dtype=mx.float32)
            mask_mx = mx.array(obs[267:319][None], dtype=mx.float32)
            act_mx, lp_mx, _, val_mx = get_action_and_value(net, obs_mx, mask_mx)
            mx.eval(act_mx, lp_mx, val_mx)
            action_np = np.array(act_mx[0])
            next_obs, reward, done, _, _ = env.step(action_np)
            buf.add(obs, action_np, float(lp_mx[0]), reward, float(done), float(val_mx[0]))
            ep_reward += reward
            ep_steps  += 1
            obs = next_obs
            if done:
                elapsed = time.time() - ep_start
                writer.writerow([episode, f"{ep_reward:.4f}", ep_steps,
                                  f"{elapsed:.1f}", opponent])
                csv_file.flush()
                if episode % 50 == 0:
                    print(f"ep={episode:5d} reward={ep_reward:+.3f} "
                          f"steps={ep_steps} t={elapsed:.1f}s opp={opponent[:25]}")
                episode += 1
                ep_reward = 0.0; ep_steps = 0; ep_start = time.time()
                if episode % CHECKPOINT_EVERY == 0:
                    ckpt_path = ckpt_dir / f"a2c_ep{episode:05d}.npz"
                    save_checkpoint(net, episode, None, ckpt_path)
                    all_ckpts = sorted(ckpt_dir.glob("a2c_ep*.npz"),
                                       key=lambda p: int(p.stem.split("ep")[1]))
                    for old in all_ckpts[:-5]:
                        old.unlink(missing_ok=True)
                    print(f"  Checkpoint saved: {ckpt_path}")
                new_opp = get_opponent(episode, args.opponent, ckpt_dir)
                if new_opp != opponent:
                    opponent = new_opp
                    env.close()
                    env = OrbitWarsEnv(opponent=opponent)
                    print(f"  Opponent updated: {opponent[:30]}")
                obs, _ = env.reset()
                if episode >= start_episode + args.episodes:
                    break

        if episode >= start_episode + args.episodes:
            break

        obs_mx  = mx.array(obs[None], dtype=mx.float32)
        mask_mx = mx.array(obs[267:319][None], dtype=mx.float32)
        _, _, _, last_val_mx = get_action_and_value(net, obs_mx, mask_mx)
        mx.eval(last_val_mx)
        advantages, returns = buf.compute_gae(float(last_val_mx[0]))

        obs_b  = mx.array(buf.obs[:buf.ptr])
        act_b  = mx.array(buf.actions[:buf.ptr], dtype=mx.int32)
        logp_b = mx.array(buf.log_probs[:buf.ptr])
        adv_b  = mx.array(advantages)
        ret_b  = mx.array(returns)
        mask_b = obs_b[:, 267:319]
        adv_b  = (adv_b - adv_b.mean()) / (adv_b.std() + 1e-8)
        mx.eval(adv_b)

        n = buf.ptr
        idx = np.random.permutation(n)
        for start in range(0, n, BATCH_SIZE := 64):
            mb = mx.array(idx[start:start + BATCH_SIZE])
            (loss, _), grads = loss_and_grad(
                net, obs_b[mb], act_b[mb], logp_b[mb],
                adv_b[mb], ret_b[mb], mask_b[mb]
            )
            grads = _clip_grads(grads, MAX_GRAD)
            optimizer.update(net, grads)
            mx.eval(net.parameters(), optimizer.state, loss)

    final_path = ckpt_dir / f"a2c_ep{episode:05d}.npz"
    save_checkpoint(net, episode, None, final_path)
    import shutil
    shutil.copy(final_path, ckpt_dir / "a2c_best.npz")
    _save_torch_compat(net, ckpt_dir / f"a2c_ep{episode:05d}.pt", episode)
    shutil.copy(ckpt_dir / f"a2c_ep{episode:05d}.pt", ckpt_dir / "a2c_best.pt")
    print(f"Training complete. Final checkpoint: {final_path}")
    csv_file.close()
    env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes",       type=int, default=1000)
    parser.add_argument("--opponent",       type=str, default="random")
    parser.add_argument("--checkpoint-dir", type=str, default="rl/checkpoints")
    parser.add_argument("--seed",           type=int, default=0)
    parser.add_argument("--resume",         action="store_true")
    args = parser.parse_args()
    train(args)
