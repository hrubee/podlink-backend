from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.api import deps, auth_deps
from app.models.user import User, UserRole
from app.models.safety import UserReport, ReportStatus, AuditLog
from app.models.matches import Match
from app.models.chat import ChatMessage
import redis

router = APIRouter()

# Security: Only admins can access these endpoints
admin_required = auth_deps.RoleChecker([UserRole.ADMIN])

@router.get("/stats")
async def get_system_stats(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(admin_required)
):
    """Aggregate high-level metrics for the Admin Dashboard."""
    return {
        "users": db.query(User).count(),
        "matches": db.query(Match).count(),
        "messages": db.query(ChatMessage).count(),
        "pending_reports": db.query(UserReport).filter(UserReport.status == ReportStatus.PENDING).count()
    }

@router.get("/reports")
async def get_reports(
    status: ReportStatus = None,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(admin_required)
):
    query = db.query(UserReport)
    if status:
        query = query.filter(UserReport.status == status)
    return query.order_by(UserReport.created_at.desc()).all()

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    reason: str,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    
    # Audit trail
    log = AuditLog(
        admin_id=current_admin.id,
        action="BAN_USER",
        target_id=user_id,
        metadata_json=reason
    )
    db.add(log)
    db.commit()
    return {"status": "success", "message": f"User {user_id} has been banned."}
