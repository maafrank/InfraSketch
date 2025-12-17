"""
DynamoDB-backed storage for user preferences.
Provides persistent storage for user settings like tutorial completion status.
"""
import os
import json
import time
from typing import Optional
from decimal import Decimal
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from .models import UserPreferences


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


class UserPreferencesStorage:
    """DynamoDB-backed user preferences storage."""

    def __init__(self, table_name: str = "infrasketch-user-preferences"):
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create table if it doesn't exist."""
        dynamodb_client = boto3.client("dynamodb")

        try:
            # Try to describe the table
            self.table.load()
            print(f"DynamoDB table '{self.table_name}' exists")

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                # Table doesn't exist, create it
                print(f"Creating DynamoDB table '{self.table_name}'...")
                dynamodb_client.create_table(
                    TableName=self.table_name,
                    KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
                    AttributeDefinitions=[
                        {"AttributeName": "user_id", "AttributeType": "S"}
                    ],
                    BillingMode="PAY_PER_REQUEST",  # On-demand pricing
                    Tags=[
                        {"Key": "Application", "Value": "InfraSketch"},
                        {"Key": "Environment", "Value": "production"},
                    ],
                )
                # Wait for table to be created
                waiter = dynamodb_client.get_waiter("table_exists")
                waiter.wait(TableName=self.table_name)
                print(f"DynamoDB table '{self.table_name}' created successfully")
            else:
                raise

    def _serialize_preferences(self, prefs: UserPreferences) -> dict:
        """Convert UserPreferences to DynamoDB item."""
        prefs_dict = json.loads(prefs.model_dump_json())

        # Convert all floats to Decimals for DynamoDB compatibility
        prefs_dict = convert_floats_to_decimals(prefs_dict)

        return prefs_dict

    def _deserialize_preferences(self, item: dict) -> UserPreferences:
        """Convert DynamoDB item to UserPreferences."""
        # Convert Decimal types back to float/int
        item_json = json.dumps(item, cls=DecimalEncoder)
        return UserPreferences.model_validate_json(item_json)

    def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Retrieve user preferences from DynamoDB."""
        try:
            response = self.table.get_item(Key={"user_id": user_id})

            if "Item" not in response:
                return None

            return self._deserialize_preferences(response["Item"])
        except Exception as e:
            print(f"Error retrieving preferences for user {user_id}: {e}")
            return None

    def save_preferences(self, prefs: UserPreferences) -> bool:
        """Save or update user preferences in DynamoDB."""
        try:
            # Update the updated_at timestamp
            prefs.updated_at = datetime.utcnow()
            item = self._serialize_preferences(prefs)
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error saving preferences for user {prefs.user_id}: {e}")
            return False

    def get_or_create_preferences(self, user_id: str) -> UserPreferences:
        """Get existing preferences or create default ones."""
        prefs = self.get_preferences(user_id)
        if prefs is None:
            prefs = UserPreferences(user_id=user_id)
            self.save_preferences(prefs)
        return prefs

    def mark_tutorial_completed(self, user_id: str) -> bool:
        """Mark the tutorial as completed for a user."""
        prefs = self.get_or_create_preferences(user_id)
        prefs.tutorial_completed = True
        prefs.tutorial_completed_at = datetime.utcnow()
        return self.save_preferences(prefs)

    def reset_tutorial(self, user_id: str) -> bool:
        """Reset tutorial status so user can replay it."""
        prefs = self.get_or_create_preferences(user_id)
        prefs.tutorial_completed = False
        prefs.tutorial_completed_at = None
        return self.save_preferences(prefs)


# Singleton instance for Lambda environment
_storage_instance: Optional[UserPreferencesStorage] = None


def get_user_preferences_storage() -> UserPreferencesStorage:
    """Get or create the singleton storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = UserPreferencesStorage()
    return _storage_instance
