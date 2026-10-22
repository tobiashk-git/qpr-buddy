"""Build the app's data files. Run by the GitHub Action a few times a day.

data/season.json  - QPR's results and fixtures this season plus the Championship table
                    (football-data.org, needs FOOTBALL_DATA_KEY in the environment or .env)
data/history.json - QPR's points and league position after every game of each Championship
                    season since 15/16, plus each season's final position. The app's slider
                    picks N and compares every season after N games.
                    Past seasons come from football-data.co.uk results files (no key needed).
data/news.json    - BBC Sport QPR headlines
"""
import csv, io, json, os, datetime, pathlib, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

TEAM = "QPR"            # football-data.co.uk name
TEAM_ID = 69            # football-data.org id
FIRST_SEASON = 2015     # QPR came down from the Premier League in 2015
ROOT = pathlib.Path(__file__).resolve().parent.parent
BBC_FEED = "https://feeds.bbci.co.uk/sport/football/teams/queens-park-rangers/rss.xml"

# Points deductions change final positions, and the results files don't record them.
# Keyed by season start year, using football-data.co.uk team names. Add new ones here.
DEDUCTIONS = {
    2018: {"Birmingham": 9},
    2019: {"Wigan": 12},
    2021: {"Derby": 21, "Reading": 6},
    2022: {"Reading": 6},
    2025: {"Sheffield Weds": 18},
}


