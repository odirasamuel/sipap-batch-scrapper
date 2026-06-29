"""
Database query utility - check what data is stored in Aurora.

This Lambda function queries the Aurora database to show:
- Total matches, teams, leagues
- Breakdown by sport, league, team
- Recent matches
- Matches with odds data
"""

import asyncio
import json
import os
from typing import Any

from sipap_batch_scraper.storage import AuroraClient
from sipap_batch_scraper.util import get_secret


async def query_database(aurora_config: dict[str, Any]) -> dict[str, Any]:
    """Query database and return statistics."""

    client = AuroraClient(**aurora_config)
    await client.connect()

    try:
        pool = client._pool
        assert pool is not None

        async with pool.acquire() as conn:
            # 1. Overall counts
            overall = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(DISTINCT sport_id) as sports,
                    COUNT(DISTINCT league_id) as leagues,
                    COUNT(DISTINCT home_team_id) + COUNT(DISTINCT away_team_id) as unique_teams
                FROM matches
            """)

            # 2. Sports breakdown
            sports = await conn.fetch("""
                SELECT s.name, s.display_name, COUNT(m.id) as match_count
                FROM sports s
                LEFT JOIN matches m ON m.sport_id = s.id
                GROUP BY s.id, s.name, s.display_name
                ORDER BY match_count DESC
            """)

            # 3. Top leagues
            leagues = await conn.fetch("""
                SELECT l.name, COUNT(m.id) as match_count
                FROM leagues l
                LEFT JOIN matches m ON m.league_id = l.id
                GROUP BY l.id, l.name
                ORDER BY match_count DESC
                LIMIT 10
            """)

            # 4. Top teams
            teams = await conn.fetch("""
                SELECT t.name,
                       COUNT(DISTINCT CASE WHEN m.home_team_id = t.id THEN m.id END) as home_matches,
                       COUNT(DISTINCT CASE WHEN m.away_team_id = t.id THEN m.id END) as away_matches
                FROM teams t
                LEFT JOIN matches m ON m.home_team_id = t.id OR m.away_team_id = t.id
                GROUP BY t.id, t.name
                ORDER BY (home_matches + away_matches) DESC
                LIMIT 10
            """)

            # 5. Match status
            statuses = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM matches
                GROUP BY status
                ORDER BY count DESC
            """)

            # 6. Matches with odds
            odds_count = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE metadata->'odds' IS NOT NULL) as with_odds
                FROM matches
            """)

            # 7. Time range
            time_range = await conn.fetchrow("""
                SELECT
                    MIN(scheduled_at) as earliest,
                    MAX(scheduled_at) as latest,
                    MIN(created_at) as first_created,
                    MAX(created_at) as last_created
                FROM matches
            """)

            # 8. Recent matches
            recent = await conn.fetch("""
                SELECT
                    m.scheduled_at,
                    ht.name as home_team,
                    at.name as away_team,
                    l.name as league,
                    m.status
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                JOIN leagues l ON m.league_id = l.id
                ORDER BY m.created_at DESC
                LIMIT 5
            """)

            return {
                'overall': {
                    'total_matches': overall['total_matches'],
                    'sports': overall['sports'],
                    'leagues': overall['leagues'],
                    'unique_teams': overall['unique_teams']
                },
                'sports': [
                    {'name': row['display_name'], 'matches': row['match_count']}
                    for row in sports
                ],
                'top_leagues': [
                    {'name': row['name'], 'matches': row['match_count']}
                    for row in leagues
                ],
                'top_teams': [
                    {
                        'name': row['name'],
                        'home': row['home_matches'],
                        'away': row['away_matches'],
                        'total': row['home_matches'] + row['away_matches']
                    }
                    for row in teams
                ],
                'statuses': [
                    {'status': row['status'], 'count': row['count']}
                    for row in statuses
                ],
                'with_odds': odds_count['with_odds'],
                'time_range': {
                    'earliest_match': time_range['earliest'].isoformat() if time_range['earliest'] else None,
                    'latest_match': time_range['latest'].isoformat() if time_range['latest'] else None,
                    'first_created': time_range['first_created'].isoformat() if time_range['first_created'] else None,
                    'last_created': time_range['last_created'].isoformat() if time_range['last_created'] else None
                },
                'recent_matches': [
                    {
                        'scheduled': row['scheduled_at'].isoformat(),
                        'home': row['home_team'],
                        'away': row['away_team'],
                        'league': row['league'],
                        'status': row['status']
                    }
                    for row in recent
                ]
            }

    finally:
        await client.close()


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for database query."""

    # Get environment
    env = os.getenv('ENVIRONMENT', 'dev')

    # Fetch database credentials from Secrets Manager
    db_creds = get_secret(f'sipap/{env}/aurora-credentials')

    aurora_config = {
        'host': db_creds['host'],
        'port': int(db_creds['port']),
        'database': db_creds['database'],
        'user': db_creds['username'],
        'password': db_creds['password'],
    }

    # Run query
    result = asyncio.run(query_database(aurora_config))

    # Pretty print results
    print("=" * 80)
    print("DATABASE QUERY RESULTS")
    print("=" * 80)
    print()

    print("OVERALL:")
    print(f"  Total Matches: {result['overall']['total_matches']}")
    print(f"  Sports: {result['overall']['sports']}")
    print(f"  Leagues: {result['overall']['leagues']}")
    print(f"  Unique Teams: {result['overall']['unique_teams']}")
    print()

    print("SPORTS:")
    for sport in result['sports']:
        print(f"  {sport['name']}: {sport['matches']} matches")
    print()

    print("TOP LEAGUES:")
    for league in result['top_leagues']:
        print(f"  {league['name']}: {league['matches']} matches")
    print()

    print("TOP TEAMS:")
    for team in result['top_teams']:
        print(f"  {team['name']}: {team['total']} matches ({team['home']} home, {team['away']} away)")
    print()

    print(f"MATCHES WITH ODDS: {result['with_odds']}")
    print()

    print("RECENT MATCHES:")
    for match in result['recent_matches']:
        print(f"  {match['scheduled']} | {match['home']} vs {match['away']} | {match['league']} | {match['status']}")
    print()

    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }


if __name__ == '__main__':
    # For local testing
    asyncio.run(query_database({
        'host': os.getenv('AURORA_HOST', 'localhost'),
        'port': int(os.getenv('AURORA_PORT', '5432')),
        'database': os.getenv('AURORA_DATABASE', 'sipap_dev'),
        'user': os.getenv('AURORA_USER', 'sipap_admin'),
        'password': os.getenv('AURORA_PASSWORD', ''),
    }))
