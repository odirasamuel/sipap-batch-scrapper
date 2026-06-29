"""
Aurora PostgreSQL database client for batch scraper.

Handles database operations for storing scraped sports data.
"""

from datetime import UTC, datetime
from typing import Any

import asyncpg  # type: ignore[import-untyped]


class AuroraClient:
    """
    Aurora PostgreSQL client for batch scraper.

    Features:
    - Async connection pooling
    - Batch insert operations
    - Upsert support (ON CONFLICT DO UPDATE)
    - Transaction management
    - Proper resource cleanup

    Example:
        >>> client = AuroraClient(
        ...     host="sipap-dev-aurora.cluster-xxx.us-east-1.rds.amazonaws.com",
        ...     port=5432,
        ...     database="sipap_dev",
        ...     user="sipap_admin",
        ...     password="password"
        ... )
        >>> await client.connect()
        >>> await client.insert_match({...})
        >>> await client.close()
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_pool_size: int = 5,
        max_pool_size: int = 20
    ) -> None:
        """
        Initialize Aurora client.

        Args:
            host: Aurora cluster endpoint
            port: Database port (default 5432)
            database: Database name
            user: Database user
            password: Database password
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size
            )

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def insert_match(self, match_data: dict[str, Any]) -> None:
        """
        Insert match data.

        Args:
            match_data: Match data dictionary with keys:
                - external_id: External match ID from source
                - home_team: Home team name
                - away_team: Away team name
                - scheduled_at: Match scheduled time (ISO 8601)
                - league: League name
                - source: Data source (flashscore, futbol24, espn)
        """
        assert self._pool is not None, "Must call connect() before insert_match()"
        query = """
            INSERT INTO matches (
                external_id, home_team, away_team, scheduled_at,
                league, source, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                match_data['external_id'],
                match_data['home_team'],
                match_data['away_team'],
                match_data['scheduled_at'],
                match_data['league'],
                match_data['source'],
                datetime.now(UTC)
            )

    async def upsert_match(self, match_data: dict[str, Any]) -> None:
        """
        Upsert match data (insert or update if exists).

        Args:
            match_data: Match data dictionary
        """
        assert self._pool is not None, "Must call connect() before upsert_match()"
        query = """
            INSERT INTO matches (
                external_id, home_team, away_team, scheduled_at,
                league, source, status, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (external_id, source)
            DO UPDATE SET
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team,
                scheduled_at = EXCLUDED.scheduled_at,
                league = EXCLUDED.league,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
        """
        now = datetime.now(UTC)
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                match_data['external_id'],
                match_data['home_team'],
                match_data['away_team'],
                match_data['scheduled_at'],
                match_data['league'],
                match_data['source'],
                match_data.get('status', 'scheduled'),
                now,
                now
            )

    async def batch_insert_matches(self, matches: list[dict[str, Any]]) -> None:
        """
        Batch insert multiple matches.

        Args:
            matches: List of match data dictionaries

        Example:
            >>> await client.batch_insert_matches([
            ...     {'external_id': '1', 'home_team': 'Arsenal', ...},
            ...     {'external_id': '2', 'home_team': 'Liverpool', ...}
            ... ])
        """
        assert self._pool is not None, "Must call connect() before batch_insert_matches()"
        query = """
            INSERT INTO matches (
                external_id, home_team, away_team, scheduled_at,
                league, source, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (external_id, source) DO NOTHING
        """
        now = datetime.now(UTC)
        records = [
            (
                m['external_id'],
                m['home_team'],
                m['away_team'],
                m['scheduled_at'],
                m['league'],
                m['source'],
                now
            )
            for m in matches
        ]

        async with self._pool.acquire() as conn:
            await conn.executemany(query, records)

    async def insert_team_stats(self, team_stats: dict[str, Any]) -> None:
        """
        Insert or update team statistics.

        Args:
            team_stats: Team statistics dictionary with keys:
                - team_id: Team identifier
                - season: Season (e.g., "2024-2025")
                - matches_played: Number of matches played
                - wins, draws, losses: Match results
                - goals_scored, goals_conceded: Goal statistics
        """
        assert self._pool is not None, "Must call connect() before insert_team_stats()"
        query = """
            INSERT INTO team_stats (
                team_id, season, matches_played, wins, draws, losses,
                goals_scored, goals_conceded, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (team_id, season)
            DO UPDATE SET
                matches_played = EXCLUDED.matches_played,
                wins = EXCLUDED.wins,
                draws = EXCLUDED.draws,
                losses = EXCLUDED.losses,
                goals_scored = EXCLUDED.goals_scored,
                goals_conceded = EXCLUDED.goals_conceded,
                updated_at = EXCLUDED.updated_at
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                team_stats['team_id'],
                team_stats['season'],
                team_stats['matches_played'],
                team_stats['wins'],
                team_stats['draws'],
                team_stats['losses'],
                team_stats['goals_scored'],
                team_stats['goals_conceded'],
                datetime.now(UTC)
            )

    async def query_matches(
        self,
        date: str | None = None,
        league: str | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Query matches from database.

        Args:
            date: Filter by date (YYYY-MM-DD)
            league: Filter by league name
            limit: Maximum number of results

        Returns:
            List of match dictionaries
        """
        assert self._pool is not None, "Must call connect() before query_matches()"
        query = "SELECT * FROM matches WHERE 1=1"
        params: list[Any] = []

        if date:
            query += " AND DATE(scheduled_at) = $1"
            params.append(date)

        if league:
            param_num = len(params) + 1
            query += f" AND league = ${param_num}"
            params.append(league)

        query += f" LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def query_team_stats(
        self,
        team_id: str,
        season: str
    ) -> dict[str, Any] | None:
        """
        Query team statistics.

        Args:
            team_id: Team identifier
            season: Season string

        Returns:
            Team statistics dictionary or None if not found
        """
        assert self._pool is not None, "Must call connect() before query_team_stats()"
        query = """
            SELECT * FROM team_stats
            WHERE team_id = $1 AND season = $2
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, team_id, season)
            return dict(row) if row else None

    async def update_match_odds(
        self,
        external_id: str,
        sport_id: int,
        bookmakers: list[dict[str, Any]],
        best_odds: dict[str, Any] | None = None
    ) -> None:
        """
        Update betting odds for a match.

        Stores odds data in the matches.metadata JSONB field under the 'odds' key.

        Args:
            external_id: External match ID from API
            sport_id: Sport ID (1=soccer, 2=basketball, etc.)
            bookmakers: List of bookmaker odds data
            best_odds: Optional best odds summary (home, draw, away)

        Example:
            >>> await client.update_match_odds(
            ...     external_id="abc123",
            ...     sport_id=1,
            ...     bookmakers=[
            ...         {'name': 'bet365', 'home': 1.50, 'draw': 4.00, 'away': 6.00},
            ...         {'name': 'william_hill', 'home': 1.55, 'draw': 3.90, 'away': 5.80}
            ...     ],
            ...     best_odds={'home': 1.55, 'draw': 4.00, 'away': 6.00}
            ... )
        """
        assert self._pool is not None, "Must call connect() before update_match_odds()"

        odds_data = {
            'bookmakers': bookmakers,
            'best_odds': best_odds or {},
            'updated_at': datetime.now(UTC).isoformat()
        }

        query = """
            UPDATE matches
            SET metadata = jsonb_set(
                COALESCE(metadata, '{}'::jsonb),
                '{odds}',
                $1::jsonb
            )
            WHERE external_id = $2 AND sport_id = $3
        """

        import json
        async with self._pool.acquire() as conn:
            await conn.execute(query, json.dumps(odds_data), external_id, sport_id)

    async def update_fixtures(self, fixtures: list[dict[str, Any]]) -> None:
        """
        Update multiple fixture records.

        Updates match status, scores, venue, and other fixture data.

        Args:
            fixtures: List of fixture dictionaries with keys:
                - external_id: External match ID (required)
                - sport_id: Sport ID (required)
                - status: Match status (optional: 'scheduled', 'live', 'finished')
                - home_score: Home team score (optional)
                - away_score: Away team score (optional)
                - venue: Match venue (optional)
                - scheduled_at: Match time (optional)

        Example:
            >>> await client.update_fixtures([
            ...     {
            ...         'external_id': 'abc123',
            ...         'sport_id': 1,
            ...         'status': 'live',
            ...         'home_score': 2,
            ...         'away_score': 1
            ...     }
            ... ])
        """
        assert self._pool is not None, "Must call connect() before update_fixtures()"

        for fixture in fixtures:
            external_id = fixture.get('external_id')
            sport_id = fixture.get('sport_id')

            if not external_id or not sport_id:
                continue

            # Build dynamic update query based on provided fields
            update_fields = []
            params = []
            param_count = 1

            if 'status' in fixture:
                update_fields.append(f"status = ${param_count}")
                params.append(fixture['status'])
                param_count += 1

            if 'home_score' in fixture:
                update_fields.append(f"home_score = ${param_count}")
                params.append(fixture['home_score'])
                param_count += 1

            if 'away_score' in fixture:
                update_fields.append(f"away_score = ${param_count}")
                params.append(fixture['away_score'])
                param_count += 1

            if 'venue' in fixture:
                update_fields.append(f"venue = ${param_count}")
                params.append(fixture['venue'])
                param_count += 1

            if 'scheduled_at' in fixture:
                update_fields.append(f"scheduled_at = ${param_count}")
                params.append(fixture['scheduled_at'])
                param_count += 1

            if not update_fields:
                continue  # Nothing to update for this fixture

            # Add WHERE clause parameters
            params.extend([external_id, sport_id])

            query = f"""
                UPDATE matches
                SET {', '.join(update_fields)}
                WHERE external_id = ${param_count} AND sport_id = ${param_count + 1}
            """

            async with self._pool.acquire() as conn:
                await conn.execute(query, *params)

    async def update_standings(self, standings: list[dict[str, Any]]) -> None:
        """
        Update league standings data.

        Since there's no dedicated standings table, this stores standings
        in the league metadata JSONB field.

        Note: For MVP, league_id can be a competition code (PL, CL, etc.) or UUID.
        If leagues table doesn't exist or league not found, operation is skipped.
        Standings are primarily cached in Redis.

        Args:
            standings: List of standings data with keys:
                - league_id: League identifier (UUID or competition code)
                - season: Season string (e.g., "2024-2025")
                - table: List of team standings with position, points, wins, etc.

        Example:
            >>> await client.update_standings([
            ...     {
            ...         'league_id': 'PL',  # Competition code
            ...         'season': '2024-2025',
            ...         'table': [
            ...             {'position': 1, 'team': 'Arsenal', 'points': 50, ...},
            ...             {'position': 2, 'team': 'Man City', 'points': 48, ...}
            ...         ]
            ...     }
            ... ])
        """
        assert self._pool is not None, "Must call connect() before update_standings()"

        import json

        for standing in standings:
            league_id = standing.get('league_id')
            season = standing.get('season', '2024-2025')
            table_data = standing.get('table', [])

            if not league_id or not table_data:
                continue

            standings_data = {
                'season': season,
                'table': table_data,
                'updated_at': datetime.now(UTC).isoformat()
            }

            # Try to update leagues table by UUID
            # If league doesn't exist or leagues table doesn't exist, skip
            # Standings are primarily cached in Redis anyway
            query = """
                UPDATE leagues
                SET metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{standings}',
                    $1::jsonb
                )
                WHERE id = $2
            """

            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(query, json.dumps(standings_data), league_id)
            except Exception:
                # League doesn't exist or table doesn't exist - skip Aurora update
                # Standings are cached in Redis which is the primary read path
                pass
