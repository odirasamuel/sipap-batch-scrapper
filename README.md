# SIPAP Batch Data Collection (API-Based)

**Proactive sports data collection via APIs for SIPAP platform**

Version: 0.2.0 (API-Based Architecture v2.3)
Status: In Development
Phase: Phase 2 (Data Layer)
Architecture Update: 2026-06-28 (Pivoted from web scraping to APIs)

---

## Overview

The SIPAP Batch Data Collection system harvests sports data from **professional APIs** before users request it. This batch-first, API-based architecture eliminates web scraping challenges while providing reliable, legal, and cost-free data collection.

### Architecture Pivot (2026-06-28)

**Why We Pivoted from Web Scraping:**
- JavaScript SPAs (FlashScore, Futbol24, ESPN) proved unreliable
- Content loads after JS execution, CSS selectors don't match actual DOM
- Anti-scraping measures (rate limiting, IP bans, CAPTCHAs)
- High maintenance burden (selectors break frequently)
- Legal gray area (Terms of Service violations)

**Solution:** 3 Free-Tier Professional APIs
- Official structured data (JSON, not HTML parsing)
- Legal compliance (proper API agreements)
- Zero maintenance (providers handle uptime)
- Better data quality and reliability

### Key Benefits

- ✅ **100% cost reduction:** $0/month (free APIs) vs $29/month (web scraping)
- ✅ **<100ms responses:** Pre-fetched data from cache
- ✅ **Legal compliance:** Official API agreements, no ToS violations
- ✅ **Zero maintenance:** No CSS selector breakage
- ✅ **Better data quality:** Structured JSON from authoritative sources
- ✅ **99%+ reliability:** Pre-fetched data always available

---

## Architecture

```
EventBridge Schedule → Fargate/Lambda → API Harvest Job
                                              ↓
                        Football-Data.org + The Odds API + TheSportsDB
                                              ↓
                                    Merge & Deduplicate Fixtures
                                              ↓
                              Aurora Database + ElastiCache (6h TTL)
                                              ↓
                        Read by sipap-sports-data-mcp (NO API CALLS)
```

### Data Collection Schedule

| Job | Frequency | Runtime | Purpose |
|-----|-----------|---------|---------|
| **Daily Harvest** | 12:00 AM | 2-3 min | Fetch ALL upcoming fixtures (next 7 days) |
| **Odds Refresh** | Every 30 minutes | 1 min | Update betting odds from 37 bookmakers |
| **Fixture Update** | Every hour | 1 min | Refresh fixtures, standings, events |

---

## Data Sources (All FREE Tier)

### 1. Football-Data.org API (PRIMARY)
- **Coverage:** 13 major competitions (Premier League, Champions League, La Liga, etc.)
- **Data:** Match fixtures, standings, team info, head-to-head
- **Rate Limit:** 10 req/min
- **Cost:** FREE forever
- **Status:** ✅ Implemented & tested

### 2. The Odds API (SECONDARY)
- **Coverage:** 40+ sports, 37 bookmakers for soccer
- **Data:** Betting odds (h2h, spreads, totals), best odds calculation
- **Rate Limit:** 500 credits/month (~16 req/day)
- **Cost:** FREE tier
- **Status:** ✅ Implemented & tested

### 3. TheSportsDB API (TERTIARY)
- **Coverage:** 40+ sports, comprehensive metadata
- **Data:** Team badges, player info, event schedules, standings
- **Rate Limit:** 30 req/min
- **Cost:** FREE tier (read-only, delayed live scores)
- **Status:** ✅ Implemented & tested

---

## Repository Structure

