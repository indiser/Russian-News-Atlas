import html
import os
import re
from datetime import datetime, timezone

import pandas as pd

from db import get_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_CANDIDATES = ["complete-russian-database-cleaned.csv"]

TAG_RE = re.compile(r"<[^>]+>")
# "Vladimir" city vs Vladimir Putin etc. Strip person names before matching.
PERSON_NOISE = re.compile(
    r"(vladimir|владимир)\s+(putin|zelensk\w*|solovyov|путин\w*|зеленск\w*|соловьев\w*|соловьёв\w*)"
)
RU_ENDINGS = "аяьйоеыи"
MAX_HOVER = 10


def clean(text):
    text = TAG_RE.sub(" ", text or "")          # drop html, hrefs would false-match
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def term_regex(term):
    """Whole-word for latin. Cyrillic: stem + up to 3 letters (handles declension)."""
    term = term.strip().lower()
    if not term:
        return None
    if re.search(r"[а-яё]", term):
        stem = term[:-1] if len(term) > 4 and term[-1] in RU_ENDINGS else term
        return re.escape(stem) + r"\w{0,3}"
    return re.escape(term)


def build_pattern(row):
    parts = [term_regex(row["Name"]), term_regex(row["Russianname"])]
    parts = [p for p in parts if p]
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)")


def prepare_articles(news_data):
    prepared, seen_titles = [], set()
    for a in news_data.get("articles", []):
        title = clean(a.get("title"))
        if not title or title in seen_titles:     # syndicated dupes
            continue
        seen_titles.add(title)
        searchable = PERSON_NOISE.sub(" ", f"{title} {clean(a.get('description'))}".lower())
        prepared.append((searchable, title))
    return prepared


def score_locations(df_locations, articles):
    counts, hovers = [], []
    for _, row in df_locations.iterrows():
        pattern = build_pattern(row)
        found = [title for text, title in articles if pattern.search(text)]
        counts.append(len(found))
        if found:
            shown = [f"➤ {html.escape(h, quote=False)}" for h in found[:MAX_HOVER]]
            if len(found) > MAX_HOVER:
                shown.append(f"...and {len(found) - MAX_HOVER} more")
            hovers.append("<br>".join(shown))
        else:
            hovers.append("No active news.")
    out = df_locations.copy()
    out["news_count"] = counts
    out["headlines"] = hovers
    return out


def find_locations_file():
    for i, name in enumerate(CSV_CANDIDATES):
        path = os.path.join(BASE_DIR, name)
        if os.path.exists(path):
            if i > 0:
                print(f"WARNING: using '{name}'. It still has 6 bad duplicate rows. "
                      f"Save the fixed file as '{CSV_CANDIDATES[0]}'.")
            return path
    raise FileNotFoundError(f"No locations CSV in {BASE_DIR}. Looked for: {CSV_CANDIDATES}")


def process_and_push_to_db(news_data):
    """Raises on any failure. Returns number of rows pushed."""
    df_locations = pd.read_csv(find_locations_file())
    # Cities col = whole-region village list. Thousands of generic words
    # ("Novyy", "Gorki", "Lenina"). Matching on it = false positives. Not used.
    df_locations = df_locations.drop(columns=["Cities"], errors="ignore")

    articles = prepare_articles(news_data)
    print(f"Loaded {len(articles)} unique articles. Scanning {len(df_locations)} cities...")

    if not articles:
        raise RuntimeError("0 articles fetched. Not touching the database. Check feed errors above.")

    df_final = score_locations(df_locations, articles)
    df_final = df_final[df_final["news_count"] > 0].sort_values("news_count", ascending=False)
    if df_final.empty:
        raise RuntimeError(f"{len(articles)} articles but 0 city matches. Not touching the database.")
    df_final["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Old frontend key. Delete if index.html uses new column names.
    df_final["State"] = df_final["Federal subject"]

    print("Connecting to database...")
    df_final.to_sql("heatmap_data", get_engine(), if_exists="replace", index=False)
    print(f"DONE. Pushed {len(df_final)} active cities.")
    return len(df_final)