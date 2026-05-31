"""
T009: DQN with prioritized experience replay for Orbit Wars — MLX backend.

Uses factored Q-heads (independent heads per action dimension) with action masking,
prioritized replay (PER), and a target network.

Usage:
    uv run python rl/dqn.py --episodes 1000 --opponent random
    uv run python rl/dqn.py --episodes 5000 --opponent agent_v38.py --resume
"""

import argparse
import csv
import random
import sys
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from rl.env import OrbitWarsEnv
from rl.obs import MAX_PLANETS, OBS_SIZE
from rl.ppo import get_opponent, _latest_checkpoint, save_checkpoint, load_checkpoint, _clip_grads, _save_torch_compat

# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------
HIDDEN         = 256
LR             = 1e-4
GAMMA          = 0.99
BUFFER_SIZE    = 10_000
BATCH_SIZE     = 64
TARGET_UPDATE  = 200
EPS_START      = 1.0
EPS_END        = 0.05
EPS_DECAY      = 500
PER_ALPHA      = 0.6
PER_BETA_START = 0.4
PER_BETA_END   = 1.0
MAX_GRAD       = 10.0
CHECKPOINT_EVERY = 200


# ---------------------------------------------------------------------------
# Q-Network (MLX, factored heads)
# ---------------------------------------------------------------------------
class QNet(nn.Module):
    def __init__(self, obs_size=OBS_SIZE, hidden=HIDDEN):
        super().__init__()
        self.fc1    = nn.Linear(obs_size, hidden)
        self.fc2    = nn.Linear(hidden,   hidden)
        self.q_src  = nn.Linear(hidden, MAX_PLANETS)
        self.q_tgt  = nn.Linear(hidden, MAX_PLANETS)
        self.q_frac = nn.Linear(hidden, 5)

    def __call__(self, x, src_mask=None, tgt_mask=None):
        h = nn.relu(self.fc1(x))
        h = nn.relu(self.fc2(h))
        q_src  = self.q_src(h)
        q_tgt  = self.q_tgt(h)
        q_frac = self.q_frac(h)
        if src_mask is not None:
            q_src = mx.where(src_mask, q_src, mx.full(q_src.shape, -1e9))
        if tgt_mask is not None:
            q_tgt = mx.where(tgt_mask, q_tgt, mx.full(q_tgt.shape, -1e9))
        return q_src, q_tgt, q_frac

    def select_action(self, x, mask):
        src_mask = mask[:, :12] > 0.5
        tgt_mask = mask[:, 12:24] > 0.5
        src_mask = mx.logical_or(src_mask, mx.logical_not(src_mask.any(axis=1, keepdims=True)))
        tgt_mask = mx.logical_or(tgt_mask, mx.logical_not(tgt_mask.any(axis=1, keepdims=True)))
        q_src, q_tgt, q_frac = self(x, src_mask, tgt_mask)
        return mx.argmax(q_src, axis=1), mx.argmax(q_tgt, axis=1), mx.argmax(q_frac, axis=1)


# ---------------------------------------------------------------------------
# Prioritized Replay Buffer (numpy — CPU side)
# ---------------------------------------------------------------------------
class PrioritizedReplay:
    def __init__(self, capacity, alpha=PER_ALPHA):
        self.capacity  = capacity
        self.alpha     = alpha
        self.buffer    = []
        self.priorities= np.zeros(capacity, dtype=np.float32)
        self.pos       = 0

    def add(self, transition, priority=1.0):
        if len(self.buffer) < self.capacity:
            self.buffer.append(transition)
        else:
            self.buffer[self.pos] = transition
        self.priorities[self.pos] = max(priority, 1e-6) ** self.alpha
        self.pos = (self.pos + 1) % self.capacity

    def sample(self, batch_size, beta=0.4):
        n     = len(self.buffer)
        probs = self.priorities[:n]
        probs = probs / probs.sum()
        indices = np.random.choice(n, batch_size, replace=False, p=probs)
        samples = [self.buffer[i] for i in indices]
        weights = (n * probs[indices]) ** (-beta)
        weights = weights / weights.max()
        return samples, indices, weights.astype(np.float32)

    def update_priorities(self, indices, td_errors):
        for i, td in zip(indices, td_errors):
            self.priorities[i] = (abs(td) + 1e-6) ** self.alpha

    def __len__(self):
        return len(self.buffer)