```
sipap-batch-scraper/
├── src/sipap_batch_scraper/
│   ├── apis/                     # API clients (NEW - v2.3)
│   │   ├── base.py               # BaseAPIClient with retry logic
│   │   ├── football_data.py      # Football-Data.org client ✅
│   │   ├── odds_api.py           # The Odds API client ✅
│   │   ├── thesportsdb.py        # TheSportsDB client ✅
│   │   └── api_football.py       # API-Football placeholder 🔜
│   ├── jobs/
│   │   ├── daily_harvest.py      # Daily API orchestration (12 AM)
│   │   ├── odds_updater.py       # Odds refresh (every 30 minutes)
│   │   └── fixture_updater.py    # Fixture refresh (hourly)
│   ├── storage/
│   │   ├── aurora.py             # Aurora database client
│   │   └── redis.py              # ElastiCache client
│   └── __init__.py
├── tests/
│   └── unit/
│       ├── apis/
│       │   ├── test_football_data.py
│       │   ├── test_odds_api.py
│       │   └── test_thesportsdb.py
│       ├── test_storage_aurora.py
│       └── test_storage_redis.py
├── test_api_integration.py       # Real API integration tests ✅
├── Dockerfile                     # Fargate container image
├── requirements.txt               # aiohttp, certifi, etc.
├── pyproject.toml
├── FIXTURE-EXTRACTION.md          # Fixture extraction guide ✅
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.12+
- Access to Aurora database
- Access to ElastiCache Redis
- API keys:
  - Football-Data.org (FREE forever)
  - The Odds API (FREE 500 credits/month)
  - TheSportsDB (FREE tier, key: '123')

### Setup

```bash
# Clone repository
cd /Users/charlesotuya/AI-Odi/sentinel/sipap/repos/sipap-batch-scraper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e '.[dev]'
```

---

## Usage

### API Clients

**Football-Data.org API:**

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

**The Odds API:**

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

**TheSportsDB API:**

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

### Harvest Job Strategy

```python
async def harvest_fixtures():
    """
    Harvest fixtures from all 3 free APIs.

    Strategy:
    1. Get fixtures from Football-Data.org (next 7 days)
    2. Get odds from The Odds API (enriches fixtures with betting data)
    3. Get events from TheSportsDB (adds team badges, metadata)
    4. Merge by (home_team, away_team, date)
    5. Store in Aurora + cache in Redis (6-hour TTL)
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

### Storage Clients

**Aurora Client:**

```python
from sipap_batch_scraper.storage.aurora import AuroraClient

client = AuroraClient(
    host="sipap-dev-aurora.cluster-xxx.us-east-1.rds.amazonaws.com",
    port=5432,
    database="sipap_dev",
    user="sipap_admin",
    password="password"
)

await client.connect()

# Insert match data
await client.insert_match({
    'external_id': 'fd_12345',
    'home_team': 'Arsenal',
    'away_team': 'Chelsea',
    'scheduled_at': '2026-06-27T15:00:00Z',
    'league': 'Premier League',
    'source': 'football-data'
})

# Query matches
matches = await client.query_matches(date='2026-06-27', league='Premier League')

await client.close()
```

**Redis Client:**

```python
from sipap_batch_scraper.storage.redis import RedisClient

client = RedisClient(
    host="sipap-dev-cache.redis.amazonaws.com",
    port=6379,
    db=0
)

await client.connect()

# Cache match data (6 hour TTL)
await client.setex('match:12345', 21600, {'home': 'Arsenal', 'away': 'Chelsea'})

# Get cached data
match = await client.get('match:12345')

await client.close()
```

---

## API Client Pattern (BaseAPIClient)

All API clients inherit from `BaseAPIClient` with built-in:
- **Async HTTP** (aiohttp)
- **Retry logic** (exponential backoff: 1s, 2s, 4s)
- **SSL certificate handling** (certifi for portable SSL verification)
- **Rate limiting respect**
- **Error handling**

```python
class BaseAPIClient:
    """Base class for API clients with retry logic, rate limiting."""

    async def _request(self, method: str, endpoint: str, params: dict = None):
        """Make HTTP request with exponential backoff retry."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                async with session.request(method, url, params=params) as response:
                    response.raise_for_status()
                    return await response.json()

            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    raise

                # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(2 ** attempt)
```

---

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/sipap_batch_scraper --cov-report=term-missing

# Run specific test module
pytest tests/unit/apis/test_football_data.py

# Test all API integrations (REAL APIs)
python test_api_integration.py
```

### Quality Gates

Before marking any component complete, ALL must pass:

#### 1. Tests ✅
```bash
pytest --cov=src/sipap_batch_scraper --cov-report=term-missing
# Required: 80%+ coverage, all tests passing
```

#### 2. Type Checking ✅
```bash
mypy src/sipap_batch_scraper --strict
# Required: Zero errors
```

#### 3. Linting ✅
```bash
ruff check src/sipap_batch_scraper tests/
# Required: Zero errors
```

#### 4. Import Verification ✅
```bash
python -c "from sipap_batch_scraper.apis import *"
# Required: All imports successful
```

---

## Deployment

### Docker Build

```bash
# Build Fargate container image
docker build -t sipap-batch-scraper:latest .

# Run locally
docker run -e FOOTBALL_DATA_KEY=$FOOTBALL_DATA_KEY \
           -e ODDS_API_KEY=$ODDS_API_KEY \
           -e DATABASE_URL=$DATABASE_URL \
           -e REDIS_URL=$REDIS_URL \
           sipap-batch-scraper:latest
```

### AWS Deployment

**Daily Harvest (Fargate):**

```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REGISTRY
docker tag sipap-batch-scraper:latest $ECR_REGISTRY/sipap-batch-scraper:latest
docker push $ECR_REGISTRY/sipap-batch-scraper:latest

# Deploy ECS task
aws ecs run-task \
  --cluster sipap-dev \
  --task-definition sipap-batch-scraper \
  --launch-type FARGATE
```

