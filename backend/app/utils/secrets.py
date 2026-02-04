import os
import json
import logging

logger = logging.getLogger(__name__)


def get_secret(secret_name: str, default_env_var: str = None) -> str:
    """
    Retrieve a secret from AWS Secrets Manager, falling back to environment variables.

    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        default_env_var: Environment variable name to use as fallback

    Returns:
        The secret value

    Raises:
        ValueError: If secret cannot be found in either location
    """
    # Try AWS Secrets Manager first
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )

        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )

            # Secrets Manager returns either a string or binary
            if 'SecretString' in get_secret_value_response:
                secret = get_secret_value_response['SecretString']

                # If it's JSON, try to parse it
                try:
                    secret_dict = json.loads(secret)
                    # If the secret is stored as {"ANTHROPIC_API_KEY": "value"}
                    if default_env_var and default_env_var in secret_dict:
                        logger.info(f"Retrieved {secret_name} from AWS Secrets Manager (JSON)")
                        return secret_dict[default_env_var]
                    # If it's a simple JSON with one key, return the first value
                    elif len(secret_dict) == 1:
                        logger.info(f"Retrieved {secret_name} from AWS Secrets Manager (JSON)")
                        return list(secret_dict.values())[0]
                except json.JSONDecodeError:
                    # Not JSON, return as plain string
                    logger.info(f"Retrieved {secret_name} from AWS Secrets Manager (plain text)")
                    return secret

            logger.warning(f"Secret {secret_name} found but no SecretString available")

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.info(f"Secret {secret_name} not found in AWS Secrets Manager")
            elif error_code == 'AccessDeniedException':
                logger.warning(f"Access denied to secret {secret_name}")
            else:
                logger.warning(f"Error retrieving secret {secret_name}: {error_code}")

        except NoCredentialsError:
            logger.info("No AWS credentials found, skipping Secrets Manager")

    except ImportError:
        logger.info("boto3 not installed, skipping AWS Secrets Manager")
    except Exception as e:
        logger.warning(f"Unexpected error accessing Secrets Manager: {e}")

    # Fallback to environment variable
    if default_env_var:
        env_value = os.getenv(default_env_var)
        if env_value:
            logger.info(f"Using {default_env_var} from environment variable")
            return env_value

    # No secret found
    raise ValueError(
        f"Could not retrieve secret '{secret_name}'. "
        f"Tried: AWS Secrets Manager, environment variable '{default_env_var}'"
    )


def get_anthropic_api_key() -> str:
    """
    Get Anthropic API key from AWS Secrets Manager or environment.

    Returns:
        The API key

    Raises:
        ValueError: If API key cannot be found
    """
    return get_secret(
        secret_name='infrasketch/anthropic-api-key',
        default_env_var='ANTHROPIC_API_KEY'
    )


def get_devto_api_key() -> str:
    """
    Get Dev.to API key from AWS Secrets Manager or environment.

    Returns:
        The API key

    Raises:
        ValueError: If API key cannot be found
    """
    return get_secret(
        secret_name='infrasketch/devto-api-key',
        default_env_var='DEVTO_API_KEY'
    )
