### 2.6 Data Acquisition Strategy (API-Based - Batch-First Architecture)

**Architecture Pivot (2026-06-28):** Transitioned from web scraping to professional sports data APIs for reliability, legal compliance, and maintainability.

**Challenge:** Initial web scraping approach (FlashScore, Futbol24, ESPN) proved unreliable:
- Sites are JavaScript SPAs (Single Page Applications) - content loads after JS execution
- CSS selectors don't match actual DOM structure
- Anti-scraping measures (rate limiting, bot detection)
- High maintenance burden (selectors break frequently)
- Legal gray area (Terms of Service violations)

**Solution:** **API-based data collection** using 3 free-tier professional sports APIs, orchestrated by a scheduled harvest job.

#### 2.6.1 API-Based Architecture

**Core Principle:** Data collection happens **independently** of user requests via scheduled API harvest jobs. User requests read from pre-populated cache/database (no real-time API calls).

```
┌─────────────────────────────────────────────────────────────────┐
│          SCHEDULED DATA COLLECTION (Proactive)                   │
│                Independent of User Requests                      │
└─────────────────────────────────────────────────────────────────┘

EventBridge Schedule
├─── 12:00 AM Daily (Primary Harvest) ─────────────────────────┐
│    Fargate Task: sipap-batch-scraper (API Orchestration)      │
│    Duration: 2-3 minutes                                      │
│    Fetches (via APIs):                                        │
│    ├─ Football-Data.org:                                     │
│    │  ├─ Match fixtures (next 7 days, 13 competitions)      │
│    │  ├─ League standings (Premier League, La Liga, etc.)   │
│    │  └─ Team information                                    │
│    ├─ The Odds API:                                          │
│    │  ├─ Betting odds (37 bookmakers)                       │
│    │  ├─ Best odds calculation                              │
│    │  └─ Odds movements                                     │
│    └─ TheSportsDB:                                           │
│       ├─ Next 15 events per league                          │
│       ├─ Team badges, metadata                              │
│       └─ Player information                                 │
│    Merges: Deduplicate by (home_team, away_team, date)      │
│    Stores: Aurora (persistent) + ElastiCache (hot cache)    │
│    Cost: ~$0 (all free tier APIs)                           │
│                                                              │
├─── Every 30 Minutes (Odds Refresh) ─────────────────────────┐
│    Lambda: odds_updater                                      │
│    Duration: 1 minute                                        │
│    Updates:                                                  │
│    └─ The Odds API: Refresh odds for upcoming matches       │
│    Stores: Aurora + refresh ElastiCache                     │
│    Cost: ~$0 (free tier: 500 credits/month)                 │
│                                                              │
└─── Hourly (Fixture & Standings Refresh) ────────────────────┐
     Lambda: fixture_updater                                   │
     Duration: 1 minute                                        │
     Updates:                                                  │
     ├─ Football-Data.org: New fixtures, standings            │
     └─ TheSportsDB: Event updates                            │
     Stores: Aurora + refresh ElastiCache                     │
     Cost: ~$0 (free tier)                                    │


┌─────────────────────────────────────────────────────────────────┐
│            USER REQUEST FLOW (Read-Only, No API Calls)          │
└─────────────────────────────────────────────────────────────────┘

User Request (WhatsApp/API)
  ↓
sipap-sports-data-mcp (Lambda - READ ONLY)
  ├─ Check ElastiCache (99% hit rate)
  │   ↓ Cache Hit
  │   └─ Return data (<50ms) ✅
  │
  └─ Cache Miss (1% of requests)
      ↓
      Query Aurora Database
      ↓
      Return data + populate cache (<100ms) ✅

Performance: <100ms response (vs 2-3s if scraping)
Cost: $0.00001 per request (API data pre-fetched)
Reliability: 99%+ (pre-fetched data always available)
```

#### 2.6.2 API Technology Stack

**Primary APIs (All FREE Tier):**

