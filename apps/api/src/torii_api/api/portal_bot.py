"""Portal Bot API — automated eVisa submission endpoints (Thing 3).

Endpoints:
    POST /v1/cases/{case_id}/portal-bot/dispatch — trigger bot submission
    GET  /v1/cases/{case_id}/portal-bot/latest   — view active/latest job status
    GET  /v1/admin/portal-bot/jobs              — admin monitoring dashboard (Thing 3E)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep
from torii_api.db.models import Case, UserRole
from torii_api.db.session import get_session
from torii_api.services.portal_bot import (
    create_submission_job,
    get_latest_job_for_case,
    list_recent_jobs,
    run_submission_job,
)

router = APIRouter(tags=["portal-bot"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class JobStepOut(BaseModel):
    step: str
    label: str
    detail: str
    timestamp: str


class PortalJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    jurisdiction_code: str
    portal_name: str
    portal_url: str
    status: str
    attempt_count: int
    portal_reference: str | None = None
    receipt_url: str | None = None
    screenshot_url: str | None = None
    error_message: str | None = None
    steps_log: list[dict[str, Any]] = []
    proxy_used: str | None = None
    captcha_solved: bool = False
    dispatched_at: datetime | None = None
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/v1/cases/{case_id}/portal-bot/dispatch",
    response_model=PortalJobOut,
    status_code=status.HTTP_201_CREATED,
)
async def dispatch_bot(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> PortalJobOut:
    """Trigger automated eVisa submission bot for a case."""
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    if case.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.OPS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your case")

    # Create & execute job
    job = await create_submission_job(session, case_id)
    job = await run_submission_job(session, job.id)
    await session.commit()

    return PortalJobOut.model_validate(job)


@router.get(
    "/v1/cases/{case_id}/portal-bot/latest",
    response_model=PortalJobOut | None,
)
async def get_latest_job(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> PortalJobOut | None:
    """Get the latest portal bot submission job for a case."""
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    if case.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.OPS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your case")

    job = await get_latest_job_for_case(session, case_id)
    if job is None:
        return None
    return PortalJobOut.model_validate(job)


@router.get(
    "/v1/admin/portal-bot/jobs",
    response_model=list[PortalJobOut],
)
async def admin_list_jobs(
    session: SessionDep,
    user: CurrentUserDep,
    limit: int = Query(50, ge=1, le=200),
) -> list[PortalJobOut]:
    """Admin monitoring dashboard: list all recent bot submission jobs (Thing 3E)."""
    if user.role not in (UserRole.ADMIN, UserRole.OPS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin or Ops only")

    jobs = await list_recent_jobs(session, limit=limit)
    return [PortalJobOut.model_validate(j) for j in jobs]
