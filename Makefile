COMPETITION  := orbit-wars
AGENT        := main.py
MESSAGE      ?= "agent update"
SUBMISSION_ID ?=
EPISODE_ID   ?=
VENV         := .venv
UV           := uv

.PHONY: venv install test eval selfplay submit status episodes replay logs leaderboard help

help:
	@echo "Usage:"
	@echo "  make venv                             Create virtual environment with uv"
	@echo "  make install                          Install kaggle-environments and kaggle CLI"
	@echo "  make test                             Run agent vs random locally"
	@echo "  make eval                             Run agent_v2.py vs main.py (10 games)"
	@echo "  make selfplay                         Run agent_v2.py vs itself (10 games)"
	@echo "  make submit MESSAGE=\"v2 description\"  Submit agent to Kaggle"
	@echo "  make status                           Show recent submissions"
	@echo "  make episodes SUBMISSION_ID=<id>      List episodes for a submission"
	@echo "  make replay   EPISODE_ID=<id>         Download replay for an episode"
	@echo "  make logs     EPISODE_ID=<id>         Download logs for an episode"
	@echo "  make leaderboard                      Show current leaderboard"

venv:
	$(UV) venv $(VENV)

install: venv
	$(UV) pip install --python $(VENV) "kaggle-environments>=1.28.0" kaggle

test:
	$(UV) run --python $(VENV) python -c "\
from kaggle_environments import make; \
env = make('orbit_wars', configuration={'seed': 42}, debug=True); \
env.run(['$(AGENT)', 'random']); \
final = env.steps[-1]; \
[print(f'Player {i}: reward={s.reward}, status={s.status}') for i, s in enumerate(final)] \
"

eval:
	$(UV) run python eval.py --agent0 agent_v2.py --agent1 main.py --games 10

selfplay:
	$(UV) run python eval.py --agent0 agent_v2.py --agent1 agent_v2.py --games 10

submit:
	kaggle competitions submit $(COMPETITION) -f $(AGENT) -m $(MESSAGE)

status:
	kaggle competitions submissions $(COMPETITION)

episodes:
	@test -n "$(SUBMISSION_ID)" || (echo "Error: SUBMISSION_ID is required. Usage: make episodes SUBMISSION_ID=<id>" && exit 1)
	kaggle competitions episodes $(SUBMISSION_ID)

replay:
	@test -n "$(EPISODE_ID)" || (echo "Error: EPISODE_ID is required. Usage: make replay EPISODE_ID=<id>" && exit 1)
	kaggle competitions replay $(EPISODE_ID) -p ./replays

logs:
	@test -n "$(EPISODE_ID)" || (echo "Error: EPISODE_ID is required. Usage: make logs EPISODE_ID=<id>" && exit 1)
	kaggle competitions logs $(EPISODE_ID) 0 -p ./logs

leaderboard:
	kaggle competitions leaderboard $(COMPETITION) -s
