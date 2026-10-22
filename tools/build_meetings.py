"""Build data/meetings.json: every QPR league game from 2000/01 to last season, across the top
three divisions (football-data.co.uk, no key). Past seasons never change, so this runs by hand
once a year (or when FIRST_SEASON moves). This season's games come from build_data.py."""
import json, datetime, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_data import fetch_csv, season_label, TEAM, ROOT  # noqa: E402

FIRST_SEASON = 2000
DIVISIONS = {"E0": "Premier League", "E1": "Championship", "E2": "League One"}


def main():
    today = datetime.date.today()
    current = today.year if today.month >= 7 else today.year - 1
    games = []
    for year in range(FIRST_SEASON, current):
        for div, name in DIVISIONS.items():
            try:
                rows = fetch_csv(year, div)
            except Exception as e:
                print(year, div, "skipped:", e)
                continue
            mine = [r for r in rows if TEAM in (r["HomeTeam"], r["AwayTeam"])]
            for r in mine:
                games.append({"date": r["_date"].isoformat(), "season": season_label(year), "comp": name,
                              "home": r["HomeTeam"], "away": r["AwayTeam"], "hg": int(r["FTHG"]), "ag": int(r["FTAG"])})
            if mine:
                print(season_label(year), name, len(mine))
    games.sort(key=lambda g: g["date"])
    (ROOT / "data" / "meetings.json").write_text(json.dumps({"games": games}, separators=(",", ":")))
    print(len(games), "games")


if __name__ == "__main__":
    main()