**1. Football-Data.org API**
```python
from sipap_batch_scraper.apis import FootballDataAPI

api = FootballDataAPI(api_key=FOOTBALL_DATA_KEY)

# Get next 7 days of fixtures
today = datetime.now().strftime('%Y-%m-%d')
next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
fixtures = await api.get_matches(date_from=today, date_to=next_week)

# Get Premier League standings
standings = await api.get_standings('PL')

# Get team info
team = await api.get_team(133604)
```

**Coverage:**
- 13 competitions (World Cup, Premier League, Champions League, Bundesliga, La Liga, Serie A, Ligue 1, etc.)
- Rate limit: 10 requests/minute
- Cost: **FREE forever**

**2. The Odds API**
```python
from sipap_batch_scraper.apis import OddsAPI, SPORT_KEYS

api = OddsAPI(api_key=ODDS_API_KEY)

# Get odds for Premier League matches
odds = await api.get_odds(
    sport=SPORT_KEYS['PREMIER_LEAGUE'],
    regions='uk,us,eu',
    markets='h2h'  # Head-to-head (match winner)
)

# Extract best odds from 37 bookmakers
for event in odds:
    print(f"{event['home_team']} vs {event['away_team']}")
    print(f"Best odds: {event['best_odds']}")
```

**Coverage:**
- 40+ sports, 80+ bookmakers
- 37 bookmakers for soccer matches
- Automatic best odds calculation
- Rate limit: 500 credits/month (~16 requests/day)
- Cost: **FREE tier**

**3. TheSportsDB API**
```python
from sipap_batch_scraper.apis import TheSportsDBClient, LEAGUE_IDS

api = TheSportsDBClient(api_key='123')  # Free tier key

# Search for teams
teams = await api.search_team('Arsenal')

# Get next Premier League events
events = await api.get_events_next_league(LEAGUE_IDS['PREMIER_LEAGUE'])

# Get league standings
standings = await api.get_league_standings(
    league_id=LEAGUE_IDS['PREMIER_LEAGUE'],
    season='2025-2026'
)
```

**Coverage:**
- 40+ sports (Soccer, NBA, NFL, MLB, NHL, etc.)
- Team info, player stats, event schedules, standings
- Rate limit: 30 requests/minute
- Cost: **FREE tier** (read-only, delayed live scores)

**Optional Upgrade: API-Football (Placeholder)**
- Cost: $19/mo (PRO tier)
- Features: Real-time stats, lineups, live scores (7,500 req/day)
- Status: Placeholder implementation, upgrade when budget allows

#### 2.6.3 API Data Sources Comparison

| API | Data Provided | Rate Limit | Cost | Status |
|-----|---------------|------------|------|--------|
| **Football-Data.org** | Match fixtures, standings, teams, H2H | 10 req/min | FREE forever | ✅ ACTIVE |
| **The Odds API** | Betting odds from 37 bookmakers | 500 credits/month | FREE tier | ✅ ACTIVE |
| **TheSportsDB** | Team info, player stats, events, standings | 30 req/min | FREE tier | ✅ ACTIVE |
| **API-Football** | Real-time stats, lineups, live scores | 7,500 req/day | $19/mo | 🔜 Placeholder |

**Multi-Source Strategy:**
- **Complementary data:** Each API provides different perspectives
  - Football-Data.org: Official fixtures, competition data
  - The Odds API: Betting markets, bookmaker odds
  - TheSportsDB: Team/player metadata, event schedules
- **No fallback hierarchy:** Merge data from all sources for completeness
- **Deduplication:** Merge fixtures by (home_team, away_team, date)

#### 2.6.4 Fixture Extraction Methods

**All APIs have fixture extraction methods:**

| API | Fixture Method | Returns |
|-----|----------------|---------|
| Football-Data.org | `get_matches(date_from, date_to)` | Fixtures with official IDs, competition info, venues |
| The Odds API | `get_odds(sport)` | Upcoming matches with betting odds (37 bookmakers) |
| TheSportsDB | `get_events_next_league(league_id)` | Next 15 events with team badges, metadata |

