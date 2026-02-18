from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import redis
import logging

from app.services.matching import MatchingService
from app.services.payments import PaymentService
from app.api import deps, auth_deps
from app.models.safety import UserReport
from app.models.user import User, UserRole
from app.models.matches import Interaction, InteractionType, Match
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class LikeRequest(BaseModel):
    target_id: int

class ReportCreate(BaseModel):
    target_id: int
    reason: str
    details: str = None


# ── Semantic Search ───────────────────────────────────────────────────────────

@router.get("/search")
async def semantic_search(
    q: str,
    limit: int = 10,
    current_user: User = Depends(auth_deps.get_current_user)
):
    """Proxy semantic search to the ML service."""
    import httpx
    from app.core.config import settings
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.ML_SERVICE_URL}/search",
                json={"query": q, "top_k": limit},
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ML search unavailable: {e}")


# ── Recommendation Feed ───────────────────────────────────────────────────────

@router.get("/feed")
async def get_recommendation_feed(
    limit: int = 20,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    """
    Returns a hybrid-ranked feed of potential matches.
    - Excludes already-interacted users
    - Sends rich profile signals to ML service for ranking
    - Falls back to content-based local sort if ML service is down
    """
    import httpx
    from app.core.config import settings

    # 1. Determine opposite role
    target_role = UserRole.GUEST if current_user.role == UserRole.HOST else UserRole.HOST

    # 2. Get already-interacted IDs
    interacted_ids = [
        str(row[0]) for row in
        db.query(Interaction.target_id)
          .filter(Interaction.actor_id == str(current_user.id))
          .all()
    ]
    interacted_ids.append(str(current_user.id))

    # 3. Fetch candidates (up to 150 for good ranking diversity)
    candidates = db.query(User).filter(
        User.role == target_role,
        User.onboarded == True,
        User.is_public == True,
        User.is_active == True,
        ~User.id.in_(interacted_ids)
    ).limit(150).all()

    if not candidates:
        return {"profiles": [], "total_candidates": 0}

    # 4. Get total interaction count for NCF blend weight
    total_interactions = db.query(Interaction).filter(
        Interaction.interaction_type == InteractionType.LIKE
    ).count()

    # 5. Build rich ML request — all signals from onboarding
    def _user_meta(u: User) -> dict:
        return {
            "topics": u.topics or [],
            "bio": u.bio or "",
            "target_audience": u.target_audience or "",
            "language": u.language or "English",
            "engagement_style": u.engagement_style or [],
            "interview_format": u.interview_format or "both",
            "episode_length_pref": u.episode_length_pref or "45-60",
            "content_rating": u.content_rating or "clean",
            "fee_expectation": u.fee_expectation or "free",
        }

    ml_payload = {
        "user_id": current_user.id,
        "user_metadata": _user_meta(current_user),
        "candidates": [
            {"id": c.id, **_user_meta(c)}
            for c in candidates
        ],
        "total_interactions": total_interactions,
    }

    # 6. Call ML service
    ranked_ids = None
    ml_scores = {}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/rank",
                json=ml_payload,
                timeout=8.0
            )
            resp.raise_for_status()
            data = resp.json()
            ranked_ids = [int(rid) for rid in data.get("ranked_ids", [])]
            # Store scores for response enrichment
            for item in data.get("debug", []):
                ml_scores[item["id"]] = item
    except Exception as e:
        logger.warning(f"ML service unavailable, using local fallback: {e}")

    # 7. Local fallback — simple topic overlap sort
    if ranked_ids is None:
        user_topics = set(t.lower() for t in (current_user.topics or []))
        def _local_score(c: User) -> float:
            cand_topics = set(t.lower() for t in (c.topics or []))
            overlap = len(user_topics & cand_topics) / max(len(user_topics | cand_topics), 1)
            lang_match = 1.0 if (c.language or "English").lower() == (current_user.language or "English").lower() else 0.0
            return overlap * 0.7 + lang_match * 0.3
        candidates.sort(key=_local_score, reverse=True)
        ranked_ids = [c.id for c in candidates]

    # 8. Build ordered profile list
    id_map = {c.id: c for c in candidates}
    profiles = []
    for rid in ranked_ids:
        if rid not in id_map:
            continue
        u = id_map[rid]
        score_info = ml_scores.get(rid, {})
        profiles.append({
            "id": u.id,
            "name": u.full_name,
            "bio": u.bio,
            "image_url": u.avatar_url,
            "location": u.location,
            "topics": u.topics,
            "language": u.language,
            "role": u.role,
            "subtitle": (
                u.host_details.get("podcast_name") if u.role == UserRole.HOST
                else u.guest_details.get("expertise_areas")
            ),
            "audience_size": u.host_details.get("audience_size") if u.role == UserRole.HOST else None,
            "experience_years": u.guest_details.get("experience_years") if u.role == UserRole.GUEST else None,
            "past_appearances": u.guest_details.get("past_appearances") if u.role == UserRole.GUEST else None,
            "interview_format": u.interview_format,
            "episode_length_pref": u.episode_length_pref,
            "social_links": u.social_links or {},
            "match_score": score_info.get("score"),
            "content_score": score_info.get("content_score"),
            "ncf_score": score_info.get("ncf_score"),
        })

    return {
        "profiles": profiles[:limit],
        "total_candidates": len(candidates),
        "ncf_active": total_interactions >= 50,
        "total_interactions": total_interactions,
    }


