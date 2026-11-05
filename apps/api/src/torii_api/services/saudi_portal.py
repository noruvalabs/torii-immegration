"""Saudi KSA Visa browser worker — fill public fields, fail closed.

This opens ksavisa.sa with stock Chromium (the shared PlaywrightPortalSession
from the Vietnam worker). It does not disguise the browser, create a portal
account, enter one-time codes, solve captchas, or pay the government fee.
ksavisa.sa files applications only inside the applicant's own signed-in
account, so a sign-in wall, OTP prompt, captcha and payment always hand off
to a person.
"""

from __future__ import annotations

from torii_api.services.saudi_evisa import (
    FIELD_LABELS,
    START_CLICK_PATTERNS,
    SaudiEvisaPayload,
    extract_confirmation_code,
    page_has_challenge,
)
from torii_api.services.vietnam_portal import FillResult, PortalSession

__all__ = ["run_saudi_portal"]


async def run_saudi_portal(
    session: PortalSession,
    payload: SaudiEvisaPayload,
    *,
    portal_url: str,
    allow_submit: bool = False,
) -> FillResult:
    """Drive one KSA Visa apply attempt.

    ``allow_submit`` only means "click Next/Continue after fields are filled".
    It never passes an account sign-in wall, an OTP prompt, a challenge page,
    and never enters card details.
    """
    result = FillResult()
    await session.goto(portal_url)
    result.url = await session.current_url()
    result.html = await session.content()
    if page_has_challenge(result.html, result.url):
        result.challenge = True
        result.screenshot = await _safe_screenshot(session)
        return result

    for pattern in START_CLICK_PATTERNS[:3]:
        if await session.click_by_name(pattern):
            result.clicks.append(pattern)
            result.html = await session.content()
            result.url = await session.current_url()
            if page_has_challenge(result.html, result.url):
                result.challenge = True
                result.screenshot = await _safe_screenshot(session)
                return result

    for key, labels in FIELD_LABELS.items():
        value = payload.values.get(key) or ""
        if not value:
            result.unfilled.append(key)
            continue
        if await session.fill_by_label(labels, value):
            result.filled.append(key)
        else:
            result.unfilled.append(key)

    result.html = await session.content()
    result.url = await session.current_url()
    if page_has_challenge(result.html, result.url):
        result.challenge = True
        result.screenshot = await _safe_screenshot(session)
        return result

    if allow_submit and not result.challenge:
        for pattern in ("Next", "Continue", "Confirm"):
            if await session.click_by_name(pattern):
                result.clicks.append(pattern)
                break
        result.html = await session.content()
        result.url = await session.current_url()
        if page_has_challenge(result.html, result.url):
            result.challenge = True

    result.screenshot = await _safe_screenshot(session)
    result.confirmation_code = extract_confirmation_code(result.html)
    return result


async def _safe_screenshot(session: PortalSession) -> bytes | None:
    try:
        return await session.screenshot()
    except Exception:
        return None
