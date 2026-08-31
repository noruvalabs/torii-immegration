"""Reading a government page's text out of its markup.

This step had no tests, which is how it went unnoticed that it sliced the raw HTML to 8000
bytes *before* stripping tags. On a page whose `<head>` is larger than that — canada.ca is —
what reached the model was the title and nothing else: 62 characters, no error, no route
found, and an admin told the country publishes nothing.
"""

from __future__ import annotations

import httpx
import pytest

from torii_ai.services.web_fetch import RAW_HTML_LIMIT, fetch_page_text, strip_html

# A page shaped like the ones that broke it: a <head> far larger than the old 8000-byte
# slice, a nav and footer around the content, and the answer inside <main>.
BIG_HEAD = "\n".join(f'<meta name="x{i}" content="{"y" * 90}">' for i in range(200))
PAGE = f"""<!doctype html>
<html><head><title>Visas</title>{BIG_HEAD}
<style>.a {{ color: red }}</style>
<script>var tracking = {{id: "abc"}};</script>
</head>
<body class="page">
<a href="#main">Skip to main content</a>
<header>Government of Somewhere</header>
<nav><ul><li>Jobs</li><li>Taxes</li><li>Health</li></ul></nav>
<main>
  <h1>Visa types</h1>
  <p>Skilled Worker visa &mdash; costs &pound;1,334.</p>
  <script>var inline = 1;</script>
  <noscript>Enable JavaScript.</noscript>
</main>
<footer>Contact us</footer>
</body></html>"""


def test_the_content_region_wins_over_the_chrome_around_it() -> None:
    text = strip_html(PAGE)

    assert "Visa types" in text
    assert "Skilled Worker visa" in text
    # Site chrome is not the page's content, and on a real page it comes first — so a reader
    # given only the opening characters would otherwise see only this.
    for chrome in ("Skip to main content", "Government of Somewhere", "Taxes", "Contact us"):
        assert chrome not in text, chrome
    for code in ("var tracking", "var inline", "color: red", "Enable JavaScript"):
        assert code not in text, code


def test_entities_are_decoded() -> None:
    """A requirement the model reads as "&pound;1,334" is one it can misread."""
    text = strip_html(PAGE)
    assert "£1,334" in text
    assert "—" in text
    assert "&pound;" not in text


def test_a_head_bigger_than_the_old_slice_no_longer_swallows_the_page() -> None:
    """The regression itself: >8KB of <head> used to leave only the title."""
    assert len(BIG_HEAD) > 8000
    text = strip_html(PAGE)
    assert len(text) > 40
    assert "Skilled Worker visa" in text


def test_body_is_used_when_a_page_declares_no_main() -> None:
    text = strip_html(
        f"<html><head><title>T</title>{BIG_HEAD}</head>"
        "<body><nav>Menu</nav><p>Student visa route.</p></body></html>"
    )
    assert "Student visa route." in text
    assert "Menu" not in text


def test_a_fragment_with_no_body_or_main_is_used_whole() -> None:
    """The gov.uk content API returns bare fragments, not documents."""
    text = strip_html("<h2>Eligibility</h2><p>You must be 18 or over.</p>")
    assert text == "Eligibility You must be 18 or over."


def test_markup_with_no_text_at_all_is_empty_not_an_error() -> None:
    assert strip_html("") == ""
    assert strip_html("<html><head><title></title></head><body></body></html>") == ""


@pytest.mark.asyncio
async def test_fetch_reads_far_past_the_old_slice() -> None:
    """A page whose content sits beyond 8000 bytes of markup still comes back."""
    filler = "<span>.</span>" * 900  # well over 8000 bytes of markup
    body = f"<html><head><title>T</title></head><body>{filler}<p>The answer.</p></body></html>"
    assert len(body) > 8000

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body, headers={"content-type": "text/html"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        text = await fetch_page_text(client, "https://immi.example.gov/visas")

    assert "The answer." in text


@pytest.mark.asyncio
async def test_a_pathological_download_is_still_bounded() -> None:
    """The raw cap is generous, not absent."""

    async def handler(request: httpx.Request) -> httpx.Response:
        huge = "<body>" + ("a" * (RAW_HTML_LIMIT * 2)) + "</body>"
        return httpx.Response(200, text=huge, headers={"content-type": "text/html"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        text = await fetch_page_text(client, "https://immi.example.gov/huge")

    assert 0 < len(text) <= RAW_HTML_LIMIT


@pytest.mark.asyncio
async def test_a_non_html_response_is_skipped() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="%PDF-1.7", headers={"content-type": "application/pdf"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_page_text(client, "https://immi.example.gov/form.pdf") == ""


@pytest.mark.asyncio
async def test_a_failed_request_is_empty_not_an_exception() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_page_text(client, "https://immi.example.gov/down") == ""
