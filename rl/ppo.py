"""
PPO training for Orbit Wars — full observation, multi-fleet action.
MLX backend (Apple Silicon GPU).

Architecture:
  Shared MLP (2 × 256 ReLU) → 5×(40+40+4) actor heads + value head
  5 independent fleet slots per turn, each: source, target, ship fraction
"""

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from rl.env import OrbitWarsEnv
from rl.obs import MAX_PLANETS, OBS_SIZE, NUM_FLEETS_PER_TURN, NUM_ACTION_VALUES

HIDDEN     = 256
GAMMA      = 0.99
LAM        = 0.95
CLIP_EPS   = 0.2
ENT_COEF   = 0.01
VF_COEF    = 0.5
LR         = 3e-4
BATCH_SIZE = 64
EPOCHS     = 4
MAX_GRAD   = 0.5
ROLLOUT_STEPS    = 512
CHECKPOINT_EVERY = 200
EVAL_FREQ  = 200
EVAL_GAMES = 50

CURRICULUM_STAGES = [
    ("random", 0.8, 500),
    ("agent_v38.py", 0.6, 1000),
    ("agent_v64.py", 0.0, 5000),
]

class PolicyNet(nn.Module):
    def __init__(self, obs_size=OBS_SIZE, hidden=HIDDEN):
        super().__init__()
        self.fc1 = nn.Linear(obs_size, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.critic = nn.Linear(hidden, 1)
        for i in range(NUM_FLEETS_PER_TURN):
            setattr(self, f"actor_src_{i}",  nn.Linear(hidden, MAX_PLANETS))
            setattr(self, f"actor_tgt_{i}",  nn.Linear(hidden, MAX_PLANETS))
            setattr(self, f"actor_frac_{i}", nn.Linear(hidden, 4))

    def __call__(self, x, src_mask=None, tgt_mask=None):
        h = nn.relu(self.fc1(x))
        h = nn.relu(self.fc2(h))
        src_logits  = []
        tgt_logits  = []
        frac_logits = []
        for i in range(NUM_FLEETS_PER_TURN):
            s = getattr(self, f"actor_src_{i}")(h)
            t = getattr(self, f"actor_tgt_{i}")(h)
            f = getattr(self, f"actor_frac_{i}")(h)
            if src_mask is not None:
                s = mx.where(src_mask, s, mx.full(s.shape, -1e9))
            if tgt_mask is not None:
                t = mx.where(tgt_mask, t, mx.full(t.shape, -1e9))
            src_logits.append(s)
            tgt_logits.append(t)
            frac_logits.append(f)
        value = self.critic(h).squeeze(-1)
        return src_logits, tgt_logits, frac_logits, value


def _sample_categorical(logits):
    gumbel = -mx.log(-mx.log(mx.random.uniform(shape=logits.shape) + 1e-10) + 1e-10)
    return mx.argmax(logits + gumbel, axis=-1)


def _log_prob_categorical(logits, actions):
    log_probs = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
    return log_probs[mx.arange(log_probs.shape[0]), actions.astype(mx.int32)]


def _entropy_categorical(logits):
    log_probs = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
    probs = mx.exp(log_probs)
    return -(probs * log_probs).sum(axis=-1)


def get_action_and_value(net, obs, mask, actions=None):
    """
    obs:    (B, obs_size)
    mask:   (B, 80)  — first 40 = src valid, next 40 = tgt valid
    actions: (B, 15) or None  — 5 fleet slots × 3 values
    Returns: actions (B,15), log_prob (B,), entropy (B,), value (B,)
    """
    src_mask_bool = mask[:, :40] > 0.5
    tgt_mask_bool = mask[:, 40:80] > 0.5

    any_src = src_mask_bool.any(axis=1, keepdims=True)
    any_tgt = tgt_mask_bool.any(axis=1, keepdims=True)
    src_mask_bool = mx.logical_or(src_mask_bool, mx.logical_not(any_src))
    tgt_mask_bool = mx.logical_or(tgt_mask_bool, mx.logical_not(any_tgt))

    src_logits_list, tgt_logits_list, frac_logits_list, value = net(obs, src_mask_bool, tgt_mask_bool)

    total_lp = 0.0
    total_ent = 0.0
    act_parts = []

    for i in range(NUM_FLEETS_PER_TURN):
        sl = src_logits_list[i]
        tl = tgt_logits_list[i]
        fl = frac_logits_list[i]

        if actions is None:
            src_a  = _sample_categorical(sl)
            tgt_a  = _sample_categorical(tl)
            frac_a = _sample_categorical(fl)
        else:
            src_a  = actions[:, i * 3]
            tgt_a  = actions[:, i * 3 + 1]
            frac_a = actions[:, i * 3 + 2]

        total_lp += (_log_prob_categorical(sl, src_a)
                     + _log_prob_categorical(tl, tgt_a)
                     + _log_prob_categorical(fl, frac_a))
        total_ent += (_entropy_categorical(sl)
                      + _entropy_categorical(tl)
                      + _entropy_categorical(fl))
        act_parts.extend([src_a, tgt_a, frac_a])

    act = mx.stack(act_parts, axis=1)
    return act, total_lp, total_ent, value


class RolloutBuffer:
    def __init__(self, steps, obs_size):
        self.obs       = np.zeros((steps, obs_size), dtype=np.float32)
        self.actions   = np.zeros((steps, NUM_ACTION_VALUES), dtype=np.int32)
        self.log_probs = np.zeros(steps, dtype=np.float32)
        self.rewards   = np.zeros(steps, dtype=np.float32)
        self.dones     = np.zeros(steps, dtype=np.float32)
        self.values    = np.zeros(steps, dtype=np.float32)
        self.ptr = 0

    def add(self, obs, action, log_prob, reward, done, value):
        self.obs[self.ptr]       = obs
        self.actions[self.ptr]   = action
        self.log_probs[self.ptr] = log_prob
        self.rewards[self.ptr]   = reward
        self.dones[self.ptr]     = done
        self.values[self.ptr]    = value
        self.ptr += 1

    def compute_gae(self, last_value):
        advantages = np.zeros_like(self.rewards)
        last_gae   = 0.0
        n = self.ptr
        for t in reversed(range(n)):
            next_val  = last_value if t == n - 1 else self.values[t + 1]
            delta     = self.rewards[t] + GAMMA * next_val * (1 - self.dones[t]) - self.values[t]
            last_gae  = delta + GAMMA * LAM * (1 - self.dones[t]) * last_gae
            advantages[t] = last_gae
        returns = advantages[:n] + self.values[:n]
        return advantages[:n], returns

    def reset(self):
        self.ptr = 0


class CurriculumTracker:
    def __init__(self, stages=None, no_curriculum=False, initial_episode=0,
                 fixed_opponent=None):
        self.stages = stages or CURRICULUM_STAGES
        self.no_curriculum = no_curriculum
        self.fixed_opponent = fixed_opponent
        self.stage_idx = 0
        self._stage_ep_start = initial_episode

    @property
    def opponent(self):
        if self.no_curriculum:
            return self.fixed_opponent or self.stages[-1][0]
        return self.stages[self.stage_idx][0]

    @property
    def min_episodes_for_stage(self):
        if self.no_curriculum:
            return 0
        return self.stages[self.stage_idx][2]

    @property
    def win_threshold(self):
        if self.no_curriculum:
            return 0.0
        return self.stages[self.stage_idx][1]

    @property
    def at_final_stage(self):
        return self.no_curriculum or self.stage_idx >= len(self.stages) - 1

    def episodes_in_stage(self, episode):
        return episode - self._stage_ep_start

    def advance_if_ready(self, episode, win_rate):
        if self.no_curriculum or self.at_final_stage:
            return False
        min_met = self.episodes_in_stage(episode) >= self.min_episodes_for_stage
        if win_rate >= self.win_threshold and min_met:
            self.stage_idx += 1
            self._stage_ep_start = episode
            return True
        return False


def run_eval(net, opponent, n_games=EVAL_GAMES):
    env = OrbitWarsEnv(opponent=opponent)
    wins = 0
    for _ in range(n_games):
        obs, _ = env.reset()
        done = False
        while not done:
            obs_mx = mx.array(obs[None], dtype=mx.float32)
            mask_mx = mx.array(obs[480:560][None], dtype=mx.float32)
            act_mx, _, _, _ = get_action_and_value(net, obs_mx, mask_mx)
            obs, r, done, _, _ = env.step(np.array(act_mx[0]))
        if r > 0:
            wins += 1
    env.close()
    return wins / n_games


def _latest_checkpoint(checkpoints_dir, prefix):
    d = Path(checkpoints_dir)
    cands = sorted(d.glob(f"{prefix}_ep*.npz"), key=lambda p: int(p.stem.split("ep")[1]))
    return cands[-1] if cands else None


def save_checkpoint(net, episode, score, path):
    flat = {}
    def _flatten(d, prefix=""):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                _flatten(v, key)
            elif isinstance(v, mx.array):
                flat[key] = np.array(v)
    _flatten(dict(net.parameters()))
    flat["__episode__"] = np.array([episode])
    flat["__score__"]   = np.array([score if score is not None else -1.0])
    np.savez(path, **flat)


def load_checkpoint(net, path):
    data = np.load(path, allow_pickle=False)
    episode = int(data["__episode__"][0])
    score   = float(data["__score__"][0])
    nested = {}
    for key in data.files:
        if key.startswith("__"):
            continue
        parts = key.split(".")
        d = nested
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = mx.array(data[key])
    net.load_weights(list(_flatten_to_list(nested)))
    return episode, score if score >= 0 else None


def _flatten_to_list(d, prefix=""):
    result = []
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.extend(_flatten_to_list(v, key))
        else:
            result.append((key, v))
    return result


def ppo_loss_fn(net, obs_b, act_b, logp_b, adv_b, ret_b, mask_b):
    _, new_lp, entropy, new_val = get_action_and_value(net, obs_b, mask_b, actions=act_b)
    ratio   = mx.exp(new_lp - logp_b)
    pg_loss = -mx.minimum(
        ratio * adv_b,
        mx.clip(ratio, 1 - CLIP_EPS, 1 + CLIP_EPS) * adv_b
    ).mean()
    vf_loss  = ((new_val - ret_b) ** 2).mean()
    ent_loss = -entropy.mean()
    loss = pg_loss + VF_COEF * vf_loss + ENT_COEF * ent_loss
    return loss, (pg_loss, vf_loss, ent_loss)


def train(args):
    ckpt_dir = Path(args.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log_file) if args.log_file else Path(__file__).parent / "logs" / "ppo_train.csv"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    net = PolicyNet()
    mx.eval(net.parameters())

    if args.bc_pretrain:
        ep, sc = load_checkpoint(net, args.bc_pretrain)
        best_score = sc or 0.0
        print(f"Loaded BC-pretrained weights from {args.bc_pretrain} (epoch {ep}, loss {best_score:.4f})")
    else:
        best_score = 0.0

    optimizer = optim.Adam(learning_rate=LR)
    loss_and_grad = nn.value_and_grad(net, ppo_loss_fn)

    start_episode = 0

    if args.resume:
        latest = _latest_checkpoint(ckpt_dir, "ppo")
        if latest:
            start_episode, sc = load_checkpoint(net, latest)
            best_score = sc or 0.0
            print(f"Resumed from {latest} (episode {start_episode})")

    csv_exists = log_path.exists()
    csv_file   = open(log_path, "a", newline="")
    writer     = csv.writer(csv_file)
    if not csv_exists:
        writer.writerow(["episode", "ep_reward", "ep_steps", "elapsed_s",
                          "opponent", "stage", "win_rate"])

    buf             = RolloutBuffer(ROLLOUT_STEPS, OBS_SIZE)
    episode         = start_episode
    curriculum      = CurriculumTracker(no_curriculum=args.no_curriculum,
                                        initial_episode=start_episode,
                                        fixed_opponent=args.opponent)
    opponent        = curriculum.opponent
    env             = OrbitWarsEnv(opponent=opponent, seed=args.seed)
    obs, _          = env.reset()
    ep_reward       = 0.0
    ep_steps        = 0
    ep_start        = time.time()
    last_eval_ep    = 0
    current_win_rate = 0.0

    print(f"Starting PPO training (MLX GPU): {args.episodes} episodes")
    if not args.no_curriculum:
        stages_str = " → ".join(s[0] for s in CURRICULUM_STAGES)
        print(f"  Curriculum: {stages_str}")

    while episode < start_episode + args.episodes:
        buf.reset()

        for _ in range(ROLLOUT_STEPS):
            obs_mx   = mx.array(obs[None], dtype=mx.float32)
            mask_mx  = mx.array(obs[480:560][None], dtype=mx.float32)
            act_mx, lp_mx, _, val_mx = get_action_and_value(net, obs_mx, mask_mx)
            mx.eval(act_mx, lp_mx, val_mx)

            action_np = np.array(act_mx[0])
            lp_val    = float(lp_mx[0])
            val_val   = float(val_mx[0])

            next_obs, reward, done, _, _ = env.step(action_np)
            buf.add(obs, action_np, lp_val, reward, float(done), val_val)
            ep_reward += reward
            ep_steps  += 1
            obs = next_obs

            if done:
                elapsed = time.time() - ep_start
                writer.writerow([episode, f"{ep_reward:.4f}", ep_steps,
                                  f"{elapsed:.1f}", opponent,
                                  curriculum.stage_idx, f"{current_win_rate:.3f}"])
                csv_file.flush()
                if episode % args.log_frequency == 0:
                    print(f"ep={episode:5d} reward={ep_reward:+.3f} "
                          f"steps={ep_steps} t={elapsed:.1f}s opp={opponent[:25]}"
                          f" stage={curriculum.stage_idx} wr={current_win_rate:.2f}")
                episode += 1
                ep_reward = 0.0
                ep_steps  = 0
                ep_start  = time.time()

                # Eval and curriculum
                if episode - last_eval_ep >= EVAL_FREQ:
                    current_win_rate = run_eval(net, opponent, args.eval_games)
                    last_eval_ep = episode
                    print(f"  Eval: {EVAL_GAMES} games vs {opponent[:20]} → "
                          f"{100*current_win_rate:.0f}% win rate")
                    advanced = curriculum.advance_if_ready(episode, current_win_rate)
                    if advanced:
                        new_opp = curriculum.opponent
                        print(f"  Curriculum advance: {opponent[:20]} → {new_opp[:20]}")
                        opponent = new_opp
                        env.close()
                        env = OrbitWarsEnv(opponent=opponent)

                if episode % CHECKPOINT_EVERY == 0:
                    ckpt_path = ckpt_dir / f"ppo_ep{episode:05d}.npz"
                    save_checkpoint(net, episode, current_win_rate, ckpt_path)
                    pt_path = ckpt_dir / f"ppo_ep{episode:05d}.pt"
                    _save_torch_compat(net, pt_path, episode)
                    all_ckpts = sorted(ckpt_dir.glob("ppo_ep*.npz"),
                                       key=lambda p: p.stat().st_mtime)
                    for old in all_ckpts[:-5]:
                        old.unlink(missing_ok=True)
                        old_pt = ckpt_dir / old.name.replace(".npz", ".pt")
                        old_pt.unlink(missing_ok=True)
                    print(f"  Checkpoint saved: {ckpt_path}")

                obs, _ = env.reset()
                if episode >= start_episode + args.episodes:
                    break

        if episode >= start_episode + args.episodes:
            break

        obs_mx  = mx.array(obs[None], dtype=mx.float32)
        mask_mx = mx.array(obs[480:560][None], dtype=mx.float32)
        _, _, _, last_val_mx = get_action_and_value(net, obs_mx, mask_mx)
        mx.eval(last_val_mx)
        advantages, returns = buf.compute_gae(float(last_val_mx[0]))

        obs_b    = mx.array(buf.obs[:buf.ptr])
        act_b    = mx.array(buf.actions[:buf.ptr], dtype=mx.int32)
        logp_b   = mx.array(buf.log_probs[:buf.ptr])
        adv_b    = mx.array(advantages)
        ret_b    = mx.array(returns)
        mask_b   = obs_b[:, 480:560]

        adv_b = (adv_b - adv_b.mean()) / (adv_b.std() + 1e-8)
        mx.eval(adv_b)

        n = buf.ptr
        for _ in range(EPOCHS):
            idx = np.random.permutation(n)
            for start in range(0, n, BATCH_SIZE):
                mb = idx[start:start + BATCH_SIZE]
                mb_mx = mx.array(mb)
                (loss, _), grads = loss_and_grad(
                    net,
                    obs_b[mb_mx], act_b[mb_mx], logp_b[mb_mx],
                    adv_b[mb_mx], ret_b[mb_mx], mask_b[mb_mx]
                )
                grads = _clip_grads(grads, MAX_GRAD)
                optimizer.update(net, grads)
                mx.eval(net.parameters(), optimizer.state, loss)

    final_path = ckpt_dir / f"ppo_ep{episode:05d}.npz"
    save_checkpoint(net, episode, None, final_path)
    best_path = ckpt_dir / "ppo_best.npz"
    import shutil
    shutil.copy(final_path, best_path)
    _save_torch_compat(net, ckpt_dir / f"ppo_ep{episode:05d}.pt", episode)
    shutil.copy(ckpt_dir / f"ppo_ep{episode:05d}.pt",
                ckpt_dir / "ppo_best.pt")
    print(f"Training complete. Final checkpoint: {final_path}")
    csv_file.close()
    env.close()


def _clip_grads(grads, max_norm):
    leaves = []
    def _collect(g):
        if isinstance(g, dict):
            for v in g.values():
                _collect(v)
        elif isinstance(g, mx.array):
            leaves.append(g)
    _collect(grads)
    if not leaves:
        return grads
    total_norm = mx.sqrt(sum((g * g).sum() for g in leaves))
    scale = mx.minimum(mx.array(max_norm) / (total_norm + 1e-6), mx.array(1.0))
    def _scale(g):
        if isinstance(g, dict):
            return {k: _scale(v) for k, v in g.items()}
        elif isinstance(g, mx.array):
            return g * scale
        return g
    return _scale(grads)


def _save_torch_compat(net, path, episode):
    import torch
    flat = {}
    def _flatten(d, prefix=""):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                _flatten(v, key)
            elif isinstance(v, mx.array):
                flat[key] = torch.tensor(np.array(v))
    _flatten(dict(net.parameters()))
    torch.save({
        "policy_state_dict": flat,
        "episode": episode,
        "score_vs_v38": None,
        "algorithm": "ppo",
    }, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes",        type=int,  default=1000)
    parser.add_argument("--opponent",        type=str,  default="agent_v64.py")
    parser.add_argument("--checkpoint-dir",  type=str,  default="rl/checkpoints")
    parser.add_argument("--seed",            type=int,  default=0)
    parser.add_argument("--resume",          action="store_true")
    parser.add_argument("--log-file",        type=str,  default=None)
    parser.add_argument("--log-frequency",   type=int,  default=50)
    parser.add_argument("--no-curriculum",   action="store_true",
                        help="Skip curriculum; use --opponent directly")
    parser.add_argument("--eval-games",      type=int,  default=EVAL_GAMES)
    parser.add_argument("--eval-frequency",  type=int,  default=EVAL_FREQ)
    parser.add_argument("--bc-pretrain",     type=str,  default=None,
                        help="Path to BC-pretrained .npz checkpoint to initialize weights")
    args = parser.parse_args()
    train(args)