def dqn_loss_fn(net, obs_b, act_b, rew_b, nobs_b, done_b, target_net, nmask_b, weights_b):
    src_mask = obs_b[:, 267:267+12] > 0.5
    tgt_mask = obs_b[:, 267+12:267+24] > 0.5
    src_mask = mx.logical_or(src_mask, mx.logical_not(src_mask.any(axis=1, keepdims=True)))
    tgt_mask = mx.logical_or(tgt_mask, mx.logical_not(tgt_mask.any(axis=1, keepdims=True)))

    q_src, q_tgt, q_frac = net(obs_b, src_mask, tgt_mask)

    def _gather(q, a):
        B = q.shape[0]
        return q[mx.arange(B), a.astype(mx.int32)]

    cur_q = (_gather(q_src,  act_b[:, 0])
           + _gather(q_tgt,  act_b[:, 1])
           + _gather(q_frac, act_b[:, 2])) / 3.0

    # Target (no gradient)
    ns, nt, nf = target_net.select_action(nobs_b, nmask_b)
    tq_src, tq_tgt, tq_frac = target_net(nobs_b)
    next_q = (_gather(tq_src,  ns)
            + _gather(tq_tgt,  nt)
            + _gather(tq_frac, nf)) / 3.0
    target_q = rew_b + GAMMA * next_q * (1.0 - done_b)

    td = cur_q - mx.stop_gradient(target_q)
    loss = (weights_b * td * td).mean()
    return loss, td


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
def train(args):
    ckpt_dir = Path(args.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    log_dir  = Path(__file__).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "dqn_train.csv"

    net        = QNet()
    target_net = QNet()
    # Copy initial weights to target
    mx.eval(net.parameters())
    target_net.load_weights(list(_flatten_params(net.parameters())))
    mx.eval(target_net.parameters())

    optimizer     = optim.Adam(learning_rate=LR)
    loss_and_grad = nn.value_and_grad(net, dqn_loss_fn)
    replay        = PrioritizedReplay(BUFFER_SIZE)

    start_episode = 0
    if args.resume:
        latest = _latest_checkpoint(ckpt_dir, "dqn")
        if latest:
            start_episode, _ = load_checkpoint(net, latest)
            target_net.load_weights(list(_flatten_params(net.parameters())))
            print(f"Resumed from {latest} (episode {start_episode})")

    csv_exists = log_path.exists()
    csv_file   = open(log_path, "a", newline="")
    writer     = csv.writer(csv_file)
    if not csv_exists:
        writer.writerow(["episode", "ep_reward", "ep_steps", "elapsed_s", "opponent", "epsilon"])

    episode     = start_episode
    global_step = 0
    opponent    = get_opponent(episode, args.opponent, ckpt_dir)
    env         = OrbitWarsEnv(opponent=opponent, seed=args.seed)
    obs, _      = env.reset()
    ep_reward   = 0.0
    ep_steps    = 0
    ep_start    = time.time()

    def epsilon(ep):
        t = min((ep - start_episode) / EPS_DECAY, 1.0)
        return EPS_START + t * (EPS_END - EPS_START)

    def beta(ep):
        t = min((ep - start_episode) / args.episodes, 1.0)
        return PER_BETA_START + t * (PER_BETA_END - PER_BETA_START)

    print(f"Starting DQN training (MLX GPU): {args.episodes} episodes")

    while episode < start_episode + args.episodes:
        eps = epsilon(episode)

        obs_mx  = mx.array(obs[None], dtype=mx.float32)
        mask_mx = mx.array(obs[267:319][None], dtype=mx.float32)

        if random.random() < eps:
            action_np = np.array([random.randrange(MAX_PLANETS),
                                   random.randrange(MAX_PLANETS),
                                   random.randrange(5)])
        else:
            s, t, f = net.select_action(obs_mx, mask_mx)
            mx.eval(s, t, f)
            action_np = np.array([int(s[0]), int(t[0]), int(f[0])])

        next_obs, reward, done, _, _ = env.step(action_np)
        replay.add((obs, action_np, reward, next_obs, float(done)))
        ep_reward += reward
        ep_steps  += 1
        obs = next_obs
        global_step += 1

        # Sync target network
        if global_step % TARGET_UPDATE == 0:
            target_net.load_weights(list(_flatten_params(net.parameters())))
            mx.eval(target_net.parameters())

        # Train step
        if len(replay) >= BATCH_SIZE:
            b = beta(episode)
            samples, indices, weights = replay.sample(BATCH_SIZE, beta=b)
            obs_b, act_b, rew_b, nobs_b, done_b = zip(*samples)

            obs_mx_b   = mx.array(np.array(obs_b,   dtype=np.float32))
            act_mx_b   = mx.array(np.array(act_b,   dtype=np.int32))
            rew_mx_b   = mx.array(np.array(rew_b,   dtype=np.float32))
            nobs_mx_b  = mx.array(np.array(nobs_b,  dtype=np.float32))
            done_mx_b  = mx.array(np.array(done_b,  dtype=np.float32))
            nmask_mx_b = nobs_mx_b[:, 267:319]
            w_mx_b     = mx.array(weights)

            (loss, td_mx), grads = loss_and_grad(
                net, obs_mx_b, act_mx_b, rew_mx_b,
                nobs_mx_b, done_mx_b, target_net, nmask_mx_b, w_mx_b
            )
            grads = _clip_grads(grads, MAX_GRAD)
            optimizer.update(net, grads)
            mx.eval(net.parameters(), optimizer.state, loss)

            td_np = np.array(td_mx)
            replay.update_priorities(indices, td_np)

        if done:
            elapsed = time.time() - ep_start
            writer.writerow([episode, f"{ep_reward:.4f}", ep_steps,
                              f"{elapsed:.1f}", opponent, f"{eps:.3f}"])
            csv_file.flush()
            if episode % 50 == 0:
                print(f"ep={episode:5d} reward={ep_reward:+.3f} "
                      f"steps={ep_steps} eps={eps:.3f} opp={opponent[:20]}")
            episode += 1
            ep_reward = 0.0; ep_steps = 0; ep_start = time.time()

            if episode % CHECKPOINT_EVERY == 0:
                ckpt_path = ckpt_dir / f"dqn_ep{episode:05d}.npz"
                save_checkpoint(net, episode, None, ckpt_path)
                all_ckpts = sorted(ckpt_dir.glob("dqn_ep*.npz"),
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

    final_path = ckpt_dir / f"dqn_ep{episode:05d}.npz"
    save_checkpoint(net, episode, None, final_path)
    import shutil
    shutil.copy(final_path, ckpt_dir / "dqn_best.npz")
    _save_torch_compat(net, ckpt_dir / f"dqn_ep{episode:05d}.pt", episode)
    shutil.copy(ckpt_dir / f"dqn_ep{episode:05d}.pt", ckpt_dir / "dqn_best.pt")
    print(f"Training complete. Final checkpoint: {final_path}")
    csv_file.close()
    env.close()


def _flatten_params(params, prefix=""):
    result = []
    for k, v in params.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.extend(_flatten_params(v, key))
        elif isinstance(v, mx.array):
            result.append((key, v))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes",       type=int, default=1000)
    parser.add_argument("--opponent",       type=str, default="random")
    parser.add_argument("--checkpoint-dir", type=str, default="rl/checkpoints")
    parser.add_argument("--seed",           type=int, default=0)
    parser.add_argument("--resume",         action="store_true")
    args = parser.parse_args()
    train(args)