# ── Like / Dislike ────────────────────────────────────────────────────────────

@router.post("/like")
async def like_user(
    request: LikeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    payment_service = PaymentService(db, r)
    current_user_id = str(current_user.id)

    if not await payment_service.check_feature_access(current_user_id):
        raise HTTPException(status_code=402, detail="Outreach limit reached. Upgrade to Premium.")

    service = MatchingService(db, r)
    is_match = await service.handle_like(current_user_id, request.target_id)

    if not is_match:
        await payment_service.increment_quota(current_user_id)

    # Auto-trigger NCF retraining every 50 new likes
    total_likes = db.query(Interaction).filter(
        Interaction.interaction_type == InteractionType.LIKE
    ).count()
    if total_likes > 0 and total_likes % 50 == 0:
        background_tasks.add_task(_trigger_ncf_retrain, db)

    return {
        "status": "success",
        "is_match": is_match,
        "message": "It's a match! 🎉" if is_match else "Like recorded."
    }


@router.post("/dislike")
async def dislike_user(
    request: LikeRequest,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    service = MatchingService(db, r)
    await service.handle_dislike(str(current_user.id), request.target_id)
    return {"status": "success", "message": "Preference recorded."}


# ── NCF Auto-Retrain ──────────────────────────────────────────────────────────

async def _trigger_ncf_retrain(db: Session):
    """Background task: pull all interactions from DB and send to ML service for retraining."""
    import httpx
    from app.core.config import settings

    try:
        interactions = db.query(Interaction).all()
        payload = {
            "interactions": [
                {
                    "actor_id": int(i.actor_id),
                    "target_id": int(i.target_id),
                    "type": i.interaction_type.value,
                }
                for i in interactions
            ],
            "epochs": 10,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/train",
                json=payload,
                timeout=30.0
            )
            logger.info(f"NCF retrain triggered: {resp.json()}")
    except Exception as e:
        logger.warning(f"NCF retrain trigger failed: {e}")


# ── Reports & Matches ─────────────────────────────────────────────────────────

@router.post("/report")
async def submit_report(
    report: ReportCreate,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    db.add(UserReport(
        reporter_id=current_user.id,
        target_id=report.target_id,
        reason=report.reason,
        details=report.details
    ))
    db.commit()
    return {"status": "success", "message": "Report submitted for review."}


@router.get("/matches")
async def get_matches(
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    service = MatchingService(db, r)
    match_ids = await service.get_active_matches(str(current_user.id))
    return {"matches": match_ids}


@router.post("/unmatch")
async def unmatch_user(
    request: LikeRequest,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    service = MatchingService(db, r)
    await service.unmatch(str(current_user.id), request.target_id)
    return {"status": "success", "message": "Unmatched."}
