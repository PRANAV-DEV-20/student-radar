import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models.credit import CreditTransaction
from app.schemas.credit import CreditTransactionResponse
from app.services.credit_service import (
    ActiveBoostError,
    DuplicateReviewError,
    InsufficientCreditsError,
    NotDossierOwnerError,
    credit_service,
)


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return [] if self.value is None else [self.value]


class FakeSession:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.added = []
        self.flushed = 0
        self.rolled_back = 0

    async def execute(self, statement):
        return FakeResult(self.results.pop(0) if self.results else None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed += 1

    async def rollback(self):
        self.rolled_back += 1


def test_spend_credits_is_atomic_and_records_ledger():
    session = FakeSession([30])
    user_id = uuid.uuid4()
    dossier_id = uuid.uuid4()

    balance = asyncio.run(
        credit_service.spend_credits(
            session,
            user_id,
            20,
            "boost_launch",
            dossier_id=dossier_id,
            metadata={"dossier_slug": "edge-kernel"},
        )
    )

    assert balance == 30
    assert len(session.added) == 1
    transaction = session.added[0]
    assert transaction.amount == -20
    assert transaction.dossier_id == dossier_id
    assert transaction.reason == "boost_launch"


def test_spend_credits_raises_when_balance_is_insufficient():
    session = FakeSession([None, 5])
    with pytest.raises(InsufficientCreditsError) as exc:
        asyncio.run(credit_service.spend_credits(session, uuid.uuid4(), 20, "boost_launch"))
    assert exc.value.balance == 5
    assert exc.value.required == 20


def test_award_credits_rejects_non_positive_amounts():
    with pytest.raises(ValueError):
        asyncio.run(credit_service.award_credits(FakeSession(), uuid.uuid4(), 0, "review_peer"))


def test_record_peer_review_blocks_duplicate_reviews():
    reviewer = SimpleNamespace(id=uuid.uuid4())
    dossier = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), title="Test Project")
    session = FakeSession([dossier.id])  # existing transaction id

    with pytest.raises(DuplicateReviewError):
        asyncio.run(
            credit_service.record_peer_review(
                session,
                reviewer,
                dossier,
                {"strength": "a", "bottleneck": "b", "suggestion": "c"},
            )
        )


def test_record_peer_review_awards_ten_credits():
    reviewer = SimpleNamespace(id=uuid.uuid4())
    dossier = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), title="Test Project")
    session = FakeSession([None, 40])

    balance = asyncio.run(
        credit_service.record_peer_review(
            session,
            reviewer,
            dossier,
            {
                "strength": "Clear architecture.",
                "bottleneck": "Single-threaded index.",
                "suggestion": "Move compaction off the write path.",
            },
        )
    )

    assert balance == 40
    transaction = session.added[0]
    assert transaction.amount == 10
    assert transaction.reason == "review_peer"
    assert transaction.dossier_id == dossier.id


def test_boost_dossier_sets_expiry_and_returns_payload():
    user_id = uuid.uuid4()
    user = SimpleNamespace(id=user_id)
    dossier = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Edge Kernel",
        slug="edge-kernel",
        boosted=False,
        boosted_until=None,
    )
    session = FakeSession([10])

    payload = asyncio.run(credit_service.boost_dossier(session, user, dossier))

    assert payload["status"] == "boosted"
    assert payload["credits_deducted"] == 20
    assert payload["remaining_balance"] == 10
    assert dossier.boosted is True
    assert dossier.boosted_until > datetime.now(timezone.utc) + timedelta(hours=47)


def test_boost_rejects_active_boost_and_non_owner():
    now = datetime.now(timezone.utc)
    user = SimpleNamespace(id=uuid.uuid4())
    active = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Active",
        slug="active",
        boosted=True,
        boosted_until=now + timedelta(hours=10),
    )
    with pytest.raises(ActiveBoostError):
        asyncio.run(credit_service.boost_dossier(FakeSession(), user, active))

    foreign = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title="Foreign",
        slug="foreign",
        boosted=False,
        boosted_until=None,
    )
    with pytest.raises(NotDossierOwnerError):
        asyncio.run(credit_service.boost_dossier(FakeSession(), user, foreign))


def test_credit_transaction_response_exposes_delta_and_metadata():
    tx = CreditTransaction(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        dossier_id=uuid.uuid4(),
        amount=-20,
        reason="boost_launch",
        metadata_json={"dossier_slug": "edge-kernel"},
        created_at=datetime.now(timezone.utc),
    )
    response = CreditTransactionResponse.model_validate(tx)
    assert response.delta == -20
    assert response.metadata == {"dossier_slug": "edge-kernel"}