**Harvest Job Strategy:**
```python
async def harvest_fixtures():
    """
    Harvest fixtures from all 3 free APIs.

    Strategy:
    1. Get fixtures from Football-Data.org (next 7 days)
    2. Get odds from The Odds API (enriches fixtures with betting data)
    3. Get events from TheSportsDB (adds team badges, metadata)
    4. Merge by (home_team, away_team, date)
    5. Store in Aurora + cache in Redis
    """

    # 1. Football-Data.org: Official fixtures
    fd_api = FootballDataAPI(api_key=FD_KEY)
    fd_fixtures = await fd_api.get_matches(
        date_from=today,
        date_to=next_week
    )

    # 2. The Odds API: Betting odds
    odds_api = OddsAPI(api_key=ODDS_KEY)
    epl_odds = await odds_api.get_odds(sport='soccer_epl')
    ucl_odds = await odds_api.get_odds(sport='soccer_uefa_champs_league')

    # 3. TheSportsDB: Event metadata
    tdb_api = TheSportsDBClient(api_key='123')
    tdb_events = []
    for league_id in [LEAGUE_IDS['PREMIER_LEAGUE'], LEAGUE_IDS['CHAMPIONS_LEAGUE']]:
        events = await tdb_api.get_events_next_league(league_id)
        tdb_events.extend(events)

    # 4. Merge fixtures
    merged = merge_fixtures(fd_fixtures, epl_odds + ucl_odds, tdb_events)

    # 5. Store
    await aurora_client.batch_insert_matches(merged)
    await redis_client.batch_set(
        {f"fixture:{f['id']}": f for f in merged},
        ttl=21600  # 6 hours
    )
```

#### 2.6.5 Caching Strategy (ElastiCache TTL)

| Data Type | Cache TTL | Update Frequency | Rationale |
|-----------|-----------|------------------|-----------|
| **Match fixtures** | 6 hours | Daily | Refreshed with daily harvest |
| **Betting odds** | 30 minutes | Every 30 minutes | Odds change frequently |
| **Team stats** | 24 hours | Daily | Stable data, low volatility |
| **League standings** | 6 hours | Hourly | Updated after matches |
| **Team metadata** | 7 days | Daily | Rarely changes (badges, info) |
| **Player info** | 7 days | Daily | Stable unless transfers |

**Cache Pre-Warming:**
- Daily batch job pre-populates cache at 12 AM
- 99%+ cache hit rate during user peak hours
- Cache misses trigger Aurora fallback (no live API calls)

#### 2.6.6 Cost Comparison: API vs Web Scraping

**Web Scraping (Previous Architecture - REJECTED):**
```
Infrastructure:
├─ Fargate batch scraper (daily): $6/month
├─ Lambda hourly updates: $15/month
├─ Lambda live tracker: $3/month
├─ Playwright layers: ~$5/month
└─ Total: $29/month ❌

Challenges:
- JavaScript SPA scraping unreliable (timeouts)
- CSS selectors break frequently (high maintenance)
- Anti-scraping measures (IP bans, CAPTCHAs)
- Legal gray area (ToS violations)
- 2-3 second response times
```

**API-Based (Current Architecture - APPROVED):**
```
API Costs:
├─ Football-Data.org: $0/month (FREE forever) ✅
├─ The Odds API: $0/month (FREE 500 credits/month) ✅
├─ TheSportsDB: $0/month (FREE 30 req/min) ✅
└─ Total: $0/month 🎉

Infrastructure:
├─ Fargate daily harvest (API calls): ~$0.05/month (minimal)
├─ Lambda odds updater (30 mins): ~$1.20/month
├─ Lambda fixture updater (hourly): ~$0.15/month
└─ Total: $0.30/month ✅

Benefits:
- Reliable structured data (JSON APIs)
- Official data sources (no scraping errors)
- Legal compliance (proper API agreements)
- <100ms response times (cache reads)
- Zero maintenance (providers handle uptime)

Savings: $28.70/month (99% cost reduction) 🎉
```

