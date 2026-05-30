"""
Orbit Wars Simulation Server

A lightweight FastAPI server that exposes the game simulation as an HTTP service.
Runs games in a process pool, returning results as JSON.

Usage:
    uv run --with fastapi --with uvicorn python sim_server.py
    # or
    uvicorn sim_server:app --reload

Endpoints:
    GET  /health       — liveness check
    POST /run          — run N games between two agents, return results
"""

import multiprocessing
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from eval import _run_game

POOL_SIZE = max(1, os.cpu_count() - 1)
_pool: multiprocessing.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = multiprocessing.Pool(processes=POOL_SIZE)
    yield
    _pool.terminate()
    _pool.join()
    _pool = None


app = FastAPI(title="Orbit Wars Simulation Server", lifespan=lifespan)


class RunRequest(BaseModel):
    agent0: str
    agent1: str
    games: int = 10
    seeds: Optional[list[int]] = None  # defaults to range(games)
    jobs: int = 1


class GameResult(BaseModel):
    seed: int
    reward0: float
    reward1: float
    winner: str  # "agent0", "agent1", or "draw"


class RunResponse(BaseModel):
    results: list[GameResult]
    wins0: int
    wins1: int
    draws: int
    win_rate0: float
    total_games: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def run_games(req: RunRequest):
    for path in (req.agent0, req.agent1):
        if not os.path.isfile(path):
            raise HTTPException(status_code=400, detail=f"Agent file not found: {path}")

    seeds = req.seeds if req.seeds is not None else list(range(req.games))
    game_args = [(req.agent0, req.agent1, seed, False) for seed in seeds]

    if req.jobs > 1 and _pool is not None:
        raw = _pool.map(_run_game, game_args)
    else:
        raw = [_run_game(a) for a in game_args]

    results = []
    wins0 = wins1 = draws = 0
    for seed, r0, r1, _ in raw:
        if r0 > r1:
            winner = "agent0"
            wins0 += 1
        elif r1 > r0:
            winner = "agent1"
            wins1 += 1
        else:
            winner = "draw"
            draws += 1
        results.append(GameResult(seed=seed, reward0=r0, reward1=r1, winner=winner))

    total = len(seeds)
    return RunResponse(
        results=results,
        wins0=wins0,
        wins1=wins1,
        draws=draws,
        win_rate0=wins0 / total if total else 0.0,
        total_games=total,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sim_server:app", host="0.0.0.0", port=8765, reload=False)
