"""Complementary co-builder matching.

The product brief specifies pgvector cosine similarity between a dossier's
``missing_roles_embedding`` and a user's ``skills_embedding``. When those
embeddings are available we blend them with a deterministic token-overlap
score derived from verified skills and portfolio tech stacks. This keeps the
endpoint useful for freshly seeded / partially enriched accounts too.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.dossier import ProjectDossier
from app.models.user import User
from app.schemas.matchmaking import CoBuilderMatch, CoBuilderMatchResponse
from app.services.dedup_service import dedup_service

_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "into",
    "your",
    "our",
    "that",
    "this",
    "role",
    "lead",
    "senior",
    "junior",
    "engineer",
    "developer",
    "specialist",
    "researcher",
    "designer",
    "manager",
    "coordinator",
    "analyst",
}


def _tokens(value: str) -> Set[str]:
    chunks = re.split(r"[^a-z0-9+#.]+", (value or "").lower())
    return {
        chunk.strip(".")
        for chunk in chunks
        if len(chunk.strip(".")) >= 2 and chunk.strip(".") not in _STOPWORDS
    }


def _role_coverage(role: str, skill_tokens: Set[str]) -> float:
    role_tokens = _tokens(role)
    if not role_tokens:
        return 0.0
    matched = 0
    for token in role_tokens:
        if token in skill_tokens:
            matched += 1
        elif any(token in skill or skill in token for skill in skill_tokens):
            matched += 0.75
    return min(1.0, matched / len(role_tokens))


def _candidate_skills(user: User) -> Tuple[List[str], List[ProjectDossier]]:
    dossiers: Sequence[ProjectDossier] = list(user.dossiers or [])
    skills: List[str] = [str(skill) for skill in (user.verified_skills or []) if str(skill).strip()]
    for dossier in dossiers:
        for item in dossier.tech_stack or []:
            value = str(item).strip()
            if value:
                skills.append(value)
    # de-duplicate while preserving order
    return list(dict.fromkeys(skills)), list(dossiers)


def _embedding_similarity(user: User, dossier: ProjectDossier) -> float:
    user_embedding = list(user.skills_embedding or [])
    role_embedding = list(dossier.missing_roles_embedding or [])
    if not user_embedding or not role_embedding:
        return 0.0
    return dedup_service.cosine_similarity(user_embedding, role_embedding)


def _missing_role_names(dossier: ProjectDossier) -> List[str]:
    roles: List[str] = []
    for item in dossier.missing_roles or []:
        if isinstance(item, dict):
            role = str(item.get("role") or "").strip()
        else:
            role = str(item).strip()
        if role:
            roles.append(role)
    return roles


class Matchmaker:
    async def match_cobuilders(
        self,
        db: AsyncSession,
        dossier: ProjectDossier,
        limit: int = 5,
    ) -> CoBuilderMatchResponse:
        roles = _missing_role_names(dossier)
        limit = max(1, min(limit, 20))

        query = (
            select(User)
            .options(selectinload(User.dossiers))
            .where(User.id != dossier.user_id if dossier.user_id else True)
            .limit(settings.MATCHMAKING_CANDIDATE_LIMIT)
        )
        result = await db.execute(query)
        candidates: Iterable[User] = result.scalars().all()

        scored: List[Tuple[float, CoBuilderMatch]] = []
        for user in candidates:
            skills, dossiers = _candidate_skills(user)
            skill_tokens: Set[str] = set()
            for skill in skills:
                skill_tokens.update(_tokens(skill))

            role_scores = [(role, _role_coverage(role, skill_tokens)) for role in roles]
            matched_roles = [role for role, score in role_scores if score >= 0.34]
            best_role_score = max((score for _, score in role_scores), default=0.0)
            embedding_score = _embedding_similarity(user, dossier)

            if roles:
                score = (0.72 * best_role_score) + (0.28 * embedding_score)
            else:
                # No explicit gap: rank complementary portfolios by semantic fit
                # and breadth of verified artifacts.
                breadth = min(1.0, len(skills) / 8.0)
                score = (0.55 * embedding_score) + (0.30 * breadth) + (0.15 * min(1.0, len(dossiers) / 3.0))

            if user.active_persona_id and user.active_persona_id != dossier.domain_persona:
                score += 0.03  # cross-domain complementarity bonus

            score = round(max(0.05, min(0.99, score)), 2)

            if matched_roles:
                reason = (
                    f"Verified portfolio covers {', '.join(matched_roles[:2])}"
                    f" using {', '.join(skills[:3]) or 'documented project artifacts'}."
                )
            elif skills:
                reason = (
                    "Complementary verified skills "
                    f"({', '.join(skills[:3])}) can extend this project's architecture."
                )
            else:
                reason = "Active builder in an adjacent persona with a public proof-of-work dossier."

            scored.append(
                (
                    score,
                    CoBuilderMatch(
                        user_id=user.id,
                        full_name=user.full_name or "Student Builder",
                        avatar_url=user.avatar_url,
                        campus_or_org=user.campus_or_org,
                        city=user.city,
                        active_persona_id=user.active_persona_id or settings.DEFAULT_PERSONA,
                        verified_skills=skills[:12],
                        matched_roles=matched_roles[:4],
                        match_score=score,
                        match_reason=reason,
                        active_dossiers_count=len(dossiers),
                        is_connected=False,
                    ),
                )
            )

        scored.sort(
            key=lambda pair: (pair[0], pair[1].active_dossiers_count),
            reverse=True,
        )

        return CoBuilderMatchResponse(
            dossier_id=dossier.id,
            dossier_slug=dossier.slug,
            missing_roles=roles,
            matches=[match for _, match in scored[:limit]],
        )


matchmaker = Matchmaker()
