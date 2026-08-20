"""Credit economy, top-up packs, and atomic consumption ledger."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep, SessionDep
from torii_api.db.models import Case, CreditTransaction, User

router = APIRouter(prefix="/v1/credits", tags=["credits"])

# Simplified 1-Credit = 1-Full-Application Pass Packaging
CREDIT_PACKS = [
    {
        "id": "starter",
        "name": "1 Full Application Pass",
        "name_ja": "1件 申請パス",
        "credits": 1,
        "price_usd": 19.00,
        "price_jpy": 2800,
        "badge": None,
        "description": "Complete filing kit for 1 visa application (all OCR scans, AI guidance & official PDFs included)",
        "description_ja": "1件のビザ申請に必要な全書類（OCR抽出・AI法令案内・公的PDF一式）の完全作成・出力",
    },
    {
        "id": "standard",
        "name": "3-Application Bundle",
        "name_ja": "3件 ファミリー・更新パック (人気)",
        "credits": 3,
        "price_usd": 39.00,
        "price_jpy": 5800,
        "badge": "Popular · Save 32%",
        "description": "3 Full Application Passes ($13.00 / ¥1,930 per case). Ideal for families, renewals, or multiple routes",
        "description_ja": "3件分の申請パス（1件あたり¥1,930）。配偶者・扶養家族、更新、複数カテゴリ申請に最適",
    },
    {
        "id": "family",
        "name": "5-Application Agency Pack",
        "name_ja": "5件 法人・複数申請パック",
        "credits": 5,
        "price_usd": 59.00,
        "price_jpy": 8900,
        "badge": "Best Value · Save 38%",
        "description": "5 Full Application Passes ($11.80 / ¥1,780 per case) for agencies, employers, or multi-year filings",
        "description_ja": "5件分の申請パス（1件あたり¥1,780）。企業スポンサー、代理申請、複数年管理向け",
    },
]


class CreditTransactionOut(BaseModel):
    id: int
    amount: int
    balance_after: int
    feature: str
    case_id: int | None = None
    description: str
    created_at: str

    model_config = {"from_attributes": True}


class CreditBalanceOut(BaseModel):
    credit_balance: int
    user_id: int
    email: str
    packs: list[dict[str, Any]]
    recent_transactions: list[CreditTransactionOut]


class ConsumeIn(BaseModel):
    feature: Literal["ocr_extraction", "ai_query", "case_unlock", "pdf_export", "translation"]
    amount: int = Field(gt=0, description="Amount of credits to consume")
    case_id: int | None = None
    description: str = Field(min_length=1, max_length=256)


class ConsumeOut(BaseModel):
    success: bool
    credits_consumed: int
    credit_balance: int
    feature: str


class TopUpIn(BaseModel):
    pack_id: Literal["starter", "standard", "family"]
    currency: Literal["usd", "jpy"] = "usd"


class TopUpOut(BaseModel):
    success: bool
    credits_added: int
    credit_balance: int
    pack_name: str
    message: str


class UnlockCaseOut(BaseModel):
    success: bool
    already_unlocked: bool
    case_id: int
    case_reference: str
    credits_consumed: int
    credit_balance: int


@router.get("/balance", response_model=CreditBalanceOut)
async def get_credit_balance(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> CreditBalanceOut:
    """Return user's real-time credit balance, available packs, and recent ledger."""
    # Ensure User object is freshly loaded
    user = await session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch last 15 credit transactions
    stmt = (
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
        .order_by(desc(CreditTransaction.id))
        .limit(15)
    )
    result = await session.execute(stmt)
    tx_list = result.scalars().all()

    tx_outs = [
        CreditTransactionOut(
            id=tx.id,
            amount=tx.amount,
            balance_after=tx.balance_after,
            feature=tx.feature,
            case_id=tx.case_id,
            description=tx.description,
            created_at=tx.created_at.isoformat() if hasattr(tx, "created_at") and tx.created_at else "",
        )
        for tx in tx_list
    ]

    return CreditBalanceOut(
        credit_balance=user.credit_balance,
        user_id=user.id,
        email=user.email,
        packs=CREDIT_PACKS,
        recent_transactions=tx_outs,
    )


