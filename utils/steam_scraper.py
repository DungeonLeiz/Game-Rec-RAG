import requests
import json
import time
import os
from pathlib import Path
from bs4 import BeautifulSoup
from collections import deque

DATA_DIR = Path("data")
CHECKPOINT_DIR = Path("checkpoints")
RESULTS_PATH = DATA_DIR / "steam_games.jsonl"
PROCESSED_PATH = CHECKPOINT_DIR / "processed_ids.json"
EXCLUDED_PATH = CHECKPOINT_DIR / "excluded_ids.json"
ERROR_PATH = CHECKPOINT_DIR / "error_ids.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)

def load_json(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_checkpoints():
    processed = set(load_json(PROCESSED_PATH) or [])
    excluded = set(load_json(EXCLUDED_PATH) or [])
    error = set(load_json(ERROR_PATH) or [])
    return processed, excluded, error

def save_checkpoints(processed, excluded, error):
    save_json(list(processed), PROCESSED_PATH)
    save_json(list(excluded), EXCLUDED_PATH)
    save_json(list(error), ERROR_PATH)

def get_all_appids():
    url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    apps = r.json().get("applist", {}).get("apps", [])
    return [a["appid"] for a in apps if a.get("appid")]

def fetch_appdetails(appid, lang="english"):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l={lang}"
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        return None
    data = r.json().get(str(appid), {})
    if not data.get("success"):
        return None
    info = data.get("data", {})
    if info.get("type") != "game":
        return None
    if info.get("release_date", {}).get("coming_soon"):
        return None
    if info.get("release_date", {}).get("date") == "Coming Soon":
        return None
    if info.get("release_date", {}).get("early_access"):
        return None
    return info

def fetch_tags(appid):
    url = f"https://store.steampowered.com/app/{appid}"
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    return [t.get_text(strip=True) for t in soup.select(".app_tag")]

def fetch_top_review(appid):
    url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {
        "json": 1,
        "num_per_page": 1,
        "filter": "all",
        "review_type": "all",
        "purchase_type": "all",
        "day_range": 9223372036854775807,
        "sort": "helpful"
    }
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        return None
    reviews = r.json().get("reviews", [])
    if not reviews:
        return None
    rev = reviews[0]
    return {
        "review": rev.get("review"),
        "votes_up": rev.get("votes_up"),
        "votes_funny": rev.get("votes_funny")
    }

def scrape_game(appid):
    info = fetch_appdetails(appid)
    if not info:
        return None
    game = {
        "appid": appid,
        "name": info.get("name"),
        "release_date": info.get("release_date", {}).get("date"),
        "developers": info.get("developers", []),
        "publishers": info.get("publishers", []),
        "genres": [g["description"] for g in info.get("genres", [])],
        "categories": [c["description"] for c in info.get("categories", [])],
        "tags": fetch_tags(appid),
        "metacritic": info.get("metacritic", {}).get("score"),
        "short_description": info.get("short_description"),
        "steam_url": f"https://store.steampowered.com/app/{appid}"
    }
    review = fetch_top_review(appid)
    if review:
        game["top_review"] = review
    return game

def save_game(game):
    with open(RESULTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(game, ensure_ascii=False) + "\n")

def scrape_all(window_seconds=300, max_per_window=200, checkpoint_every=1000):
    appids = get_all_appids()
    processed, excluded, error = load_checkpoints()
    remaining = deque([aid for aid in appids if aid not in processed and aid not in excluded and aid not in error])
    req_count = 0
    window_start = time.time()
    processed_count = 0
    with open(RESULTS_PATH, "a", encoding="utf-8") as _:
        pass
    while remaining:
        now = time.time()
        if now - window_start >= window_seconds:
            window_start = now
            req_count = 0
        if req_count >= max_per_window:
            sleep_for = window_seconds - (now - window_start) + 1
            time.sleep(max(1, sleep_for))
            continue
        appid = remaining.popleft()
        game = scrape_game(appid)
        req_count += 1
        if game:
            save_game(game)
            processed.add(appid)
            processed_count += 1
            print(f"Saved {game['name']}")
        else:
            excluded.add(appid)
        if processed_count and processed_count % checkpoint_every == 0:
            save_checkpoints(processed, excluded, error)
            print(f"Checkpoint: {len(processed)} processed")
        time.sleep(2)
    save_checkpoints(processed, excluded, error)

if __name__ == "__main__":
    scrape_all()
