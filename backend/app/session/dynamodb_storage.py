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
            print(f"DynamoDB table '{self.table_name}' exists")

            # Check if GSI exists, create if missing
            table_description = dynamodb_client.describe_table(TableName=self.table_name)
            gsis = table_description.get('Table', {}).get('GlobalSecondaryIndexes', [])

            has_user_gsi = any(gsi['IndexName'] == 'user_id-index' for gsi in gsis)

            if not has_user_gsi:
                print(f"Creating user_id GSI on table '{self.table_name}'...")
                dynamodb_client.update_table(
                    TableName=self.table_name,
                    AttributeDefinitions=[
                        {'AttributeName': 'user_id', 'AttributeType': 'S'}
                    ],
                    GlobalSecondaryIndexUpdates=[{
                        'Create': {
                            'IndexName': 'user_id-index',
                            'KeySchema': [
                                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                            ],
                            'Projection': {'ProjectionType': 'ALL'}
                            # Note: BillingMode is inherited from table, cannot be specified in GSI update
                        }
                    }]
                )
                print(f"GSI creation initiated for '{self.table_name}'")

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it with GSI
                print(f"Creating DynamoDB table '{self.table_name}' with user_id GSI...")
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
                print(f"DynamoDB table '{self.table_name}' created successfully with GSI")
            else:
                raise

    def _serialize_session(self, session: SessionState) -> dict:
        """Convert SessionState to DynamoDB item."""
        # Convert to dict, then to JSON string, then back to dict
        # This handles nested Pydantic models properly
        session_dict = json.loads(session.model_dump_json())

        # Convert all floats to Decimals for DynamoDB compatibility
        session_dict = convert_floats_to_decimals(session_dict)

        # Add TTL (expire sessions after 90 days for security)
        # Shorter TTL reduces exposure window if user credentials are compromised
        session_dict['ttl'] = int(time.time()) + (90 * 24 * 60 * 60)

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
            print(f"Error saving session {session.session_id}: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve session from DynamoDB."""
        try:
            response = self.table.get_item(Key={'session_id': session_id})

            if 'Item' not in response:
                return None

            return self._deserialize_session(response['Item'])
        except Exception as e:
            print(f"Error retrieving session {session_id}: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session from DynamoDB."""
        try:
            self.table.delete_item(Key={'session_id': session_id})
            return True
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
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
                    print(f"Error deserializing session: {e}")
                    continue

            return sessions

        except Exception as e:
            print(f"Error querying sessions for user {user_id}: {e}")
            return []
