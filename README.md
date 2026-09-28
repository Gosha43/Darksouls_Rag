# Dark Souls Lore RAG - Data Collection

Scrapers that build the raw corpus for a Dark Souls I/II/III lore RAG assistant.

| Source | How | Output |
|---|---|---|
| Fandom wikis (DS1, DS2, DS3) | MediaWiki API (`/api.php`), HTML cleaned into sections | `data/raw/wiki/<ds1\|ds2\|ds3>/*.json` |
| YouTube lore videos | Data API v3 finds videos, `youtube-transcript-api` gets captions | `data/raw/youtube/<video_id>.json` |

## Quick start
```bash
make setup            # venv + deps + .env
# edit .env -> YOUTUBE_API_KEY=...
# edit src/config.py -> your contact email in USER_AGENT, channels, keywords
make test
make wiki-test        # 10 pages per wiki, foreground sanity check
make bg-all           # full scrape in the background
```

## Working while it runs
```bash
make status   # running jobs + file counts
make logs     # tail logs (Ctrl+C only stops the tail)
make stop     # stop jobs; re-running `make bg-all` resumes (finished files are skipped)
```
Jobs use `nohup`, so they survive closing the terminal but NOT a laptop sleeping/shutdown.
On Windows use WSL.

## Notes
- Requests are throttled (1s wiki, 2s transcripts). Please don't lower this much.
- YouTube quota: channel uploads are ~1 unit/page; `--search` costs 100 units per query (10k/day free).
- Some videos have no captions or transcripts get IP-blocked; failures are logged and skipped.
- Wiki text is CC-BY-SA (Fandom) - keep source URLs in the data for citation/attribution.
- Next steps: `src/processing/` for chunking -> embeddings -> vector DB -> RAG chain.
