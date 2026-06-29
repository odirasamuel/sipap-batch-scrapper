# Fixture Extraction Methods Across APIs

This document explains how fixtures (upcoming matches/events) are extracted from each API source.

## Summary

**YES**, all three APIs have built-in methods for extracting fixtures. The harvest job will orchestrate calling these methods to build a comprehensive fixture list.

---

## Football-Data.org API

**Fixture Methods:**

### 1. `get_today_matches()`
```python
matches = await football_data_api.get_today_matches()
```
- Returns all matches scheduled for today across all 13 competitions
- Useful for: Daily updates, live match tracking

### 2. `get_matches(date_from, date_to, competition_id, status)`
```python
# Get next week's Premier League fixtures
matches = await football_data_api.get_matches(
    date_from='2026-06-28',
    date_to='2026-07-05',
    competition_id='PL',
    status='SCHEDULED'
)
```
- Returns filtered matches by date range, competition, and status
- Status options: `SCHEDULED`, `IN_PLAY`, `FINISHED`
- Useful for: Weekly fixture planning, competition-specific schedules

### 3. `get_match(match_id)`
```python
match = await football_data_api.get_match(123456)
```
- Returns detailed information for a single match
- Useful for: Match detail updates, lineup information

**Data Returned:**
```json
{
  "external_id": "123456",
  "home_team": "Arsenal",
  "away_team": "Chelsea",
  "utc_date": "2026-08-21T15:00:00Z",
  "status": "SCHEDULED",
  "competition": "Premier League",
  "venue": "Emirates Stadium",
  "source": "football-data.org"
}
```

---

## The Odds API

**Fixture Methods:**

### 1. `get_odds(sport, regions, markets)`
```python
# Get upcoming Premier League matches with odds
odds = await odds_api.get_odds(
    sport='soccer_epl',
    regions='uk,us,eu',
    markets='h2h'
)
```
- Returns all upcoming events with betting odds for a sport
- **This is effectively a fixture list** with odds attached
- Includes: event ID, home team, away team, commence time
- Useful for: Fixture discovery + odds in one call

### 2. `get_event_odds(sport, event_id)`
```python
event_odds = await odds_api.get_event_odds(
    sport='soccer_epl',
    event_id='abc123'
)
```
- Returns odds for a specific event
- Useful for: Updating odds for known fixtures

### 3. `get_scores(sport, days_from)`
```python
# Get scores for last 1 day
scores = await odds_api.get_scores(
    sport='soccer_epl',
    days_from=-1
)
```
- Returns recent scores (completed fixtures)
- Useful for: Result updates

**Data Returned:**
```json
{
  "external_id": "abc123",
  "sport_key": "soccer_epl",
  "home_team": "Arsenal",
  "away_team": "Coventry City",
  "commence_time": "2026-08-21T19:00:00Z",
  "bookmakers": [...],
  "best_odds": {
    "home": 1.19,
    "draw": 8.5,
    "away": 22.0
  },
  "num_bookmakers": 37,
  "source": "the-odds-api"
}
```

---

## TheSportsDB API

**Fixture Methods:**

### 1. `get_events_next_league(league_id)`
```python
# Get next 15 Premier League events
events = await thesportsdb_api.get_events_next_league(
    league_id=LEAGUE_IDS['PREMIER_LEAGUE']
)
```
- Returns next 15 upcoming events for a league
- Useful for: Short-term fixture planning

### 2. `get_events(league_id, season)`
```python
# Get all Premier League events for 2025-2026 season
events = await thesportsdb_api.get_events(
    league_id=LEAGUE_IDS['PREMIER_LEAGUE'],
    season='2025-2026'
)
```
- Returns all events for a league season
- Useful for: Long-term fixture planning, season schedules

**Data Returned:**
```json
{
  "idEvent": "2494000",
  "strEvent": "Arsenal vs Coventry City",
  "strTimestamp": "2026-08-21T19:00:00",
  "strHomeTeam": "Arsenal",
  "strAwayTeam": "Coventry City",
  "idLeague": "4328",
  "strLeague": "English Premier League",
  "strSeason": "2026-2027",
  "dateEvent": "2026-08-21",
  "strTime": "19:00:00",
  "strVenue": "Emirates Stadium",
  "strStatus": "NS",
  "source": "thesportsdb"
}
```

