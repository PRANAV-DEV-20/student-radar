import uuid
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import compute_sha256, is_valid_sha256
from app.models.user import User
from app.models.dossier import ProjectDossier
from app.models.network import ReferralInvite, SuppressedEmail
from app.schemas.network import (
    ContactMatchRequest,
    ContactMatchResponse,
    MatchedContact,
    InviteSendRequest,
    InviteSendResponse
)
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/network", tags=["Network & Viral Growth"])

@router.post("/contacts/match", response_model=ContactMatchResponse)
async def match_contacts_by_hash(
    req: ContactMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Zero-PII Contact Matching:
    Compares client-provided SHA-256 hashes against active users.
    No raw email addresses are ever transmitted or stored.
    """
    # Sanitize inputs to valid 64-character hex hashes
    valid_hashes = set(h.lower() for h in req.hashes if is_valid_sha256(h))
    if not valid_hashes:
        return ContactMatchResponse(matched_contacts=[])

    # Fetch users and compare SHA-256
    result = await db.execute(select(User))
    users = result.scalars().all()

    matched = []
    for u in users:
        u_hash = compute_sha256(u.email)
        if u_hash in valid_hashes:
            # Count active dossiers
            d_count_res = await db.execute(
                select(func.count(ProjectDossier.id)).where(ProjectDossier.user_id == u.id)
            )
            count = d_count_res.scalar() or 0

            matched.append(
                MatchedContact(
                    user_id=u.id,
                    full_name=u.full_name or "Student Builder",
                    avatar_url=u.avatar_url,
                    active_dossiers_count=count,
                    is_connected=False
                )
            )

    return ContactMatchResponse(matched_contacts=matched)

@router.post("/invites/send", response_model=InviteSendResponse, status_code=status.HTTP_201_CREATED)
async def send_project_invite(
    req: InviteSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Enforce Redis / DB rate limit: max 10 outbound invites per day
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count_res = await db.execute(
        select(func.count(ReferralInvite.id)).where(
            ReferralInvite.sender_user_id == current_user.id,
            ReferralInvite.created_at >= start_of_day
        )
    )
    daily_sent = count_res.scalar() or 0
    if daily_sent >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily invite limit reached (10 invites/day max)."
        )

    # Check suppression
    suppressed = await db.execute(
        select(SuppressedEmail).where(SuppressedEmail.email_hash == req.recipient_email_hash)
    )
    if suppressed.scalars().first():
        raise HTTPException(status_code=400, detail="This recipient has opted out of invites.")

    # Retrieve dossier for title
    d_res = await db.execute(select(ProjectDossier).where(ProjectDossier.id == req.dossier_id))
    dossier = d_res.scalars().first()
    dossier_title = dossier.title if dossier else "our new build"
    slug = dossier.slug if dossier else "project"

    token = f"ref_{uuid.uuid4().hex[:12]}"
    invite = ReferralInvite(
        sender_user_id=current_user.id,
        recipient_email_hash=req.recipient_email_hash,
        token=token,
        status="pending"
    )
    db.add(invite)
    await db.commit()

    # Generate wa.me deep link
    share_url = f"https://studentradar.dev/p/{slug}?ref={token}"
    msg_text = (
        f"Hey! We just published the Proof-of-Work Dossier for '{dossier_title}'. "
        f"We're looking for a {req.role_context or 'contributor'} to join. "
        f"Check out the architecture here: {share_url}"
    )
    encoded_msg = urllib.parse.quote(msg_text)
    whatsapp_url = f"https://wa.me/?text={encoded_msg}"

    return InviteSendResponse(
        status="sent",
        invite_token=token,
        whatsapp_url=whatsapp_url,
        daily_invites_remaining=max(0, 9 - daily_sent)
    )