**Scheduled via EventBridge:**

```json
{
  "schedule": "cron(0 0 * * ? *)",
  "target": {
    "arn": "arn:aws:ecs:us-east-1:xxx:cluster/sipap-dev",
    "ecsParameters": {
      "taskDefinitionArn": "arn:aws:ecs:us-east-1:xxx:task-definition/sipap-batch-scraper"
    }
  }
}
```

---

## Cost Breakdown

### API-Based Architecture (Current - v2.3)

| Component | Cost/Month |
|-----------|------------|
| **API Costs** | |
| └─ Football-Data.org | $0 (FREE forever) |
| └─ The Odds API | $0 (FREE 500 credits/month) |
| └─ TheSportsDB | $0 (FREE 30 req/min) |
| **Infrastructure Costs** | |
| └─ Fargate Daily Harvest (3 min/day) | $0.05 |
| └─ Lambda Odds Updater (48 runs/day) | $1.20 |
| └─ Lambda Fixture Updater (24 runs/day) | $0.15 |
| **Total Data Collection** | **$1.40/month** |

### Web Scraping (Previous - REJECTED)

| Component | Cost/Month |
|-----------|------------|
| Fargate batch scraper (daily) | $6 |
| Lambda hourly updates | $15 |
| Lambda live tracker | $3 |
| Playwright layers | $5 |
| **Total Web Scraping** | **$29/month** |

**Savings:** $27.60/month (95% cost reduction for data collection) 🎉

---

## Monitoring

### CloudWatch Metrics

- `api.success_rate` - API success rate (target: >95%)
- `api.fixtures_fetched` - Total fixtures fetched
- `api.duration_ms` - API request duration
- `api.credits_used` - API credits consumed (The Odds API)
- `api.error_count` - Error count

### CloudWatch Logs

- `/aws/ecs/sipap-batch-scraper` - Fargate logs
- `/aws/lambda/sipap-odds-updater` - Odds updater logs
- `/aws/lambda/sipap-fixture-updater` - Fixture updater logs

---

## Rate Limiting & API Management

### Request Budgets

| API | Rate Limit | Daily Budget | Strategy |
|-----|------------|--------------|----------|
| Football-Data.org | 10 req/min | ~14,400 req/day | Batch requests, avoid polling |
| The Odds API | 500 credits/month | ~48 req/day | Cache with 30-minute TTL |
| TheSportsDB | 30 req/min | ~43,200 req/day | Batch team/player lookups |

### Caching Strategy

| Data Type | Cache TTL | Update Frequency | Rationale |
|-----------|-----------|------------------|-----------|
| **Match fixtures** | 6 hours | Daily | Refreshed with daily harvest |
| **Betting odds** | 30 minutes | Every 30 minutes | Odds change frequently |
| **Team stats** | 24 hours | Daily | Stable data, low volatility |
| **League standings** | 6 hours | Hourly | Updated after matches |
| **Team metadata** | 7 days | Daily | Rarely changes (badges, info) |
| **Player info** | 7 days | Daily | Stable unless transfers |

---

## Troubleshooting

### Common Issues

**1. API Rate Limit Exceeded**

```python
# Check API credits usage (The Odds API)
response = await odds_api.get_odds(sport='soccer_epl')
print(f"Remaining credits: {response.headers.get('x-requests-remaining')}")

# Increase cache TTL to reduce API calls
await redis_client.setex('fixtures', 21600, data)  # 6 hours
```

**2. API Key Invalid**

```python
# Verify API keys are loaded correctly
print(f"Football-Data.org key: {FOOTBALL_DATA_KEY[:10]}...")
print(f"The Odds API key: {ODDS_API_KEY[:10]}...")

# Check environment variables
import os
print(os.getenv('FOOTBALL_DATA_KEY'))
```

**3. SSL Certificate Verification Failed**

```python
# Ensure certifi is installed and used
import certifi
import ssl

ssl_context = ssl.create_default_context(cafile=certifi.where())
```

---

## References

- **Architecture:** `AI-Odi/sentinel/sipap/technical-architecture-v2.md` Section 2.6
- **API Integration Tests:** `test_api_integration.py` (this repository)
- **Documentation Update Plan:** `AI-Odi/sentinel/sipap/DOCUMENTATION-UPDATE-PLAN.md`

---

**Version:** 0.2.0 (API-Based Architecture v2.3)
**Last Updated:** 2026-06-28
**Status:** In Development (Phase 2 - API Integration)
**Architecture:** Pivoted from web scraping to professional APIs (2026-06-28)