---

## Harvest Job Strategy

The harvest job will orchestrate fixture extraction across all three APIs:

### Daily Fixture Harvest (Runs Daily at 00:00 UTC)

```python
async def harvest_fixtures():
    """
    Harvest fixtures from all sources.

    Strategy:
    1. Get today's fixtures + next 7 days from Football-Data.org
    2. Get odds for upcoming matches from The Odds API
    3. Get next 15 events per league from TheSportsDB
    4. Merge and deduplicate fixtures
    5. Store in Aurora PostgreSQL
    6. Cache in Redis (TTL: 6 hours)
    """

    # 1. Football-Data.org: Next 7 days
    football_data = FootballDataAPI(api_key=FOOTBALL_DATA_KEY)
    today = datetime.now().strftime('%Y-%m-%d')
    next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    fd_fixtures = await football_data.get_matches(
        date_from=today,
        date_to=next_week
    )

    # 2. The Odds API: Upcoming matches with odds
    odds_api = OddsAPI(api_key=ODDS_API_KEY)
    epl_odds = await odds_api.get_odds(sport='soccer_epl')
    ucl_odds = await odds_api.get_odds(sport='soccer_uefa_champs_league')

    # 3. TheSportsDB: Next 15 events per league
    thesportsdb = TheSportsDBClient(api_key='123')
    tdb_fixtures = []
    for league_name, league_id in LEAGUE_IDS.items():
        events = await thesportsdb.get_events_next_league(league_id)
        tdb_fixtures.extend(events)

    # 4. Merge fixtures by (home_team, away_team, date)
    merged_fixtures = merge_fixtures(
        fd_fixtures,
        epl_odds + ucl_odds,
        tdb_fixtures
    )

    # 5. Store in database
    await aurora_client.batch_insert_matches(merged_fixtures)

    # 6. Cache in Redis
    await redis_client.batch_set(
        {f"fixture:{fixture['id']}": fixture for fixture in merged_fixtures},
        ttl=21600  # 6 hours
    )
```

### Fixture Deduplication

Since multiple APIs return the same fixtures, we'll deduplicate by:
- **Primary key:** (home_team, away_team, date)
- **Merge strategy:** Combine data from all sources
  - Use Football-Data.org for: official IDs, competition info, venue
  - Use The Odds API for: betting odds, bookmaker data
  - Use TheSportsDB for: team badges, additional metadata

### Update Frequency

| Source | Update Frequency | Rate Limit |
|--------|-----------------|------------|
| Football-Data.org | Daily at 00:00 UTC | 10 req/min |
| The Odds API | Every 6 hours | 500 credits/month (~4 req/day) |
| TheSportsDB | Daily at 00:00 UTC | 30 req/min |

---

## Example: Merged Fixture

```json
{
  "id": "sipap_fixture_20260821_arsenal_coventry",
  "home_team": "Arsenal",
  "away_team": "Coventry City",
  "utc_date": "2026-08-21T19:00:00Z",
  "competition": "English Premier League",
  "venue": "Emirates Stadium",

  "sources": {
    "football_data_org": {
      "external_id": "123456",
      "competition_id": "PL",
      "matchday": 1,
      "status": "SCHEDULED"
    },
    "the_odds_api": {
      "external_id": "abc123",
      "best_odds": {
        "home": 1.19,
        "draw": 8.5,
        "away": 22.0
      },
      "num_bookmakers": 37
    },
    "thesportsdb": {
      "idEvent": "2494000",
      "strVenue": "Emirates Stadium",
      "idLeague": "4328"
    }
  },

  "created_at": "2026-06-28T16:00:00Z",
  "updated_at": "2026-06-28T16:00:00Z"
}
```

---

## Conclusion

**All three APIs have fixture extraction methods.** The harvest job will:
1. Call fixture methods from all APIs in parallel
2. Merge fixtures from multiple sources
3. Deduplicate by (home_team, away_team, date)
4. Store merged fixtures in Aurora PostgreSQL
5. Cache in Redis for fast access

This multi-source approach ensures:
- **Reliability:** If one API is down, we still have fixtures from others
- **Completeness:** Different APIs may have different competitions/leagues
- **Enrichment:** Combine official data + odds + metadata from multiple sources
