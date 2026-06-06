COMPETITION  := orbit-wars
AGENT        := agent_v61.py
RENDER_AGENT    ?= agent_v61.py
RENDER_OPPONENT ?= random
RENDER_OUT      ?= render_4player_out.ipynb
RENDER2_OUT     ?= render_2player_out.ipynb
MESSAGE      ?= "agent update"
SUBMISSION_ID ?=
EPISODE_ID   ?=
VENV         := .venv
UV           := uv

RL_OPPONENT ?= agent_v38.py
RL_EPISODES ?= 1000

.PHONY: venv install test eval selfplay opponents eval4p submit status episodes replay logs leaderboard render4 render2 help train-ppo train-dqn train-a2c

help:
	@echo "Usage:"
	@echo "  make venv                             Create virtual environment with uv"
	@echo "  make install                          Install kaggle-environments and kaggle CLI"
	@echo "  make test                             Run agent vs random locally"
	@echo "  make eval                             Run $(AGENT) vs main.py (10 games)"
	@echo "  make selfplay                         Run $(AGENT) vs itself (10 games)"
	@echo "  make opponents                        Sweep $(AGENT) vs all known opponents"
	@echo "  make eval4p                           4-player eval: $(AGENT) vs random"
	@echo "  make submit MESSAGE=\"v2 description\"  Submit agent to Kaggle"
	@echo "  make status                           Show recent submissions"
	@echo "  make episodes SUBMISSION_ID=<id>      List episodes for a submission"
	@echo "  make replay   EPISODE_ID=<id>         Download replay for an episode"
	@echo "  make logs     EPISODE_ID=<id>         Download logs for an episode"
	@echo "  make leaderboard                      Show current leaderboard"
	@echo "  make render4 [RENDER_AGENT=<file>]    Run 4-player notebook and export HTML"
	@echo "  make render2 [RENDER_AGENT=<file>] [RENDER_OPPONENT=<file|random>]  Run 2-player notebook and export HTML"

venv:
	$(UV) venv $(VENV)

install: venv
	$(UV) pip install --python $(VENV) "kaggle-environments>=1.28.0" kaggle papermill

test:
	$(UV) run --python $(VENV) python -c "\
from kaggle_environments import make; \
env = make('orbit_wars', configuration={'seed': 42}, debug=True); \
env.run(['$(AGENT)', 'random']); \
final = env.steps[-1]; \
[print(f'Player {i}: reward={s.reward}, status={s.status}') for i, s in enumerate(final)] \
"

eval:
	$(UV) run python eval.py h2h --agent0 $(AGENT) --agent1 main.py --games 10 --swap

selfplay:
	$(UV) run python eval.py h2h --agent0 $(AGENT) --agent1 $(AGENT) --games 10

opponents:
	$(UV) run python eval.py opponents --agent $(AGENT) --games 20

eval4p:
	$(UV) run python eval.py 4p --agent $(AGENT) --games 20

SUBMISSION_ARCHIVE := $(basename $(AGENT)).tar.gz

$(SUBMISSION_ARCHIVE):
	cp $(AGENT) main.py
	tar -czf $(SUBMISSION_ARCHIVE) main.py helper.py

submit: $(SUBMISSION_ARCHIVE)
	uvx kaggle competitions submit $(COMPETITION) -f $(SUBMISSION_ARCHIVE) -m "$(MESSAGE)"
	rm -f $(SUBMISSION_ARCHIVE)

status:
	uvx kaggle competitions submissions $(COMPETITION)

episodes:
	@test -n "$(SUBMISSION_ID)" || (echo "Error: SUBMISSION_ID is required. Usage: make episodes SUBMISSION_ID=<id>" && exit 1)
	uvx kaggle competitions episodes $(SUBMISSION_ID)

replay:
	@test -n "$(EPISODE_ID)" || (echo "Error: EPISODE_ID is required. Usage: make replay EPISODE_ID=<id>" && exit 1)
	uvx kaggle competitions replay $(EPISODE_ID) -p ./replays

logs:
	@test -n "$(EPISODE_ID)" || (echo "Error: EPISODE_ID is required. Usage: make logs EPISODE_ID=<id>" && exit 1)
	uvx kaggle competitions logs $(EPISODE_ID) 0 -p ./logs

leaderboard:
	uvx kaggle competitions leaderboard $(COMPETITION) -s

render4:
	$(UV) pip install --python $(VENV) papermill ipykernel nbconvert --quiet
	$(VENV)/bin/python -m ipykernel install --user --name orbit-wars --display-name "Orbit Wars" 2>/dev/null || true
	$(VENV)/bin/papermill render_4player.ipynb $(RENDER_OUT) -p agent_file $(RENDER_AGENT) --kernel orbit-wars
	$(VENV)/bin/jupyter nbconvert --to html $(RENDER_OUT)

render2:
	$(UV) pip install --python $(VENV) papermill ipykernel nbconvert --quiet
	$(VENV)/bin/python -m ipykernel install --user --name orbit-wars --display-name "Orbit Wars" 2>/dev/null || true
	$(VENV)/bin/papermill render_2player.ipynb $(RENDER2_OUT) -p agent_file $(RENDER_AGENT) -p opponent $(RENDER_OPPONENT) --kernel orbit-wars
	$(VENV)/bin/jupyter nbconvert --to html $(RENDER2_OUT)

train-ppo:
	$(UV) run python rl/ppo.py --episodes $(RL_EPISODES) --opponent $(RL_OPPONENT)

train-dqn:
	$(UV) run python rl/dqn.py --episodes $(RL_EPISODES) --opponent $(RL_OPPONENT)

train-a2c:
	$(UV) run python rl/a2c.py --episodes $(RL_EPISODES) --opponent $(RL_OPPONENT)
