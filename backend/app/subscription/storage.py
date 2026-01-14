"""
DynamoDB storage for email subscribers.
Handles opt-in/opt-out tracking for marketing emails.
"""
import os
import uuid
import time
from typing import Optional, List
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from .models import Subscriber


class SubscriberStorage:
    """DynamoDB-backed subscriber storage."""

    def __init__(self, table_name: str = "infrasketch-subscribers"):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create table if it doesn't exist, with GSI for token lookups."""
        dynamodb_client = boto3.client('dynamodb')

        try:
            self.table.load()
            print(f"DynamoDB table '{self.table_name}' exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Creating DynamoDB table '{self.table_name}'...")
                dynamodb_client.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'user_id', 'AttributeType': 'S'},
                        {'AttributeName': 'unsubscribe_token', 'AttributeType': 'S'}
                    ],
                    GlobalSecondaryIndexes=[{
                        'IndexName': 'token-index',
                        'KeySchema': [
                            {'AttributeName': 'unsubscribe_token', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'}
                    }],
                    BillingMode='PAY_PER_REQUEST',
                    Tags=[
                        {'Key': 'Application', 'Value': 'InfraSketch'},
                        {'Key': 'Environment', 'Value': 'production'}
                    ]
                )
                waiter = dynamodb_client.get_waiter('table_exists')
                waiter.wait(TableName=self.table_name)
                print(f"DynamoDB table '{self.table_name}' created successfully")
            else:
                raise

    def _generate_token(self) -> str:
        """Generate a unique unsubscribe token."""
        return str(uuid.uuid4())

    def _now_iso(self) -> str:
        """Get current time as ISO string."""
        return datetime.utcnow().isoformat() + "Z"

    def create_subscriber(self, user_id: str, email: str) -> Subscriber:
        """
        Create a new subscriber (auto opt-in).
        If subscriber already exists, returns existing record.
        """
        # Check if already exists
        existing = self.get_subscriber(user_id)
        if existing:
            # Update email if changed
            if existing.email != email:
                return self.update_email(user_id, email)
            return existing

        now = self._now_iso()
        subscriber = Subscriber(
            user_id=user_id,
            email=email,
            subscribed=True,
            unsubscribe_token=self._generate_token(),
            created_at=now,
            updated_at=now,
            unsubscribed_at=None
        )

        try:
            self.table.put_item(Item=subscriber.model_dump())
            print(f"Created subscriber: {email}")
            return subscriber
        except Exception as e:
            print(f"Error creating subscriber {user_id}: {e}")
            raise

    def get_subscriber(self, user_id: str) -> Optional[Subscriber]:
        """Get subscriber by Clerk user ID."""
        try:
            response = self.table.get_item(Key={'user_id': user_id})
            if 'Item' not in response:
                return None
            return Subscriber(**response['Item'])
        except Exception as e:
            print(f"Error getting subscriber {user_id}: {e}")
            return None

    def get_subscriber_by_token(self, token: str) -> Optional[Subscriber]:
        """Get subscriber by unsubscribe token (for email links)."""
        try:
            response = self.table.query(
                IndexName='token-index',
                KeyConditionExpression='unsubscribe_token = :token',
                ExpressionAttributeValues={':token': token}
            )
            items = response.get('Items', [])
            if not items:
                return None
            return Subscriber(**items[0])
        except Exception as e:
            print(f"Error getting subscriber by token: {e}")
            return None

    def unsubscribe(self, user_id: str) -> bool:
        """Unsubscribe a user from emails."""
        now = self._now_iso()
        try:
            self.table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET subscribed = :sub, unsubscribed_at = :unsub_at, updated_at = :updated',
                ExpressionAttributeValues={
                    ':sub': False,
                    ':unsub_at': now,
                    ':updated': now
                }
            )
            print(f"Unsubscribed user: {user_id}")
            return True
        except Exception as e:
            print(f"Error unsubscribing {user_id}: {e}")
            return False

    def resubscribe(self, user_id: str) -> bool:
        """Re-subscribe a user to emails."""
        now = self._now_iso()
        try:
            self.table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET subscribed = :sub, updated_at = :updated REMOVE unsubscribed_at',
                ExpressionAttributeValues={
                    ':sub': True,
                    ':updated': now
                }
            )
            print(f"Resubscribed user: {user_id}")
            return True
        except Exception as e:
            print(f"Error resubscribing {user_id}: {e}")
            return False

    def update_email(self, user_id: str, new_email: str) -> Optional[Subscriber]:
        """Update subscriber's email address."""
        now = self._now_iso()
        try:
            self.table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET email = :email, updated_at = :updated',
                ExpressionAttributeValues={
                    ':email': new_email,
                    ':updated': now
                }
            )
            print(f"Updated email for user {user_id}")
            return self.get_subscriber(user_id)
        except Exception as e:
            print(f"Error updating email for {user_id}: {e}")
            return None

    def get_all_subscribed(self) -> List[Subscriber]:
        """Get all subscribers who are opted in."""
        try:
            # Scan with filter for subscribed=true
            # Note: Scan is fine for small subscriber lists (< 1000)
            # For larger lists, consider a GSI on subscribed status
            response = self.table.scan(
                FilterExpression='subscribed = :sub',
                ExpressionAttributeValues={':sub': True}
            )

            subscribers = []
            for item in response.get('Items', []):
                subscribers.append(Subscriber(**item))

            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression='subscribed = :sub',
                    ExpressionAttributeValues={':sub': True},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    subscribers.append(Subscriber(**item))

            return subscribers
        except Exception as e:
            print(f"Error getting subscribed users: {e}")
            return []

    def get_subscriber_count(self) -> dict:
        """Get count of total and subscribed users."""
        try:
            # Get all items (scan)
            response = self.table.scan(
                Select='COUNT'
            )
            total = response.get('Count', 0)

            # Get subscribed count
            response = self.table.scan(
                FilterExpression='subscribed = :sub',
                ExpressionAttributeValues={':sub': True},
                Select='COUNT'
            )
            subscribed = response.get('Count', 0)

            return {
                'total': total,
                'subscribed': subscribed,
                'unsubscribed': total - subscribed
            }
        except Exception as e:
            print(f"Error getting subscriber count: {e}")
            return {'total': 0, 'subscribed': 0, 'unsubscribed': 0}


# Singleton instance for local development
_local_storage: Optional[SubscriberStorage] = None


def get_subscriber_storage() -> SubscriberStorage:
    """Get or create subscriber storage instance."""
    global _local_storage

    # In Lambda, always create fresh (stateless)
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        return SubscriberStorage()

    # In local dev, use singleton
    if _local_storage is None:
        _local_storage = SubscriberStorage()

    return _local_storage
