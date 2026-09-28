"""Collect Dark Souls lore video transcripts.

Video discovery: YouTube Data API v3 (channel uploads + optional keyword search).
Transcripts:     youtube-transcript-api (the official captions.download endpoint needs
                 OAuth as the video owner, so it can't be used for other people's videos).

Resumable: videos already saved in data/raw/youtube/ are skipped.
Usage:  python -m src.scrapers.youtube_scraper [--max-per-channel 100] [--search]
"""
import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from tqdm import tqdm

from src.config import (RAW_DIR, TITLE_KEYWORDS, YOUTUBE_CHANNELS,
                        YOUTUBE_SEARCH_QUERIES)
from src.scrapers.http import get_json, make_session

log = logging.getLogger("youtube")
API = "https://www.googleapis.com/youtube/v3"
OUT = RAW_DIR / "youtube"


def channel_uploads_playlist(session, key: str, handle: str) -> str | None:
    data = get_json(session, f"{API}/channels",
                    {"part": "contentDetails", "forHandle": handle, "key": key})
    items = data.get("items", [])
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"] if items else None


def iter_channel_videos(session, key: str, playlist_id: str, max_videos: int):
    params = {"part": "snippet", "playlistId": playlist_id, "maxResults": 50, "key": key}
    n = 0
    while n < max_videos:
        data = get_json(session, f"{API}/playlistItems", params)
        for it in data.get("items", []):
            sn = it["snippet"]
            yield {"video_id": sn["resourceId"]["videoId"], "title": sn["title"],
                   "channel": sn["videoOwnerChannelTitle"] if "videoOwnerChannelTitle" in sn else sn["channelTitle"],
                   "published_at": sn["publishedAt"], "description": sn.get("description", "")}
            n += 1
            if n >= max_videos:
                return
        if "nextPageToken" not in data:
            return
        params["pageToken"] = data["nextPageToken"]


def iter_search_videos(session, key: str, query: str, max_videos: int = 50):
    data = get_json(session, f"{API}/search", {
        "part": "snippet", "q": query, "type": "video", "maxResults": min(max_videos, 50),
        "relevanceLanguage": "en", "key": key})
    for it in data.get("items", []):
        sn = it["snippet"]
        yield {"video_id": it["id"]["videoId"], "title": sn["title"], "channel": sn["channelTitle"],
               "published_at": sn["publishedAt"], "description": sn.get("description", "")}


def fetch_transcript(video_id: str) -> list[dict]:
    from youtube_transcript_api import YouTubeTranscriptApi
    fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US", "en-GB"])
    return [{"text": s.text, "start": s.start, "duration": s.duration} for s in fetched]


def relevant(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in TITLE_KEYWORDS)


def collect_candidates(session, key: str, max_per_channel: int, use_search: bool) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for handle in YOUTUBE_CHANNELS:
        pl = channel_uploads_playlist(session, key, handle)
        if not pl:
            log.warning("channel %s not found - check the handle in config.py", handle)
            continue
        kept = 0
        for v in iter_channel_videos(session, key, pl, max_per_channel):
            if relevant(v["title"]):
                found[v["video_id"]] = v
                kept += 1
        log.info("%s: kept %d relevant videos", handle, kept)
    if use_search:
        for q in YOUTUBE_SEARCH_QUERIES:
            for v in iter_search_videos(session, key, q):
                found.setdefault(v["video_id"], v)
            log.info("search %r done (%d candidates total)", q, len(found))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-channel", type=int, default=100)
    ap.add_argument("--search", action="store_true", help="also run keyword searches (100 quota units each)")
    ap.add_argument("--limit", type=int, default=None, help="max videos to transcribe (for testing)")
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    load_dotenv()
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key or key == "your_key_here":
        raise SystemExit("Set YOUTUBE_API_KEY in .env first (see .env.example)")

    OUT.mkdir(parents=True, exist_ok=True)
    session = make_session()
    candidates = collect_candidates(session, key, args.max_per_channel, args.search)
    todo = [v for vid, v in candidates.items() if not (OUT / f"{vid}.json").exists()]
    if args.limit:
        todo = todo[: args.limit]
    log.info("%d candidates, %d new to transcribe", len(candidates), len(todo))

    saved = failed = 0
    for v in tqdm(todo, desc="transcripts", mininterval=30):
        try:
            segs = fetch_transcript(v["video_id"])
        except Exception as e:  # captions disabled, IP blocked, etc.
            failed += 1
            log.warning("no transcript for %s (%s): %s", v["video_id"], v["title"], type(e).__name__)
            time.sleep(args.delay)
            continue
        doc = {"source": "youtube", **v, "url": f"https://www.youtube.com/watch?v={v['video_id']}",
               "transcript": segs, "text": " ".join(s["text"].replace("\n", " ") for s in segs),
               "scraped_at": datetime.now(timezone.utc).isoformat()}
        (OUT / f"{v['video_id']}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        saved += 1
        time.sleep(args.delay)
    log.info("done: saved=%d failed=%d", saved, failed)


if __name__ == "__main__":
    main()