def api_key():
    if os.environ.get("FOOTBALL_DATA_KEY"):
        return os.environ["FOOTBALL_DATA_KEY"]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("FOOTBALL_DATA_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("FOOTBALL_DATA_KEY is not set")


def get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "qpr-buddy", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def api(path):
    return json.loads(get("https://api.football-data.org/v4" + path, {"X-Auth-Token": api_key()}))


def season_label(start):
    return f"{start % 100:02d}/{(start + 1) % 100:02d}"


# ---------- past seasons (football-data.co.uk) ----------

def fetch_csv(start):
    code = f"{start % 100:02d}{(start + 1) % 100:02d}"
    text = get(f"https://www.football-data.co.uk/mmz4281/{code}/E1.csv").decode("utf-8-sig", errors="replace")
    rows = [row for row in csv.DictReader(io.StringIO(text)) if row.get("FTHG") not in (None, "")]
    for row in rows:
        d, m, y = row["Date"].split("/")
        row["_date"] = datetime.date(int(y) + (2000 if len(y) == 2 else 0), int(m), int(d))
    rows.sort(key=lambda r: (r["_date"], r.get("Time", "")))
    return rows


def standings(t, deductions=None):
    pts = {k: v[0] - (deductions or {}).get(k, 0) for k, v in t.items()}
    return sorted(t, key=lambda k: (-pts[k], -t[k][1], -t[k][2], k))


def progress(rows, start, final=True):
    """QPR's cumulative points and league position after each of their games, plus the final position.
    In-season positions ignore deductions (they landed on different dates); the final one includes them."""
    t, pts, pos = {}, [], []
    total = 0
    for r in rows:
        h, a, hg, ag = r["HomeTeam"], r["AwayTeam"], int(r["FTHG"]), int(r["FTAG"])
        for team, gf, ga in ((h, hg, ag), (a, ag, hg)):
            s = t.setdefault(team, [0, 0, 0])  # points, goal difference, goals for
            s[0] += 3 if gf > ga else 1 if gf == ga else 0
            s[1] += gf - ga
            s[2] += gf
            if team == TEAM:
                total += 3 if gf > ga else 1 if gf == ga else 0
                pts.append(total)
    # position after QPR's k-th game = table at the end of that matchday's date
    dates = [r["_date"] for r in rows if TEAM in (r["HomeTeam"], r["AwayTeam"])]
    t2, i = {}, 0
    for k, d in enumerate(dates):
        while i < len(rows) and rows[i]["_date"] <= d:
            r = rows[i]
            for team, gf, ga in ((r["HomeTeam"], int(r["FTHG"]), int(r["FTAG"])), (r["AwayTeam"], int(r["FTAG"]), int(r["FTHG"]))):
                s = t2.setdefault(team, [0, 0, 0])
                s[0] += 3 if gf > ga else 1 if gf == ga else 0
                s[1] += gf - ga
                s[2] += gf
            i += 1
        pos.append(standings(t2).index(TEAM) + 1)
    out = {"pts": pts, "pos": pos}
    if final:
        out["final"] = standings(t, DEDUCTIONS.get(start)).index(TEAM) + 1
    return out


# ---------- this season (football-data.org) ----------

def side(team):
    return {"id": team["id"], "name": team.get("shortName") or team["name"], "crest": team.get("crest")}


def match_row(m):
    home = m["homeTeam"]["id"] == TEAM_ID
    row = {"id": m["id"], "utc": m["utcDate"], "status": m["status"], "matchday": m.get("matchday"),
           "competition": m["competition"]["name"], "home": home,
           "opponent": side(m["awayTeam"] if home else m["homeTeam"])}
    ft = m["score"]["fullTime"]
    if m["status"] == "FINISHED" and ft["home"] is not None:
        gf, ga = (ft["home"], ft["away"]) if home else (ft["away"], ft["home"])
        row.update({"for": gf, "against": ga, "result": "W" if gf > ga else "D" if gf == ga else "L"})
    return row


def build_season():
    matches = api(f"/teams/{TEAM_ID}/matches")["matches"]
    rows = sorted((match_row(m) for m in matches), key=lambda r: r["utc"])
    results = [r for r in rows if "result" in r][::-1]
    fixtures = [r for r in rows if r["status"] in ("SCHEDULED", "TIMED", "POSTPONED", "IN_PLAY", "PAUSED")]

    st = api("/competitions/ELC/standings")
    total = next(s for s in st["standings"] if s["type"] == "TOTAL")
    table = [{"pos": r["position"], **side(r["team"]), "p": r["playedGames"], "w": r["won"], "d": r["draw"],
              "l": r["lost"], "gf": r["goalsFor"], "ga": r["goalsAgainst"], "gd": r["goalDifference"],
              "pts": r["points"]} for r in total["table"]]
    start = int(st["season"]["startDate"][:4])
    return start, {"season": season_label(start), "results": results, "fixtures": fixtures, "table": table}


# ---------- news ----------

def build_news():
    root = ET.fromstring(get(BBC_FEED))
    items = []
    for i in root.iter("item"):
        thumb = i.find("{http://search.yahoo.com/mrss/}thumbnail")
        items.append({"title": i.findtext("title", "").strip(), "summary": i.findtext("description", "").strip(),
                      "link": i.findtext("link", "").split("?")[0], "source": "BBC Sport",
                      "date": parsedate_to_datetime(i.findtext("pubDate")).isoformat(),
                      "image": thumb.get("url") if thumb is not None else None})
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:30]


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
    data = ROOT / "data"
    data.mkdir(exist_ok=True)

    start, season = build_season()
    season["updated"] = stamp
    (data / "season.json").write_text(json.dumps(season, indent=1))

    me = next(r for r in season["table"] if r["id"] == TEAM_ID)
    seasons = [{"season": season_label(y), **progress(fetch_csv(y), y)} for y in range(FIRST_SEASON, start)]
    # This season: points from the API results; positions from the results file where it has
    # caught up, and the live table position for the latest game.
    cur = {"season": season_label(start), "current": True, "now": me["pos"], "pts": [], "pos": []}
    total = 0
    for m in season["results"][::-1]:
        if m["competition"] == "Championship":
            total += {"W": 3, "D": 1, "L": 0}[m["result"]]
            cur["pts"].append(total)
    try:
        cur["pos"] = progress(fetch_csv(start), start, final=False)["pos"][:len(cur["pts"])]
    except Exception as e:
        print("current-season positions failed:", e)
    cur["pos"] = (cur["pos"] + [None] * len(cur["pts"]))[:len(cur["pts"])]
    if cur["pos"]:
        cur["pos"][-1] = me["pos"]
    seasons.append(cur)
    n = me["p"]
    history = {"games": n, "teams": len(season["table"]), "seasons": seasons, "updated": stamp}
    (data / "history.json").write_text(json.dumps(history, indent=1))

    try:
        (data / "news.json").write_text(json.dumps({"items": build_news(), "updated": stamp}, indent=1))
    except Exception as e:  # keep yesterday's news rather than failing the whole refresh
        print("news failed:", e)

    print(f"{len(season['results'])} results, {len(season['fixtures'])} fixtures, "
          f"{n} games played, position {me['pos']}")


if __name__ == "__main__":
    main()
