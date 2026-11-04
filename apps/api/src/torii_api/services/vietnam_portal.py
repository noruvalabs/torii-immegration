"""Vietnam eVisa browser worker — fill public fields, fail closed.

This opens the official site with stock Chromium. It does not disguise the browser,
solve captchas, or pay the government fee. Captcha and payment always hand off to a person.
"""

from __future__ import annotations

import re
from typing import Protocol

from torii_api.services.vietnam_evisa import (
    FIELD_LABELS,
    START_CLICK_PATTERNS,
    VietnamEvisaPayload,
    page_has_challenge,
)


class PortalSession(Protocol):
    async def goto(self, url: str) -> None: ...
    async def content(self) -> str: ...
    async def current_url(self) -> str: ...
    async def screenshot(self) -> bytes: ...
    async def click_by_name(self, pattern: str) -> bool: ...
    async def fill_by_label(self, labels: tuple[str, ...], value: str) -> bool: ...
    async def close(self) -> None: ...


class FillResult:
    def __init__(self) -> None:
        self.filled: list[str] = []
        self.unfilled: list[str] = []
        self.clicks: list[str] = []
        self.challenge = False
        self.confirmation_code: str | None = None
        self.html: str = ""
        self.url: str = ""
        self.screenshot: bytes | None = None


async def run_vietnam_portal(
    session: PortalSession,
    payload: VietnamEvisaPayload,
    *,
    portal_url: str,
    allow_submit: bool = False,
) -> FillResult:
    """Drive one Vietnam eVisa apply attempt.

    ``allow_submit`` only means "click Next/Continue after fields are filled".
    It never bypasses a challenge page and never enters card details.
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
    from torii_api.services.vietnam_evisa import extract_confirmation_code

    result.confirmation_code = extract_confirmation_code(result.html)
    return result


async def _safe_screenshot(session: PortalSession) -> bytes | None:
    try:
        return await session.screenshot()
    except Exception:
        return None


class PlaywrightPortalSession:
    """Thin Playwright adapter. Stock Chromium only — no stealth, no proxy."""

    def __init__(self, page: object, browser: object, playwright: object) -> None:
        self._page = page
        self._browser = browser
        self._playwright = playwright

    @classmethod
    async def launch(
        cls, *, headless: bool = True, timeout_ms: int = 45_000
    ) -> PlaywrightPortalSession:
        try:
            from playwright.async_api import async_playwright  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. From apps/api run: "
                "uv add playwright && uv run playwright install chromium"
            ) from exc

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=headless)
        page = await browser.new_page()
        page.set_default_timeout(timeout_ms)
        return cls(page, browser, playwright)

    async def goto(self, url: str) -> None:
        await self._page.goto(url, wait_until="domcontentloaded")  # type: ignore[attr-defined]

    async def content(self) -> str:
        return await self._page.content()  # type: ignore[attr-defined]

    async def current_url(self) -> str:
        return str(self._page.url)  # type: ignore[attr-defined]

    async def screenshot(self) -> bytes:
        return await self._page.screenshot(full_page=True)  # type: ignore[attr-defined]

    async def click_by_name(self, pattern: str) -> bool:
        regex = re.compile(pattern, re.IGNORECASE)
        locators = (
            self._page.get_by_role("button", name=regex),  # type: ignore[attr-defined]
            self._page.get_by_role("link", name=regex),  # type: ignore[attr-defined]
            self._page.get_by_text(regex),  # type: ignore[attr-defined]
        )
        for locator in locators:
            try:
                first = locator.first
                if await first.count() == 0:
                    continue
                await first.click(timeout=3_000)
                return True
            except Exception:
                continue
        return False

    async def fill_by_label(self, labels: tuple[str, ...], value: str) -> bool:
        for label in labels:
            regex = re.compile(re.escape(label), re.IGNORECASE)
            candidates = (
                self._page.get_by_label(regex),  # type: ignore[attr-defined]
                self._page.get_by_placeholder(regex),  # type: ignore[attr-defined]
            )
            for locator in candidates:
                first = locator.first  # assigned once per locator, always bound in try
                try:
                    if await first.count() == 0:
                        continue
                    await first.fill(value, timeout=2_000)
                    return True
                except Exception:
                    try:
                        await first.select_option(label=value, timeout=2_000)
                        return True
                    except Exception:
                        continue
        return False

    async def close(self) -> None:
        try:
            await self._browser.close()  # type: ignore[attr-defined]
        finally:
            await self._playwright.stop()  # type: ignore[attr-defined]
