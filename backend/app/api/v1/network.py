import asyncio
import logging
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import compute_sha256, is_valid_sha256
from app.models.dossier import ProjectDossier
from app.models.network import ReferralInvite, SuppressedEmail
from app.models.user import User
from app.schemas.network import (
    ContactMatchRequest,
    ContactMatchResponse,
    InviteSendRequest,
    InviteSendResponse,
    MatchedContact,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/network", tags=["Network & Viral Growth"])
PUBLIC_APP_URL = "https://studentradar.dev"


@router.post("/contacts/match", response_model=ContactMatchResponse)
async def match_contacts_by_hash(
    req: ContactMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Zero-PII contact matching: compares client-provided SHA-256 hashes against
    active users. Raw email addresses never leave the client or the database.
    """
    valid_hashes = {h.lower() for h in req.hashes if is_valid_sha256(h)}
    if not valid_hashes:
        return ContactMatchResponse(matched_contacts=[])

    suppressed_result = await db.execute(select(SuppressedEmail.email_hash))
    suppressed = {row[0] for row in suppressed_result.all()}

    result = await db.execute(select(User))
    users = result.scalars().all()

    matched_users = []
    for user in users:
        email_hash = compute_sha256(user.email)
        if email_hash in valid_hashes and email_hash not in suppressed:
            matched_users.append(user)

    if not matched_users:
        return ContactMatchResponse(matched_contacts=[])

    # One grouped query instead of one count query per matched user.
    counts_result = await db.execute(
        select(ProjectDossier.user_id, func.count(ProjectDossier.id))
        .where(ProjectDossier.user_id.in_([user.id for user in matched_users]))
        .group_by(ProjectDossier.user_id)
    )
    counts = {user_id: count for user_id, count in counts_result.all()}

    return ContactMatchResponse(
        matched_contacts=[
            MatchedContact(
                user_id=user.id,
                full_name=user.full_name or "Student Builder",
                avatar_url=user.avatar_url,
                active_dossiers_count=int(counts.get(user.id, 0)),
                is_connected=False,
            )
            for user in matched_users
        ]
    )


@router.post("/invites/send", response_model=InviteSendResponse, status_code=status.HTTP_201_CREATED)
async def send_project_invite(
    req: InviteSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Serialize invites per sender so concurrent requests cannot exceed the
    # daily cap or create duplicate pending invites.
    await db.execute(
        select(User.id).where(User.id == current_user.id).with_for_update()
    )

    # Daily outbound cap.
    count_res = await db.execute(
        select(func.count(ReferralInvite.id)).where(
            ReferralInvite.sender_user_id == current_user.id,
            ReferralInvite.created_at >= start_of_day,
        )
    )
    daily_sent = int(count_res.scalar() or 0)
    if daily_sent >= settings.INVITE_DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily invite limit reached ({settings.INVITE_DAILY_LIMIT} invites/day max).",
        )

    if req.recipient_email_hash == compute_sha256(current_user.email):
        raise HTTPException(status_code=400, detail="You cannot invite your own account.")

    # Suppression / opt-out list.
    suppressed = await db.execute(
        select(SuppressedEmail).where(SuppressedEmail.email_hash == req.recipient_email_hash)
    )
    if suppressed.scalars().first():
        raise HTTPException(status_code=400, detail="This recipient has opted out of invites.")

    d_res = await db.execute(select(ProjectDossier).where(ProjectDossier.id == req.dossier_id))
    dossier = d_res.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")
    if dossier.user_id is not None and dossier.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only invite collaborators to your own dossier.")

    # De-duplicate pending invites to the same person for the same project in
    # the last 24 hours to prevent spam.
    recent_res = await db.execute(
        select(ReferralInvite.id).where(
            ReferralInvite.sender_user_id == current_user.id,
            ReferralInvite.dossier_id == req.dossier_id,
            ReferralInvite.recipient_email_hash == req.recipient_email_hash,
            ReferralInvite.status == "pending",
            ReferralInvite.created_at >= now - timedelta(hours=24),
        )
    )
    if recent_res.scalars().first():
        raise HTTPException(
            status_code=409,
            detail="A pending invite for this recipient already exists (last 24 hours).",
        )

    token = f"ref_{uuid.uuid4().hex[:12]}"
    invite = ReferralInvite(
        sender_user_id=current_user.id,
        dossier_id=dossier.id,
        recipient_email_hash=req.recipient_email_hash,
        token=token,
        status="pending",
    )
    db.add(invite)
    await db.commit()

    share_url = f"{PUBLIC_APP_URL}/p/{dossier.slug}?ref={token}"
    msg_text = (
        f"Hey! We just published the Proof-of-Work Dossier for '{dossier.title}'. "
        f"We're looking for a {req.role_context or 'contributor'} to join. "
        f"Check out the architecture here: {share_url}"
    )
    encoded_msg = urllib.parse.quote(msg_text)
    whatsapp_url = f"https://wa.me/?text={encoded_msg}"

    if settings.ENABLE_CELERY_DISPATCH:
        try:
            from app.workers.tasks import send_invite_email

            await asyncio.to_thread(
                send_invite_email.delay,
                req.recipient_email_hash,
                token,
                dossier.title,
            )
        except Exception as exc:  # pragma: no cover - broker optional
            logger.warning("Could not dispatch invite email task: %s", exc)

    return InviteSendResponse(
        status="sent",
        invite_token=token,
        whatsapp_url=whatsapp_url,
        daily_invites_remaining=max(0, settings.INVITE_DAILY_LIMIT - (daily_sent + 1)),
    )