**Optional Upgrades (Future):**
- API-Football: $19/mo (real-time stats, 7,500 req/day)
- TheSportsDB Premium: $9/mo (real-time scores, no delay)

#### 2.6.7 Rate Limiting & API Management

**Request Budgets:**

| API | Rate Limit | Daily Budget | Strategy |
|-----|------------|--------------|----------|
| Football-Data.org | 10 req/min | ~14,400 req/day | Batch requests, avoid polling |
| The Odds API | 500 credits/month | ~48 req/day | Cache with 30-minute TTL |
| TheSportsDB | 30 req/min | ~43,200 req/day | Batch team/player lookups |

**Rate Limit Handling:**
```python
class BaseAPIClient:
    async def _request(self, method, endpoint, params):
        for attempt in range(self.max_retries):
            try:
                async with session.request(method, url, params) as response:
                    response.raise_for_status()
                    return await response.json()

            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    raise

                # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(2 ** attempt)
```

**Monitoring:**
- CloudWatch metrics: `api_success_rate`, `api_credits_used`
- Alert if success rate drops below 95%
- Daily API usage report (track free tier limits)

#### 2.6.8 Repository Structure

**Updated Repository: `sipap-batch-scraper`**

```
sipap/repos/sipap-batch-scraper/
├── apis/                        # API clients (NEW)
│   ├── base.py                  # BaseAPIClient with retry logic
│   ├── football_data.py         # Football-Data.org client ✅
│   ├── odds_api.py              # The Odds API client ✅
│   ├── thesportsdb.py           # TheSportsDB client ✅
│   └── api_football.py          # API-Football placeholder 🔜
├── jobs/
│   ├── daily_harvest.py         # Daily API orchestration (12 AM)
│   ├── odds_updater.py          # Odds refresh (every 30 minutes)
│   └── fixture_updater.py       # Fixture refresh (hourly)
├── storage/
│   ├── aurora.py                # Aurora database client
│   └── redis.py                 # ElastiCache client
├── test_api_integration.py      # Real API integration tests ✅
├── Dockerfile                    # Fargate container image
├── requirements.txt              # aiohttp, certifi, etc.
├── tests/
│   ├── test_apis.py
│   └── test_jobs.py
├── FIXTURE-EXTRACTION.md         # Fixture extraction guide ✅
└── README.md
```

**Deployment:**
- **Fargate Task:** Daily harvest job (API orchestration)
- **Lambda Functions:** Odds updater + fixture updater
- **EventBridge Rules:** Schedule triggers (12 AM daily, 30 minutes, hourly)

#### 2.6.9 Cost Breakdown (Data Collection)

| Component | Configuration | Monthly Cost |
|-----------|---------------|--------------|
| **API Costs** | | |
| └─ Football-Data.org | FREE forever | $0 |
| └─ The Odds API | FREE 500 credits/month | $0 |
| └─ TheSportsDB | FREE 30 req/min | $0 |
| **Infrastructure Costs** | | |
| └─ Fargate Daily Harvest | 3 min/day × $0.04/hour | $0.05 |
| └─ Lambda Odds Updater | 4 runs/day × 30 days | $0.10 |
| └─ Lambda Fixture Updater | 24 runs/day × 30 days | $0.15 |
| **Data Storage** | | |
| └─ ElastiCache (Data Cache) | 1.5 GB serverless | $15 |
| └─ Aurora (Data Storage) | 0.5-1 ACU | $43-67 |
| **Total Data Infrastructure** | | **$58.30-82.30/month** |

**Compare to Web Scraping:** $82-106/month (infrastructure) + $29/month (scraping)
**API Architecture:** $58.30-82.30/month (infrastructure only, APIs free)
**Savings:** $52.70-52.70/month (47-48% cost reduction) 🎉

**Additional Benefits:**
- Zero API costs (3 free-tier APIs)
- Better data reliability (official sources)
- Legal compliance (proper API agreements)
- Lower maintenance (no CSS selector breakage)
- Faster responses (<100ms vs 2-3s)

---
