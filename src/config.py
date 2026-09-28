"""Central config: edit this file to change what gets scraped."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"

USER_AGENT = "griffithjr@msoe.edu"
REQUEST_DELAY = 1.0  # seconds between requests; be polite to the wikis

# Fandom wikis expose the MediaWiki API at <base>/api.php
WIKIS = {
    "ds1": {"game": "Dark Souls", "base": "https://darksouls.fandom.com"},
    "ds2": {"game": "Dark Souls II", "base": "https://darksouls2.fandom.com"},
    "ds3": {"game": "Dark Souls III", "base": "https://darksouls3.fandom.com"},
}

# YouTube: channels are resolved by @handle -> uploads playlist (cheap: ~1 quota unit/page).
# Verify these handles exist and add/remove channels as you like.
YOUTUBE_CHANNELS = ["@VaatiVidya", "@EpicNameBro"]

# Optional keyword searches (EXPENSIVE: 100 quota units each, 10,000/day free quota).
YOUTUBE_SEARCH_QUERIES = [
    "dark souls lore explained",
    "dark souls 2 lore",
    "dark souls 3 lore",
]

# Only keep channel uploads whose title contains one of these (case-insensitive).
TITLE_KEYWORDS = [
    "dark souls", "ds1", "ds2", "ds3", "lordran", "drangleic", "lothric",
    "gwyn", "anor londo", "firelink", "lord of cinder", "kindling", "undead",
]
