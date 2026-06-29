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

    async def _get_or_create_sport(self, sport_name: str) -> int:
        """Get sport ID, creating if it doesn't exist."""
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            # Try to get existing sport
            result = await conn.fetchrow(
                "SELECT id FROM sports WHERE name = $1",
                sport_name
            )

            if result:
                return int(result['id'])

            # Create new sport
            result = await conn.fetchrow(
                """
                INSERT INTO sports (name, display_name, enabled)
                VALUES ($1, $2, true)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                sport_name,
                sport_name.replace('_', ' ').title()
            )
            assert result is not None
            return int(result['id'])

    async def _get_or_create_team(
        self,
        sport_id: int,
        team_name: str,
        external_id: str | None = None
    ) -> str:
        """Get team UUID, creating if it doesn't exist."""
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            # Try to find by external_id if provided
            if external_id:
                result = await conn.fetchrow(
                    "SELECT id FROM teams WHERE sport_id = $1 AND external_id = $2",
                    sport_id,
                    external_id
                )
                if result:
                    return str(result['id'])

            # Try to find by name
            result = await conn.fetchrow(
                "SELECT id FROM teams WHERE sport_id = $1 AND name = $2",
                sport_id,
                team_name
            )

            if result:
                return str(result['id'])

            # Create new team
            result = await conn.fetchrow(
                """
                INSERT INTO teams (sport_id, external_id, name, short_name)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                sport_id,
                external_id,
                team_name,
                team_name[:50] if team_name else None
            )
            return str(result['id'])

    async def _get_or_create_league(
        self,
        sport_id: int,
        league_name: str,
        external_id: str | None = None
    ) -> str:
        """Get league UUID, creating if it doesn't exist."""
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            # Try to find by external_id if provided
            if external_id:
                result = await conn.fetchrow(
                    "SELECT id FROM leagues WHERE sport_id = $1 AND external_id = $2",
                    sport_id,
                    external_id
                )
                if result:
                    return str(result['id'])

            # Try to find by name
            result = await conn.fetchrow(
                "SELECT id FROM leagues WHERE sport_id = $1 AND name = $2",
                sport_id,
                league_name
            )

            if result:
                return str(result['id'])

            # Create new league
            result = await conn.fetchrow(
                """
                INSERT INTO leagues (sport_id, external_id, name, enabled)
                VALUES ($1, $2, $3, true)
                RETURNING id
                """,
                sport_id,
                external_id,
                league_name
            )
            return str(result['id'])

    async def batch_insert_matches(self, matches: list[dict[str, Any]]) -> None:
        """
        Batch insert multiple matches with proper foreign key lookups.

        This method works with the normalized schema by:
        1. Ensuring sport exists (defaults to 'soccer')
        2. Looking up or creating teams
        3. Looking up or creating leagues
        4. Inserting matches with foreign key references

        Args:
            matches: List of match data dictionaries with keys:
                - external_id: External match ID from source
                - home_team: Home team name
                - away_team: Away team name
                - scheduled_at: Match scheduled time
                - league: League name
                - source: Data source (football-data.org, thesportsdb, etc.)
                - sport: Sport name (optional, defaults to 'soccer')

        Example:
            >>> await client.batch_insert_matches([
            ...     {
            ...         'external_id': '12345',
            ...         'home_team': 'Arsenal',
            ...         'away_team': 'Liverpool',
            ...         'scheduled_at': '2024-01-15T15:00:00Z',
            ...         'league': 'Premier League',
            ...         'source': 'football-data.org',
            ...         'sport': 'soccer'
            ...     }
            ... ])
        """
        assert self._pool is not None, "Must call connect() before batch_insert_matches()"

        if not matches:
            return

        # Get or create sport (default to soccer for sports data)
        sport_id = await self._get_or_create_sport('soccer')

        # Process each match to resolve foreign keys
        match_records = []
        for match in matches:
            # Get or create teams
            home_team_id = await self._get_or_create_team(
                sport_id,
                match['home_team'],
                match.get('home_team_id')
            )

            away_team_id = await self._get_or_create_team(
                sport_id,
                match['away_team'],
                match.get('away_team_id')
            )

            # Get or create league
            league_id = await self._get_or_create_league(
                sport_id,
                match['league'],
                match.get('league_id')
            )

            match_records.append((
                sport_id,
                league_id,
                match['external_id'],
                home_team_id,
                away_team_id,
                match['scheduled_at'],
                match.get('status', 'scheduled'),
                match.get('home_score'),
                match.get('away_score'),
                match.get('venue'),
                datetime.now(UTC)
            ))

        # Batch insert all matches
        query = """
            INSERT INTO matches (
                sport_id, league_id, external_id,
                home_team_id, away_team_id, scheduled_at,
                status, home_score, away_score, venue, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (sport_id, external_id) DO NOTHING
        """

        async with self._pool.acquire() as conn:
            await conn.executemany(query, match_records)

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
