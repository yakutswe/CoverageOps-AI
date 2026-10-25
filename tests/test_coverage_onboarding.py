
from unittest.mock import MagicMock

import pytest

from app.coverage.services.onboarding import (
    create_customer_workflow,
)


def test_rejects_empty_company_name():
    db = MagicMock()

    with pytest.raises(ValueError):
        create_customer_workflow(
            db=db,
            company_name="   ",
            industry="Logistics",
        )

    db.add.assert_not_called()


def test_rejects_empty_industry():
    db = MagicMock()

    with pytest.raises(ValueError):
        create_customer_workflow(
            db=db,
            company_name="Northstar Logistics",
            industry="  ",
        )

    db.add.assert_not_called()


def test_customer_workflow_commits_once():
    db = MagicMock()

    result = create_customer_workflow(
        db=db,
        company_name="Northstar Logistics",
        industry="Logistics",
    )

    assert result["status"] == "pending"
    assert result["current_step"] == "intake"

    assert db.add.call_count == 3
    assert db.flush.call_count == 2
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_failed_commit_rolls_back():
    db = MagicMock()
    db.commit.side_effect = RuntimeError(
        "Simulated database failure"
    )

    with pytest.raises(RuntimeError):
        create_customer_workflow(
            db=db,
            company_name="Northstar Logistics",
            industry="Logistics",
        )

    db.rollback.assert_called_once()