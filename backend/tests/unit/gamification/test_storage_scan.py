"""Tests for GamificationStorage.scan_at_risk_users method.

Covers: basic scan, pagination, error handling, filter logic.
"""

from unittest.mock import patch, MagicMock
from app.gamification.storage import GamificationStorage


def _make_mock_storage():
    """Create a GamificationStorage with mocked DynamoDB."""
    with patch("app.gamification.storage.boto3") as mock_boto3:
        mock_table = MagicMock()
        mock_table.load.return_value = None
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        mock_boto3.client.return_value = MagicMock()

        storage = GamificationStorage()
        return storage, mock_table


class TestScanAtRiskUsers:
    def test_returns_at_risk_users(self):
        storage, mock_table = _make_mock_storage()
        mock_table.scan.return_value = {
            "Items": [
                {
                    "user_id": "user-1",
                    "current_streak": 5,
                    "last_active_date": "2026-02-04",
                    "streak_grace_used": False,
                    "streak_reminders_enabled": True,
                    "xp_total": 100,
                    "level": 2,
                    "level_name": "Junior Designer",
                }
            ]
        }

        results = storage.scan_at_risk_users("2026-02-05")
        assert len(results) == 1
        assert results[0].user_id == "user-1"
        assert results[0].current_streak == 5

    def test_returns_empty_when_no_at_risk(self):
        storage, mock_table = _make_mock_storage()
        mock_table.scan.return_value = {"Items": []}

        results = storage.scan_at_risk_users("2026-02-05")
        assert results == []

    def test_handles_pagination(self):
        storage, mock_table = _make_mock_storage()
        mock_table.scan.side_effect = [
            {
                "Items": [
                    {
                        "user_id": "user-1",
                        "current_streak": 3,
                        "last_active_date": "2026-02-04",
                        "xp_total": 0,
                        "level": 1,
                        "level_name": "Intern",
                    }
                ],
                "LastEvaluatedKey": {"user_id": "user-1"},
            },
            {
                "Items": [
                    {
                        "user_id": "user-2",
                        "current_streak": 7,
                        "last_active_date": "2026-02-03",
                        "xp_total": 50,
                        "level": 2,
                        "level_name": "Junior Designer",
                    }
                ],
            },
        ]

        results = storage.scan_at_risk_users("2026-02-05")
        assert len(results) == 2
        assert results[0].user_id == "user-1"
        assert results[1].user_id == "user-2"

    def test_returns_empty_on_error(self):
        storage, mock_table = _make_mock_storage()
        mock_table.scan.side_effect = Exception("DynamoDB error")

        results = storage.scan_at_risk_users("2026-02-05")
        assert results == []

    def test_scan_called_with_correct_filter(self):
        storage, mock_table = _make_mock_storage()
        mock_table.scan.return_value = {"Items": []}

        storage.scan_at_risk_users("2026-02-05")

        mock_table.scan.assert_called_once()
        call_kwargs = mock_table.scan.call_args[1]
        assert ":zero" in call_kwargs["ExpressionAttributeValues"]
        assert ":today" in call_kwargs["ExpressionAttributeValues"]
        assert call_kwargs["ExpressionAttributeValues"][":today"] == "2026-02-05"
        assert "current_streak > :zero" in call_kwargs["FilterExpression"]
        assert "last_active_date < :today" in call_kwargs["FilterExpression"]

    def test_filter_includes_streak_reminders_check(self):
        """Verify the scan filter only includes users with reminders enabled."""
        storage, mock_table = _make_mock_storage()
        mock_table.scan.return_value = {"Items": []}

        storage.scan_at_risk_users("2026-02-05")

        call_kwargs = mock_table.scan.call_args[1]
        filter_expr = call_kwargs["FilterExpression"]
        expr_values = call_kwargs["ExpressionAttributeValues"]
        # Must check for opted-in users
        assert "streak_reminders_enabled = :enabled" in filter_expr
        assert expr_values[":enabled"] is True
        # Must handle backwards compat (old records missing the field)
        assert "attribute_not_exists(streak_reminders_enabled)" in filter_expr

    def test_multiple_users_returned(self):
        storage, mock_table = _make_mock_storage()
        mock_table.scan.return_value = {
            "Items": [
                {
                    "user_id": "user-1",
                    "current_streak": 3,
                    "last_active_date": "2026-02-04",
                    "xp_total": 0,
                    "level": 1,
                    "level_name": "Intern",
                },
                {
                    "user_id": "user-2",
                    "current_streak": 10,
                    "last_active_date": "2026-02-03",
                    "streak_grace_used": True,
                    "xp_total": 200,
                    "level": 3,
                    "level_name": "Designer",
                },
            ]
        }

        results = storage.scan_at_risk_users("2026-02-05")
        assert len(results) == 2
        user_ids = [r.user_id for r in results]
        assert "user-1" in user_ids
        assert "user-2" in user_ids
