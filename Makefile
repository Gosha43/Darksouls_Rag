PY := .venv/bin/python

.PHONY: help setup test wiki youtube wiki-test bg-wiki bg-youtube bg-all status logs stop

help:
	@echo "make setup       create venv, install deps, create .env"
	@echo "make test        run unit tests"
	@echo "make wiki-test   scrape 10 pages/wiki in the foreground (sanity check)"
	@echo "make bg-all      run wiki + youtube scrapers in the background"
	@echo "make bg-wiki     run only the wiki scraper in the background"
	@echo "make bg-youtube  run only the YouTube scraper in the background"
	@echo "make status      show running jobs + how much data is collected"
	@echo "make logs        follow logs (Ctrl+C stops following, NOT the jobs)"
	@echo "make stop        stop all background jobs (safe: scrapers resume where they left off)"

setup:
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt
	@test -f .env || cp .env.example .env
	@echo "Done. Now put your key in .env"

test:
	$(PY) -m pytest -q

wiki:
	$(PY) -m src.scrapers.wiki_scraper --wiki all

youtube:
	$(PY) -m src.scrapers.youtube_scraper

wiki-test:
	$(PY) -m src.scrapers.wiki_scraper --wiki all --limit 10

bg-wiki:
	@scripts/jobs.sh start wiki $(PY) -m src.scrapers.wiki_scraper --wiki all

bg-youtube:
	@scripts/jobs.sh start youtube $(PY) -m src.scrapers.youtube_scraper

bg-all: bg-wiki bg-youtube

status:
	@scripts/jobs.sh status

logs:
	@scripts/jobs.sh logs

stop:
	@scripts/jobs.sh stop
