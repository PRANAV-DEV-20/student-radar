import asyncio
import uuid
from types import SimpleNamespace

from app.api.v1.auth import _award_referral_if_present


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalars(self):
        return self

    def first(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.added = []
        self.flushed = 0

    async def execute(self, statement):
        return FakeResult(self.results.pop(0) if self.results else None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed += 1


def make_invite(sender_id, status="pending"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        sender_user_id=sender_id,
        status=status,
        claimed_user_id=None,
    )


def test_referral_awards_the_inviter_not_the_new_user():
    sender_id = uuid.uuid4()
    new_user = SimpleNamespace(id=uuid.uuid4())
    invite = make_invite(sender_id)
    session = FakeSession([invite, 45])  # invite lookup, then sender UPDATE..RETURNING

    awarded = asyncio.run(_award_referral_if_present(session, new_user, "ref_abc123"))

    assert awarded == 15
    assert invite.status == "claimed"
    assert invite.claimed_user_id == new_user.id
    assert len(session.added) == 1
    ledger = session.added[0]
    assert ledger.user_id == sender_id
    assert ledger.amount == 15
    assert ledger.reason == "signup_referral"
    assert ledger.metadata_json["referred_user_id"] == str(new_user.id)


def test_claimed_or_self_referral_tokens_are_ignored():
    user = SimpleNamespace(id=uuid.uuid4())

    claimed = make_invite(uuid.uuid4(), status="claimed")
    session = FakeSession([claimed])
    assert asyncio.run(_award_referral_if_present(session, user, "ref_claimed")) == 0
    assert session.added == []

    own_invite = make_invite(user.id)
    session = FakeSession([own_invite])
    assert asyncio.run(_award_referral_if_present(session, user, "ref_self")) == 0
    assert session.added == []


def test_missing_referral_token_is_a_noop():
    session = FakeSession()
    assert asyncio.run(_award_referral_if_present(session, SimpleNamespace(id=uuid.uuid4()), None)) == 0
    assert session.added == []