@router.post("/consume", response_model=ConsumeOut)
async def consume_credits(
    payload: ConsumeIn,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ConsumeOut:
    """Atomically consume credits for an AI or document feature."""
    user = await session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.credit_balance < payload.amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": f"Insufficient credits. Required: {payload.amount}, Current balance: {user.credit_balance}.",
                "required": payload.amount,
                "current_balance": user.credit_balance,
                "shortage": payload.amount - user.credit_balance,
            },
        )

    # Deduct atomically
    user.credit_balance -= payload.amount
    tx = CreditTransaction(
        user_id=user.id,
        amount=-payload.amount,
        balance_after=user.credit_balance,
        feature=payload.feature,
        case_id=payload.case_id,
        description=payload.description,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(user)

    return ConsumeOut(
        success=True,
        credits_consumed=payload.amount,
        credit_balance=user.credit_balance,
        feature=payload.feature,
    )


@router.post("/top-up", response_model=TopUpOut)
async def top_up_credits(
    payload: TopUpIn,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> TopUpOut:
    """Purchase a credit pack and credit user's balance."""
    pack = next((p for p in CREDIT_PACKS if p["id"] == payload.pack_id), None)
    if not pack:
        raise HTTPException(status_code=400, detail="Invalid credit pack ID")

    user = await session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    credits_to_add = pack["credits"]
    user.credit_balance += credits_to_add

    price_str = f"${pack['price_usd']}" if payload.currency == "usd" else f"¥{pack['price_jpy']:,}"
    tx = CreditTransaction(
        user_id=user.id,
        amount=credits_to_add,
        balance_after=user.credit_balance,
        feature="top_up",
        description=f"Purchased {pack['name']} ({credits_to_add} Credits for {price_str})",
    )
    session.add(tx)
    await session.commit()
    await session.refresh(user)

    return TopUpOut(
        success=True,
        credits_added=credits_to_add,
        credit_balance=user.credit_balance,
        pack_name=pack["name"],
        message=f"Successfully credited {credits_to_add} credits to your account.",
    )


@router.post("/unlock-case/{case_id}", response_model=UnlockCaseOut)
async def unlock_case_packet(
    case_id: int,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> UnlockCaseOut:
    """Unlock the official dossier packet for a case (cost: 30 credits or free if already unlocked)."""
    case = await session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    user = await session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if case.is_entitled:
        return UnlockCaseOut(
            success=True,
            already_unlocked=True,
            case_id=case.id,
            case_reference=case.reference,
            credits_consumed=0,
            credit_balance=user.credit_balance,
        )

    # Cost to unlock official dossier packet: 1 Application Pass
    UNLOCK_COST = 1

    if user.credit_balance < UNLOCK_COST:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": f"Case unlock requires 1 Application Pass. Current balance: {user.credit_balance}.",
                "required": UNLOCK_COST,
                "current_balance": user.credit_balance,
                "shortage": UNLOCK_COST - user.credit_balance,
            },
        )

    # Deduct and mark entitled
    user.credit_balance -= UNLOCK_COST
    case.is_entitled = True

    tx = CreditTransaction(
        user_id=user.id,
        amount=-UNLOCK_COST,
        balance_after=user.credit_balance,
        feature="case_unlock",
        case_id=case.id,
        description=f"Unlocked official dossier packet for case {case.reference}",
    )
    session.add(tx)
    await session.commit()
    await session.refresh(user)
    await session.refresh(case)

    return UnlockCaseOut(
        success=True,
        already_unlocked=False,
        case_id=case.id,
        case_reference=case.reference,
        credits_consumed=UNLOCK_COST,
        credit_balance=user.credit_balance,
    )
