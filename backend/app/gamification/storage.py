"""DynamoDB-backed storage for user gamification data."""

import os
import json
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from .models import UserGamification


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


class GamificationStorage:
    """DynamoDB-backed gamification storage."""

    def __init__(self, table_name: str = "infrasketch-user-gamification"):
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create table if it doesn't exist."""
        dynamodb_client = boto3.client("dynamodb")

        try:
            self.table.load()
            print(f"DynamoDB table '{self.table_name}' exists")

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                print(f"Creating DynamoDB table '{self.table_name}'...")
                dynamodb_client.create_table(
                    TableName=self.table_name,
                    KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
                    AttributeDefinitions=[
                        {"AttributeName": "user_id", "AttributeType": "S"}
                    ],
                    BillingMode="PAY_PER_REQUEST",
                    Tags=[
                        {"Key": "Application", "Value": "InfraSketch"},
                        {"Key": "Environment", "Value": "production"},
                    ],
                )
                waiter = dynamodb_client.get_waiter("table_exists")
                waiter.wait(TableName=self.table_name)
                print(f"DynamoDB table '{self.table_name}' created successfully")
            else:
                raise

    def _serialize(self, gamification: UserGamification) -> dict:
        """Convert UserGamification to DynamoDB item."""
        data = json.loads(gamification.model_dump_json())
        return convert_floats_to_decimals(data)

    def _deserialize(self, item: dict) -> UserGamification:
        """Convert DynamoDB item to UserGamification."""
        item_json = json.dumps(item, cls=DecimalEncoder)
        return UserGamification.model_validate_json(item_json)

    def get(self, user_id: str) -> Optional[UserGamification]:
        """Retrieve gamification data for a user."""
        try:
            response = self.table.get_item(Key={"user_id": user_id})
            if "Item" not in response:
                return None
            return self._deserialize(response["Item"])
        except Exception as e:
            print(f"Error retrieving gamification for user {user_id}: {e}")
            return None

    def save(self, gamification: UserGamification) -> bool:
        """Save or update gamification data."""
        try:
            gamification.updated_at = datetime.utcnow()
            item = self._serialize(gamification)
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error saving gamification for user {gamification.user_id}: {e}")
            return False

    def get_or_create(self, user_id: str) -> UserGamification:
        """Get existing gamification data or create defaults."""
        data = self.get(user_id)
        if data is None:
            data = UserGamification(user_id=user_id)
            self.save(data)
        return data

    def scan_at_risk_users(self, today_str: str) -> List[UserGamification]:
        """Scan for users who have an active streak but haven't been active today.

        Returns users where:
        - current_streak > 0
        - last_active_date < today_str (not active today)
        - streak_reminders_enabled is True OR field doesn't exist (backwards compat)
        """
        try:
            filter_expr = (
                "current_streak > :zero "
                "AND last_active_date < :today "
                "AND (attribute_not_exists(streak_reminders_enabled) "
                "OR streak_reminders_enabled = :enabled)"
            )
            expr_values = {
                ":zero": 0,
                ":today": today_str,
                ":enabled": True,
            }

            results = []
            response = self.table.scan(
                FilterExpression=filter_expr,
                ExpressionAttributeValues=expr_values,
            )
            for item in response.get("Items", []):
                results.append(self._deserialize(item))

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    FilterExpression=filter_expr,
                    ExpressionAttributeValues=expr_values,
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                for item in response.get("Items", []):
                    results.append(self._deserialize(item))

            return results
        except Exception as e:
            print(f"Error scanning at-risk users: {e}")
            return []


# Singleton instance
_storage_instance: Optional[GamificationStorage] = None


def get_gamification_storage() -> GamificationStorage:
    """Get or create the singleton storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = GamificationStorage()
    return _storage_instance
