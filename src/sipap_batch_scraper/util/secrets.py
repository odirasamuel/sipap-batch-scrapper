"""
AWS Secrets Manager integration.

Provides secure retrieval of API keys and sensitive configuration
from AWS Secrets Manager.
"""

import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError


def get_secret(secret_name: str, region_name: str = 'us-east-1') -> dict[str, Any]:
    """
    Retrieve a secret from AWS Secrets Manager.

    Args:
        secret_name: Name of the secret in Secrets Manager
        region_name: AWS region where the secret is stored

    Returns:
        Dictionary containing the secret key-value pairs

    Raises:
        ClientError: If secret cannot be retrieved

    Example:
        >>> secrets = get_secret('sipap/dev/api-keys')
        >>> football_data_key = secrets['FOOTBALL_DATA_KEY']
        >>> odds_api_key = secrets['ODDS_API_KEY']
    """
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # Handle specific error codes
        error_code = e.response['Error']['Code']
        if error_code == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key
            raise RuntimeError(
                f"Cannot decrypt secret '{secret_name}'. "
                "Check KMS key permissions."
            ) from e
        elif error_code == 'InternalServiceErrorException':
            # An error occurred on the server side
            raise RuntimeError(
                f"Internal service error when retrieving secret '{secret_name}'. "
                "Retry the request."
            ) from e
        elif error_code == 'InvalidParameterException':
            # Invalid parameter provided
            raise ValueError(
                f"Invalid parameter when retrieving secret '{secret_name}'."
            ) from e
        elif error_code == 'InvalidRequestException':
            # Invalid request (e.g., secret not found)
            raise ValueError(
                f"Invalid request for secret '{secret_name}'. "
                "Verify the secret name is correct."
            ) from e
        elif error_code == 'ResourceNotFoundException':
            # Secret doesn't exist
            raise ValueError(
                f"Secret '{secret_name}' not found in Secrets Manager. "
                "Verify the secret name and region."
            ) from e
        else:
            # Generic error
            raise RuntimeError(
                f"Error retrieving secret '{secret_name}': {error_code}"
            ) from e

    # Decrypt secret value
    if 'SecretString' in get_secret_value_response:
        secret_string = get_secret_value_response['SecretString']
        return json.loads(secret_string)
    else:
        # Binary secrets not supported (API keys are string-based)
        raise ValueError(
            f"Secret '{secret_name}' is a binary secret. "
            "Only string secrets are supported."
        )


def get_api_keys(env: str = 'dev', region_name: str = 'us-east-1') -> dict[str, str]:
    """
    Retrieve all API keys for SIPAP batch scraper.

    This is a convenience wrapper around get_secret() that retrieves
    all API keys needed for the batch scraper jobs.

    Args:
        env: Environment (dev, staging, prod)
        region_name: AWS region where secrets are stored

    Returns:
        Dictionary with keys:
            - FOOTBALL_DATA_KEY: Football-Data.org API key
            - ODDS_API_KEY: The Odds API key
            - THESPORTSDB_KEY: TheSportsDB API key

    Example:
        >>> keys = get_api_keys(env='dev')
        >>> fd_key = keys['FOOTBALL_DATA_KEY']
        >>> odds_key = keys['ODDS_API_KEY']
        >>> tdb_key = keys['THESPORTSDB_KEY']
    """
    secret_name = f"sipap/{env}/api-keys"
    return get_secret(secret_name, region_name)  # type: ignore[return-value]


def get_db_credentials(env: str = 'dev', region_name: str = 'us-east-1') -> dict[str, str]:
    """
    Retrieve Aurora database credentials.

    Args:
        env: Environment (dev, staging, prod)
        region_name: AWS region where secrets are stored

    Returns:
        Dictionary with keys:
            - username: Database username
            - password: Database password
            - host: Database host
            - port: Database port
            - database: Database name

    Example:
        >>> db_creds = get_db_credentials(env='dev')
        >>> aurora_config = {
        ...     'host': db_creds['host'],
        ...     'port': int(db_creds['port']),
        ...     'database': db_creds['database'],
        ...     'user': db_creds['username'],
        ...     'password': db_creds['password'],
        ... }
    """
    secret_name = f"sipap/{env}/aurora-credentials"
    return get_secret(secret_name, region_name)  # type: ignore[return-value]


# For local development/testing: fall back to environment variables
def get_api_keys_with_fallback(env: str = 'dev') -> dict[str, str]:
    """
    Get API keys from Secrets Manager with fallback to environment variables.

    In production (AWS Lambda/Fargate), fetches from Secrets Manager.
    For local development, falls back to environment variables.

    Args:
        env: Environment (dev, staging, prod)

    Returns:
        Dictionary with API keys

    Example:
        >>> keys = get_api_keys_with_fallback(env='dev')
        >>> fd_key = keys['FOOTBALL_DATA_KEY']
    """
    # Check if running in AWS (Lambda/Fargate)
    is_aws = os.getenv('AWS_EXECUTION_ENV') is not None or os.getenv('ECS_CONTAINER_METADATA_URI') is not None

    if is_aws:
        # Running in AWS - use Secrets Manager
        return get_api_keys(env=env)
    else:
        # Running locally - use environment variables
        return {
            'FOOTBALL_DATA_KEY': os.getenv('FOOTBALL_DATA_KEY', ''),
            'ODDS_API_KEY': os.getenv('ODDS_API_KEY', ''),
            'THESPORTSDB_KEY': os.getenv('THESPORTSDB_KEY', '123'),
        }


__all__ = [
    'get_secret',
    'get_api_keys',
    'get_db_credentials',
    'get_api_keys_with_fallback',
]
