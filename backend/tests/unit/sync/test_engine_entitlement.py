"""Entitlement re-checks at engine execution time.

Regression: scheduling time (schedule()) checked _user_is_paid, but the
actual LLM-calling execution (run_diagram_to_doc) did not. A user could
become past_due between schedule and dispatch and still get free service.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.sync import engine


def _session_pending(user_id="user_test", session_id="sess_test"):
    sess = MagicMock()
    sess.user_id = user_id
    sess.sync_status.state = "pending"
    sess.sync_status.sync_due_at = time.time() - 1  # past, should fire
    sess.diagram_revision = 5
    sess.design_doc_revision = 3
    sess.last_synced_diagram_revision = 0  # so the "already synced" no-op doesn't kick in
    return sess


def test_run_aborts_when_user_no_longer_paid(mocker):
    sess = _session_pending()
    sm = MagicMock()
    sm.get_session.return_value = sess
    # session_manager is imported lazily inside the function, so patch the source.
    mocker.patch("app.session.manager.session_manager", sm)
    mocker.patch("app.sync.engine._user_is_paid", return_value=False)
    exec_spy = mocker.patch("app.sync.engine._execute_diagram_to_doc")

    engine.run_diagram_to_doc("sess_test")

    exec_spy.assert_not_called()
    # Status should be flipped to idle with a clear error reason.
    assert sm.update_sync_status.called
    call_kwargs = sm.update_sync_status.call_args.kwargs
    assert call_kwargs.get("state") == "idle"
    assert call_kwargs.get("error") == "not_entitled"


def test_run_proceeds_when_user_still_paid(mocker):
    sess = _session_pending()
    sm = MagicMock()
    sm.get_session.return_value = sess
    mocker.patch("app.session.manager.session_manager", sm)
    mocker.patch("app.sync.engine._user_is_paid", return_value=True)
    exec_spy = mocker.patch("app.sync.engine._execute_diagram_to_doc", return_value="NO_SYNC_NEEDED")

    engine.run_diagram_to_doc("sess_test")

    exec_spy.assert_called_once()
