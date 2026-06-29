# SIPAP Batch Scraper Examples

This directory contains working examples demonstrating the usage of sipap-batch-scraper components.

## Examples

### 1. Base Scraper (`example_base_scraper.py`)

Demonstrates web scraping with Playwright + stealth mode:
- HTML content extraction
- Anti-detection features (stealth mode, user-agent rotation)
- Random delays for human-like behavior
- Proper resource cleanup

**Run:**
```bash
# Install Playwright browsers first
playwright install chromium

# Run example
python examples/example_base_scraper.py
```

### 2. Aurora Client (`example_aurora_client.py`)

Demonstrates Aurora PostgreSQL database operations:
- Connection pooling
- Inserting match data
- Upserting (insert or update on conflict)
- Batch inserts for performance
- Querying matches by date/league
- Team statistics storage

**Run:**
```bash
# Set environment variables
export AURORA_HOST=localhost
export AURORA_PORT=5432
export AURORA_DATABASE=sipap_dev
export AURORA_USER=sipap_admin
export AURORA_PASSWORD=password

# Or use Docker
docker-compose up postgres

# Run example
python examples/example_aurora_client.py
```

### 3. Redis Client (`example_redis_client.py`)

Demonstrates Redis caching operations:
- Connecting to Redis/ElastiCache
- Setting keys with TTL (time-to-live)
- Getting cached data
- JSON serialization/deserialization
- Batch set/get operations
- Key pattern searching
- Incrementing counters

**Run:**
```bash
# Set environment variables
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Or use Docker
docker-compose up redis

# Run example
python examples/example_redis_client.py
```

### 4. Daily Harvest Job (`example_daily_harvest.py`) ⭐ NEW

Demonstrates the complete fixture harvesting pipeline from all 3 APIs:
- Orchestrates Football-Data.org, The Odds API, and TheSportsDB
- Fetches fixtures for next 7 days
- Enriches fixtures with betting odds (37 bookmakers)
- Adds team metadata (badges, venue info)
- Merges and deduplicates fixtures by (home_team, away_team, date)
- Stores in Aurora + caches in Redis (6-hour TTL)
- Full error handling and metrics logging

**Run:**
```bash
# Set environment variables
export FOOTBALL_DATA_KEY=your_api_key_here
export ODDS_API_KEY=your_api_key_here
export THESPORTSDB_KEY=123  # Free tier key
export AURORA_HOST=localhost
export AURORA_PORT=5432
export AURORA_DATABASE=sipap_dev
export AURORA_USER=sipap_admin
export AURORA_PASSWORD=password
export REDIS_URL=redis://localhost:6379

# Or use Docker for local services
docker-compose up -d postgres redis

# Run example
python examples/example_daily_harvest.py
```

**API Keys (FREE):**
- Football-Data.org: https://www.football-data.org/ (FREE forever, 10 req/min)
- The Odds API: https://the-odds-api.com/ (FREE 500 credits/month)
- TheSportsDB: https://www.thesportsdb.com/ (FREE tier, key: '123')

## Prerequisites

### Python Dependencies

All examples require the sipap-batch-scraper package to be installed:

```bash
pip install -e '.[dev]'
```

### External Services

- **Playwright:** Requires Chromium browser installed
  ```bash
  playwright install chromium
  ```

- **PostgreSQL:** Required for Aurora client example
  - Local: Install PostgreSQL or use Docker
  - AWS: Aurora Serverless v2

- **Redis:** Required for Redis client example
  - Local: Install Redis or use Docker
  - AWS: ElastiCache Redis

## Docker Compose

You can run PostgreSQL and Redis locally using Docker:

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: sipap_dev
      POSTGRES_USER: sipap_admin
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

```bash
# Start services
docker-compose up -d

# Run examples
python examples/example_aurora_client.py
python examples/example_redis_client.py
```

## Notes

- Examples are self-contained and demonstrate real usage
- Error handling is included to show failure modes
- All examples use async/await for proper asynchronous execution
- Resource cleanup is demonstrated (closing connections, pools)

## Troubleshooting

### Playwright Browser Not Found
```bash
playwright install chromium
```

### Database Connection Errors
- Ensure PostgreSQL is running
- Check connection details in environment variables
- Verify network connectivity

### Redis Connection Errors
- Ensure Redis is running
- Check REDIS_HOST and REDIS_PORT
- Verify firewall rules (port 6379)

---

**Last Updated:** 2026-06-27
