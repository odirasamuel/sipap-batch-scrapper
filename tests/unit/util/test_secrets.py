"""
Tests for AWS Secrets Manager integration utilities.

Tests the secure retrieval of API keys and database credentials from
AWS Secrets Manager for batch scraper jobs.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from sipap_batch_scraper.util.secrets import (
    get_api_keys,
    get_api_keys_with_fallback,
    get_db_credentials,
    get_secret,
)


class TestGetSecret:
    """Test get_secret() function."""

    @patch('boto3.session.Session')
    def test_get_secret_success(self, mock_session_class: MagicMock) -> None:
        """Test successful secret retrieval."""
        # Mock Secrets Manager response
        mock_sm_client = MagicMock()
        mock_sm_client.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'API_KEY_1': 'value1',
                'API_KEY_2': 'value2',
            })
        }

        # Mock session instance that returns the client
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm_client
        mock_session_class.return_value = mock_session

        result = get_secret('test-secret')

        assert result == {'API_KEY_1': 'value1', 'API_KEY_2': 'value2'}
        mock_sm_client.get_secret_value.assert_called_once_with(SecretId='test-secret')

    @patch('boto3.session.Session')
    def test_get_secret_decryption_failure(self, mock_session_class: MagicMock) -> None:
        """Test handling of decryption failure."""
        # Mock Secrets Manager decryption error
        mock_sm_client = MagicMock()
        mock_sm_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'DecryptionFailureException', 'Message': 'KMS error'}},
            'GetSecretValue'
        )

        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm_client
        mock_session_class.return_value = mock_session

        with pytest.raises(RuntimeError, match='Cannot decrypt secret'):
            get_secret('test-secret')

    @patch('boto3.session.Session')
    def test_get_secret_not_found(self, mock_session_class: MagicMock) -> None:
        """Test handling of secret not found error."""
        # Mock Secrets Manager not found error
        mock_sm_client = MagicMock()
        mock_sm_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Secret not found'}},
            'GetSecretValue'
        )

        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm_client
        mock_session_class.return_value = mock_session

        with pytest.raises(ValueError, match="Secret 'test-secret' not found"):
            get_secret('test-secret')

    @patch('boto3.session.Session')
    def test_get_secret_with_custom_region(self, mock_session_class: MagicMock) -> None:
        """Test secret retrieval with custom AWS region."""
        # Mock Secrets Manager response
        mock_sm_client = MagicMock()
        mock_sm_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'KEY': 'value'})
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm_client
        mock_session_class.return_value = mock_session

        get_secret('test-secret', region_name='us-west-2')

        # Verify session.client was created with correct region
        mock_session.client.assert_called_once_with(
            service_name='secretsmanager',
            region_name='us-west-2'
        )


class TestGetApiKeys:
    """Test get_api_keys() function."""

    @patch('sipap_batch_scraper.util.secrets.get_secret')
    def test_get_api_keys_dev(self, mock_get_secret: MagicMock) -> None:
        """Test retrieving API keys for dev environment."""
        mock_get_secret.return_value = {
            'FOOTBALL_DATA_KEY': 'fd_key_dev',
            'ODDS_API_KEY': 'odds_key_dev',
            'THESPORTSDB_KEY': '123',
        }

        result = get_api_keys(env='dev')

        assert result == {
            'FOOTBALL_DATA_KEY': 'fd_key_dev',
            'ODDS_API_KEY': 'odds_key_dev',
            'THESPORTSDB_KEY': '123',
        }
        mock_get_secret.assert_called_once_with('sipap/dev/api-keys', 'us-east-1')

    @patch('sipap_batch_scraper.util.secrets.get_secret')
    def test_get_api_keys_staging(self, mock_get_secret: MagicMock) -> None:
        """Test retrieving API keys for staging environment."""
        mock_get_secret.return_value = {
            'FOOTBALL_DATA_KEY': 'fd_key_staging',
            'ODDS_API_KEY': 'odds_key_staging',
            'THESPORTSDB_KEY': '123',
        }

        result = get_api_keys(env='staging')

        assert result == {
            'FOOTBALL_DATA_KEY': 'fd_key_staging',
            'ODDS_API_KEY': 'odds_key_staging',
            'THESPORTSDB_KEY': '123',
        }
        mock_get_secret.assert_called_once_with('sipap/staging/api-keys', 'us-east-1')

    @patch('sipap_batch_scraper.util.secrets.get_secret')
    def test_get_api_keys_prod(self, mock_get_secret: MagicMock) -> None:
        """Test retrieving API keys for prod environment."""
        mock_get_secret.return_value = {
            'FOOTBALL_DATA_KEY': 'fd_key_prod',
            'ODDS_API_KEY': 'odds_key_prod',
            'THESPORTSDB_KEY': '123',
        }

        result = get_api_keys(env='prod')

        assert result == {
            'FOOTBALL_DATA_KEY': 'fd_key_prod',
            'ODDS_API_KEY': 'odds_key_prod',
            'THESPORTSDB_KEY': '123',
        }
        mock_get_secret.assert_called_once_with('sipap/prod/api-keys', 'us-east-1')


class TestGetDbCredentials:
    """Test get_db_credentials() function."""

    @patch('sipap_batch_scraper.util.secrets.get_secret')
    def test_get_db_credentials_dev(self, mock_get_secret: MagicMock) -> None:
        """Test retrieving database credentials for dev environment."""
        mock_get_secret.return_value = {
            'username': 'sipap_admin',
            'password': 'dev_password',
            'host': 'sipap-dev-cluster.cluster-xxxxx.us-east-1.rds.amazonaws.com',
            'port': '5432',
            'database': 'sipap_dev',
        }

        result = get_db_credentials(env='dev')

        assert result == {
            'username': 'sipap_admin',
            'password': 'dev_password',
            'host': 'sipap-dev-cluster.cluster-xxxxx.us-east-1.rds.amazonaws.com',
            'port': '5432',
            'database': 'sipap_dev',
        }
        mock_get_secret.assert_called_once_with('sipap/dev/aurora-credentials', 'us-east-1')

    @patch('sipap_batch_scraper.util.secrets.get_secret')
    def test_get_db_credentials_with_custom_region(
        self, mock_get_secret: MagicMock
    ) -> None:
        """Test retrieving database credentials with custom region."""
        mock_get_secret.return_value = {
            'username': 'sipap_admin',
            'password': 'password',
            'host': 'localhost',
            'port': '5432',
            'database': 'sipap_dev',
        }

        get_db_credentials(env='dev', region_name='eu-west-1')

        mock_get_secret.assert_called_once_with('sipap/dev/aurora-credentials', 'eu-west-1')


class TestGetApiKeysWithFallback:
    """Test get_api_keys_with_fallback() function."""

    @patch('sipap_batch_scraper.util.secrets.get_api_keys')
    @patch('os.getenv')
    def test_uses_secrets_manager_in_aws(
        self, mock_getenv: MagicMock, mock_get_api_keys: MagicMock
    ) -> None:
        """Test using Secrets Manager when running in AWS."""
        # Simulate AWS environment
        mock_getenv.side_effect = lambda key, default=None: {
            'AWS_EXECUTION_ENV': 'AWS_ECS_FARGATE',
        }.get(key, default)

        mock_get_api_keys.return_value = {
            'FOOTBALL_DATA_KEY': 'fd_key_from_sm',
            'ODDS_API_KEY': 'odds_key_from_sm',
            'THESPORTSDB_KEY': '123',
        }

        result = get_api_keys_with_fallback(env='dev')

        assert result == {
            'FOOTBALL_DATA_KEY': 'fd_key_from_sm',
            'ODDS_API_KEY': 'odds_key_from_sm',
            'THESPORTSDB_KEY': '123',
        }
        mock_get_api_keys.assert_called_once_with(env='dev')

    @patch('sipap_batch_scraper.util.secrets.get_api_keys')
    @patch('os.getenv')
    def test_uses_env_vars_locally(
        self, mock_getenv: MagicMock, mock_get_api_keys: MagicMock
    ) -> None:
        """Test using environment variables when running locally."""
        # Simulate local environment (AWS env vars return None, not empty strings)
        def getenv_side_effect(key: str, default: str = '') -> str | None:
            env_vars: dict[str, str | None] = {
                'AWS_EXECUTION_ENV': None,  # Not in AWS
                'ECS_CONTAINER_METADATA_URI': None,  # Not in ECS
                'FOOTBALL_DATA_KEY': 'fd_key_local',
                'ODDS_API_KEY': 'odds_key_local',
                'THESPORTSDB_KEY': '123',
            }
            # Return None if key not found and that's what env_vars has, otherwise use default
            if key in env_vars:
                return env_vars[key]
            return default

        mock_getenv.side_effect = getenv_side_effect

        result = get_api_keys_with_fallback(env='dev')

        assert result == {
            'FOOTBALL_DATA_KEY': 'fd_key_local',
            'ODDS_API_KEY': 'odds_key_local',
            'THESPORTSDB_KEY': '123',
        }
        # Secrets Manager should NOT be called when running locally
        mock_get_api_keys.assert_not_called()

    @patch('sipap_batch_scraper.util.secrets.get_api_keys')
    @patch('os.getenv')
    def test_detects_ecs_fargate_environment(
        self, mock_getenv: MagicMock, mock_get_api_keys: MagicMock
    ) -> None:
        """Test detection of ECS Fargate environment."""
        # Simulate ECS Fargate environment
        mock_getenv.side_effect = lambda key, default=None: {
            'ECS_CONTAINER_METADATA_URI': 'http://169.254.170.2/v3/containers/...',
        }.get(key, default)

        mock_get_api_keys.return_value = {
            'FOOTBALL_DATA_KEY': 'fd_key_from_sm',
            'ODDS_API_KEY': 'odds_key_from_sm',
            'THESPORTSDB_KEY': '123',
        }

        get_api_keys_with_fallback(env='dev')

        # Should use Secrets Manager in ECS Fargate
        mock_get_api_keys.assert_called_once_with(env='dev')
