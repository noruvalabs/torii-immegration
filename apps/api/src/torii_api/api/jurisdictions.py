"""Jurisdictions — a thin, real resource that exercises the DB seam end to end.

Onboarding offers only live jurisdictions (US-01.3); this is the read/write surface behind
that. Kept intentionally minimal — it is the proof that the async engine, session dependency,
and migrations all line up, and the first slice of the "configure a jurisdiction" story (US-29).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.db.models import Jurisdiction
from torii_api.db.session import get_session

router = APIRouter(prefix="/v1/jurisdictions", tags=["jurisdictions"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class JurisdictionIn(BaseModel):
    code: str = Field(min_length=2, max_length=8, examples=["JP"])
    name: str = Field(min_length=1, max_length=128, examples=["Japan"])
    is_live: bool = False


class JurisdictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    is_live: bool


@router.get("", response_model=list[JurisdictionOut])
async def list_jurisdictions(session: SessionDep, live_only: bool = False) -> list[Jurisdiction]:
    """List jurisdictions; ``live_only=true`` returns just the ones offered to applicants."""
    stmt = select(Jurisdiction).order_by(Jurisdiction.code)
    if live_only:
        stmt = stmt.where(Jurisdiction.is_live.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=JurisdictionOut, status_code=status.HTTP_201_CREATED)
async def create_jurisdiction(payload: JurisdictionIn, session: SessionDep) -> Jurisdiction:
    """Create a jurisdiction (idempotency is by unique ``code``)."""
    jurisdiction = Jurisdiction(
        code=payload.code.upper(), name=payload.name, is_live=payload.is_live
    )
    session.add(jurisdiction)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"jurisdiction '{payload.code.upper()}' already exists",
        ) from exc
    await session.refresh(jurisdiction)
    return jurisdiction
