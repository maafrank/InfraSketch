"""
DynamoDB-backed storage for user credits and transactions.
Provides persistent storage for credit balances and audit trail.
"""

import os
import json
import uuid
from typing import Optional, List, Tuple
from decimal import Decimal
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from .models import UserCredits, CreditTransaction
from .credit_costs import get_plan_credits


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


class UserCreditsStorage:
    """DynamoDB-backed user credits storage."""

    def __init__(
        self,
        credits_table_name: str = "infrasketch-user-credits",
        transactions_table_name: str = "infrasketch-credit-transactions",
    ):
        self.credits_table_name = credits_table_name
        self.transactions_table_name = transactions_table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.credits_table = self.dynamodb.Table(credits_table_name)
        self.transactions_table = self.dynamodb.Table(transactions_table_name)
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        """Create tables if they don't exist."""
        dynamodb_client = boto3.client("dynamodb")

        # Check/create credits table
        try:
            self.credits_table.load()
            print(f"DynamoDB table '{self.credits_table_name}' exists")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                print(f"Creating DynamoDB table '{self.credits_table_name}'...")
                dynamodb_client.create_table(
                    TableName=self.credits_table_name,
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
                waiter.wait(TableName=self.credits_table_name)
                print(f"DynamoDB table '{self.credits_table_name}' created successfully")
            else:
                raise

        # Check/create transactions table
        try:
            self.transactions_table.load()
            print(f"DynamoDB table '{self.transactions_table_name}' exists")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                print(f"Creating DynamoDB table '{self.transactions_table_name}'...")
                dynamodb_client.create_table(
                    TableName=self.transactions_table_name,
                    KeySchema=[
                        {"AttributeName": "transaction_id", "KeyType": "HASH"}
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "transaction_id", "AttributeType": "S"},
                        {"AttributeName": "user_id", "AttributeType": "S"},
                    ],
                    GlobalSecondaryIndexes=[
                        {
                            "IndexName": "user_id-index",
                            "KeySchema": [
                                {"AttributeName": "user_id", "KeyType": "HASH"}
                            ],
                            "Projection": {"ProjectionType": "ALL"},
                        }
                    ],
                    BillingMode="PAY_PER_REQUEST",
                    Tags=[
                        {"Key": "Application", "Value": "InfraSketch"},
                        {"Key": "Environment", "Value": "production"},
                    ],
                )
                waiter = dynamodb_client.get_waiter("table_exists")
                waiter.wait(TableName=self.transactions_table_name)
                print(
                    f"DynamoDB table '{self.transactions_table_name}' created successfully"
                )
            else:
                raise

    def _serialize_credits(self, credits: UserCredits) -> dict:
        """Convert UserCredits to DynamoDB item."""
        credits_dict = json.loads(credits.model_dump_json())
        return convert_floats_to_decimals(credits_dict)

    def _deserialize_credits(self, item: dict) -> UserCredits:
        """Convert DynamoDB item to UserCredits."""
        item_json = json.dumps(item, cls=DecimalEncoder)
        return UserCredits.model_validate_json(item_json)

    def _serialize_transaction(self, txn: CreditTransaction) -> dict:
        """Convert CreditTransaction to DynamoDB item."""
        txn_dict = json.loads(txn.model_dump_json())
        return convert_floats_to_decimals(txn_dict)

    def _deserialize_transaction(self, item: dict) -> CreditTransaction:
        """Convert DynamoDB item to CreditTransaction."""
        item_json = json.dumps(item, cls=DecimalEncoder)
        return CreditTransaction.model_validate_json(item_json)

    def get_credits(self, user_id: str) -> Optional[UserCredits]:
        """Retrieve user credits from DynamoDB."""
        try:
            response = self.credits_table.get_item(Key={"user_id": user_id})
            if "Item" not in response:
                return None
            return self._deserialize_credits(response["Item"])
        except Exception as e:
            print(f"Error retrieving credits for user {user_id}: {e}")
            return None

    def save_credits(self, credits: UserCredits) -> bool:
        """Save or update user credits in DynamoDB."""
        try:
            credits.updated_at = datetime.utcnow()
            item = self._serialize_credits(credits)
            self.credits_table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error saving credits for user {credits.user_id}: {e}")
            return False

    def get_or_create_credits(self, user_id: str) -> UserCredits:
        """Get existing credits or create with free tier defaults."""
        credits = self.get_credits(user_id)
        if credits is None:
            credits = UserCredits(
                user_id=user_id,
                plan="free",
                credits_balance=get_plan_credits("free"),
                credits_monthly_allowance=get_plan_credits("free"),
                plan_started_at=datetime.utcnow(),
            )
            self.save_credits(credits)
            # Log the initial grant
            self._log_transaction(
                user_id=user_id,
                txn_type="grant",
                amount=credits.credits_balance,
                balance_after=credits.credits_balance,
                action="initial_signup",
                metadata={"plan": "free"},
            )
        return credits

    def deduct_credits(
        self,
        user_id: str,
        amount: int,
        action: str,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Tuple[bool, UserCredits]:
        """
        Deduct credits from user balance atomically.

        Returns:
            Tuple of (success, updated_credits)
        """
        credits = self.get_or_create_credits(user_id)

        # Check if user has enough credits
        if credits.credits_balance < amount:
            return (False, credits)

        # Deduct credits
        credits.credits_balance -= amount
        credits.credits_used_this_period += amount

        if not self.save_credits(credits):
            return (False, credits)

        # Log the transaction
        self._log_transaction(
            user_id=user_id,
            txn_type="deduction",
            amount=-amount,
            balance_after=credits.credits_balance,
            action=action,
            session_id=session_id,
            metadata=metadata or {},
        )

        return (True, credits)

    def add_credits(
        self,
        user_id: str,
        amount: int,
        reason: str,
        metadata: Optional[dict] = None,
    ) -> UserCredits:
        """Add credits to user balance (for promo codes, etc.)."""
        credits = self.get_or_create_credits(user_id)
        credits.credits_balance += amount
        self.save_credits(credits)

        self._log_transaction(
            user_id=user_id,
            txn_type="grant",
            amount=amount,
            balance_after=credits.credits_balance,
            action=reason,
            metadata=metadata or {},
        )

        return credits

    def reset_monthly_credits(self, user_id: str) -> UserCredits:
        """Reset credits to monthly allowance (called on billing cycle)."""
        credits = self.get_or_create_credits(user_id)

        old_balance = credits.credits_balance
        credits.credits_balance = credits.credits_monthly_allowance
        credits.credits_used_this_period = 0
        credits.last_credit_reset_at = datetime.utcnow()

        self.save_credits(credits)

        self._log_transaction(
            user_id=user_id,
            txn_type="reset",
            amount=credits.credits_balance - old_balance,
            balance_after=credits.credits_balance,
            action="monthly_reset",
            metadata={"plan": credits.plan},
        )

        return credits

    def update_plan(
        self,
        user_id: str,
        new_plan: str,
        clerk_subscription_id: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
    ) -> UserCredits:
        """Update user's subscription plan and adjust credits."""
        credits = self.get_or_create_credits(user_id)

        old_plan = credits.plan
        old_allowance = credits.credits_monthly_allowance
        new_allowance = get_plan_credits(new_plan)

        credits.plan = new_plan
        credits.credits_monthly_allowance = new_allowance
        credits.subscription_status = "active"
        credits.plan_started_at = datetime.utcnow()

        if clerk_subscription_id:
            credits.clerk_subscription_id = clerk_subscription_id
        if stripe_customer_id:
            credits.stripe_customer_id = stripe_customer_id

        # On upgrade, immediately add the difference in credits
        if new_allowance > old_allowance:
            credit_boost = new_allowance - old_allowance
            credits.credits_balance += credit_boost
            txn_type = "upgrade"
        else:
            # On downgrade, just update allowance (credits remain until reset)
            credit_boost = 0
            txn_type = "downgrade"

        self.save_credits(credits)

        self._log_transaction(
            user_id=user_id,
            txn_type=txn_type,
            amount=credit_boost,
            balance_after=credits.credits_balance,
            action="plan_change",
            metadata={
                "old_plan": old_plan,
                "new_plan": new_plan,
                "old_allowance": old_allowance,
                "new_allowance": new_allowance,
            },
        )

        return credits

    def mark_promo_redeemed(self, user_id: str, promo_code: str) -> bool:
        """Mark a promo code as redeemed by user."""
        credits = self.get_or_create_credits(user_id)
        if promo_code not in credits.redeemed_promo_codes:
            credits.redeemed_promo_codes.append(promo_code)
            return self.save_credits(credits)
        return True

    def has_redeemed_promo(self, user_id: str, promo_code: str) -> bool:
        """Check if user has already redeemed a promo code."""
        credits = self.get_credits(user_id)
        if credits is None:
            return False
        return promo_code in credits.redeemed_promo_codes

    def _log_transaction(
        self,
        user_id: str,
        txn_type: str,
        amount: int,
        balance_after: int,
        action: str,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Log a credit transaction to the audit table."""
        try:
            txn = CreditTransaction(
                transaction_id=str(uuid.uuid4()),
                user_id=user_id,
                type=txn_type,
                amount=amount,
                balance_after=balance_after,
                action=action,
                session_id=session_id,
                metadata=metadata or {},
            )
            item = self._serialize_transaction(txn)
            self.transactions_table.put_item(Item=item)
        except Exception as e:
            print(f"Error logging transaction for user {user_id}: {e}")

    def get_transaction_history(
        self, user_id: str, limit: int = 50
    ) -> List[CreditTransaction]:
        """Get user's credit transaction history."""
        try:
            response = self.transactions_table.query(
                IndexName="user_id-index",
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id},
                ScanIndexForward=False,  # Most recent first
                Limit=limit,
            )
            return [
                self._deserialize_transaction(item) for item in response.get("Items", [])
            ]
        except Exception as e:
            print(f"Error retrieving transaction history for user {user_id}: {e}")
            return []


# Singleton instance for Lambda environment
_storage_instance: Optional[UserCreditsStorage] = None


def get_user_credits_storage() -> UserCreditsStorage:
    """Get or create the singleton storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = UserCreditsStorage()
    return _storage_instance
