# QPR Buddy

iPhone home-screen app (PWA) for following QPR. Hosted on GitHub Pages; a GitHub Action refreshes
the data every two hours.

## Pages
- **Home** - crest, league position + form, next match with countdown, latest result, top headlines
- **Results** - this season, newest first; tap one for timeline, stats and line-ups (ESPN summary, fetched on demand)
- **Fixtures** - grouped by month, UK times, per-match and "add all" calendar (.ics) buttons; tap one for
  form + table positions and head to head (league meetings since 2000/01 from data/meetings.json)
- **League** - points-after-N-games vs position chart across every Championship season since 15/16,
  with a games slider (1-46) and a final-position / position-after-N toggle; full table below
- **Live (match day)** - Home shows a live card polling ESPN's keyless scoreboard (eng.2, QPR = team 334) every 30 s
  from 20 min before kick-off; `?demo=YYYYMMDD` replays a past game day
- **News** - BBC Sport QPR feed + link to qpr.co.uk/news (the club site blocks scripted fetches)

## Data (tools/build_data.py)
- football-data.org v4 (free key, `FOOTBALL_DATA_KEY` secret / local `.env`): QPR matches, ELC standings
- football-data.co.uk E1.csv per season (no key): past seasons game by game for the chart
- data/meetings.json: every QPR league game 2000/01 to last season (tools/build_meetings.py, run by
  hand each summer); this season's meetings come from season.json. Table rows carry "csv" (results-file
  name, NAME_OVERRIDES in build_data.py) and last-five "form"
- Points deductions are not in the CSVs: keep `DEDUCTIONS` up to date (final positions verified
  against the user's reference chart for 15/16-25/26)

## Releases
Bump `VERSION` in sw.js and `APP_VERSION` in index.html together.

## Ideas
- Push reminders before kick-off, cup fixtures, player stats
