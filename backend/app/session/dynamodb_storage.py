"""
DynamoDB-backed session storage for Lambda environment.
Provides persistent session storage across Lambda invocations.
"""
import os
import json
import time
from typing import Optional, List
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from app.models import SessionState, Diagram, Message, DesignDocStatus

import logging
logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def convert_floats_to_decimals(obj):
    """Recursively convert all float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimals(item) for item in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


class DynamoDBSessionStorage:
    """DynamoDB-backed session storage."""

    def __init__(self, table_name: str = "infrasketch-sessions"):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create table if it doesn't exist, with GSI for user_id queries."""
        dynamodb_client = boto3.client('dynamodb')

        try:
            # Try to describe the table
            self.table.load()
            logger.info(f"DynamoDB table '{self.table_name}' exists")

            # Check if GSI exists, create if missing
            table_description = dynamodb_client.describe_table(TableName=self.table_name)
            gsis = table_description.get('Table', {}).get('GlobalSecondaryIndexes', [])

            existing_indexes = {gsi['IndexName'] for gsi in gsis}

            # DynamoDB allows only one GSI creation at a time, so these are
            # attempted independently and any that fail for that reason get
            # created on a later cold start.
            pending = [
                (
                    'user_id-index',
                    [{'AttributeName': 'user_id', 'AttributeType': 'S'}],
                    [{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
                ),
                # Sparse: only shared sessions carry share_token, so this index
                # holds one entry per share rather than one per session.
                (
                    'share_token-index',
                    [{'AttributeName': 'share_token', 'AttributeType': 'S'}],
                    [{'AttributeName': 'share_token', 'KeyType': 'HASH'}],
                ),
                # Sparse too: powers the share sitemap without a table scan.
                (
                    'public_flag-index',
                    [
                        {'AttributeName': 'public_flag', 'AttributeType': 'S'},
                        {'AttributeName': 'session_id', 'AttributeType': 'S'},
                    ],
                    [
                        {'AttributeName': 'public_flag', 'KeyType': 'HASH'},
                        {'AttributeName': 'session_id', 'KeyType': 'RANGE'},
                    ],
                ),
            ]

            for index_name, attr_defs, key_schema in pending:
                if index_name in existing_indexes:
                    continue
                logger.info(f"Creating {index_name} on table '{self.table_name}'...")
                try:
                    dynamodb_client.update_table(
                        TableName=self.table_name,
                        AttributeDefinitions=attr_defs,
                        GlobalSecondaryIndexUpdates=[{
                            'Create': {
                                'IndexName': index_name,
                                'KeySchema': key_schema,
                                'Projection': {'ProjectionType': 'ALL'}
                                # Note: BillingMode is inherited from table, cannot be specified in GSI update
                            }
                        }]
                    )
                    logger.info(f"GSI creation initiated for '{index_name}'")
                    # Only one index can be building at a time; the rest are
                    # picked up on a later invocation.
                    break
                except ClientError as gsi_error:
                    logger.warning(f"Could not create {index_name} now: {gsi_error}")
                    break

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it with GSI
                logger.info(f"Creating DynamoDB table '{self.table_name}' with user_id GSI...")
                dynamodb_client.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {'AttributeName': 'session_id', 'KeyType': 'HASH'}
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'session_id', 'AttributeType': 'S'},
                        {'AttributeName': 'user_id', 'AttributeType': 'S'}
                    ],
                    GlobalSecondaryIndexes=[{
                        'IndexName': 'user_id-index',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }],
                    BillingMode='PAY_PER_REQUEST',  # On-demand pricing
                    Tags=[
                        {'Key': 'Application', 'Value': 'InfraSketch'},
                        {'Key': 'Environment', 'Value': 'production'}
                    ]
                )
                # Wait for table to be created
                waiter = dynamodb_client.get_waiter('table_exists')
                waiter.wait(TableName=self.table_name)
                logger.info(f"DynamoDB table '{self.table_name}' created successfully with GSI")
            else:
                raise

    def _serialize_session(self, session: SessionState) -> dict:
        """Convert SessionState to DynamoDB item."""
        # Convert to dict, then to JSON string, then back to dict
        # This handles nested Pydantic models properly
        session_dict = json.loads(session.model_dump_json())

        # Convert all floats to Decimals for DynamoDB compatibility
        session_dict = convert_floats_to_decimals(session_dict)

        # Drop null GSI keys. DynamoDB rejects an item whose index key attribute
        # is present but null, and a sparse index requires the attribute to be
        # absent entirely for non-shared sessions.
        for sparse_key in ('share_token', 'public_flag'):
            if session_dict.get(sparse_key) is None:
                session_dict.pop(sparse_key, None)

        # Add TTL (expire sessions after 1 year)
        session_dict['ttl'] = int(time.time()) + (365 * 24 * 60 * 60)

        return session_dict

    def _deserialize_session(self, item: dict) -> SessionState:
        """Convert DynamoDB item to SessionState."""
        # Remove TTL field before deserializing
        item.pop('ttl', None)

        # Convert Decimal types back to float/int
        item_json = json.dumps(item, cls=DecimalEncoder)
        return SessionState.model_validate_json(item_json)

    def save_session(self, session: SessionState) -> bool:
        """Save or update session in DynamoDB."""
        try:
            item = self._serialize_session(session)
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logger.exception(f"Error saving session {session.session_id}: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve session from DynamoDB."""
        try:
            response = self.table.get_item(Key={'session_id': session_id})

            if 'Item' not in response:
                return None

            return self._deserialize_session(response['Item'])
        except Exception as e:
            logger.exception(f"Error retrieving session {session_id}: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session from DynamoDB."""
        try:
            self.table.delete_item(Key={'session_id': session_id})
            return True
        except Exception as e:
            logger.exception(f"Error deleting session {session_id}: {e}")
            return False

    def get_sessions_by_user(self, user_id: str) -> List[SessionState]:
        """
        Query all sessions belonging to a user using GSI.

        Args:
            user_id: Clerk user ID

        Returns:
            List of SessionState objects
        """
        try:
            response = self.table.query(
                IndexName='user_id-index',
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )

            sessions = []
            for item in response.get('Items', []):
                try:
                    session = self._deserialize_session(item)
                    sessions.append(session)
                except Exception as e:
                    logger.exception(f"Error deserializing session: {e}")
                    continue

            return sessions

        except Exception as e:
            logger.exception(f"Error querying sessions for user {user_id}: {e}")
            return []

    def get_session_by_share_token(self, share_token: str) -> Optional[SessionState]:
        """Look up a shared session by its public token via the sparse GSI."""
        try:
            response = self.table.query(
                IndexName='share_token-index',
                KeyConditionExpression='share_token = :token',
                ExpressionAttributeValues={':token': share_token},
                Limit=1,
            )
            items = response.get('Items', [])
            if not items:
                return None
            return self._deserialize_session(items[0])
        except Exception as e:
            logger.exception(f"Error querying session by share token: {e}")
            return None

    def list_public_sessions(self, limit: int = 1000) -> List[SessionState]:
        """List publicly shared sessions, for the share sitemap."""
        try:
            response = self.table.query(
                IndexName='public_flag-index',
                KeyConditionExpression='public_flag = :flag',
                ExpressionAttributeValues={':flag': '1'},
                Limit=limit,
            )
            sessions = []
            for item in response.get('Items', []):
                try:
                    sessions.append(self._deserialize_session(item))
                except Exception as e:
                    logger.exception(f"Error deserializing public session: {e}")
            return sessions
        except Exception as e:
            logger.exception(f"Error listing public sessions: {e}")
            return []
