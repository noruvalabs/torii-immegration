"""Reading a government page's text out of its markup.

This step had no tests, which is how it went unnoticed that it sliced the raw HTML to 8000
bytes *before* stripping tags. On a page whose `<head>` is larger than that — canada.ca is —
what reached the model was the title and nothing else: 62 characters, no error, no route
found, and an admin told the country publishes nothing.
"""

from __future__ import annotations

import httpx
import pytest

from torii_ai.services.web_fetch import (
    RAW_HTML_LIMIT,
    fetch_page_details,
    fetch_page_text,
    strip_html,
)

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


@pytest.mark.asyncio
async def test_redirect_to_official_destination_accepted_with_updated_provenance() -> None:
    """Official-to-official redirects are followed and provenance records the final URL."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://mofa.go.jp/visa":
            return httpx.Response(301, headers={"location": "https://www.mofa.go.jp/j_info/visit/visa/index.html"})
        if request.url == "https://www.mofa.go.jp/j_info/visit/visa/index.html":
            return httpx.Response(200, text="<main><p>Official Japanese Visa Requirements.</p></main>", headers={"content-type": "text/html"})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        final_url, text = await fetch_page_details(client, "https://mofa.go.jp/visa", destination="JP")

    assert final_url == "https://www.mofa.go.jp/j_info/visit/visa/index.html"
    assert "Official Japanese Visa Requirements." in text


@pytest.mark.asyncio
async def test_redirect_to_untrusted_destination_is_rejected() -> None:
    """Official-to-untrusted redirects are blocked and return empty content."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://travel.state.gov/visa":
            return httpx.Response(302, headers={"location": "https://visa.gov.scamportal.com/harvest"})
        if request.url == "https://visa.gov.scamportal.com/harvest":
            return httpx.Response(200, text="<p>Malicious phishing page content</p>", headers={"content-type": "text/html"})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        final_url, text = await fetch_page_details(client, "https://travel.state.gov/visa", destination="US")

    assert final_url == ""
    assert text == ""


@pytest.mark.asyncio
async def test_redirect_chain_allowed_when_all_targets_official() -> None:
    """Redirect chains are allowed provided the final target is an authenticated official domain."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "http://state.gov/visas":
            return httpx.Response(301, headers={"location": "https://state.gov/visas"})
        if request.url == "https://state.gov/visas":
            return httpx.Response(302, headers={"location": "https://travel.state.gov/content/visas.html"})
        if request.url == "https://travel.state.gov/content/visas.html":
            return httpx.Response(200, text="<p>US Visa Information</p>", headers={"content-type": "text/html"})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        final_url, text = await fetch_page_details(client, "http://state.gov/visas", destination="US")

    assert final_url == "https://travel.state.gov/content/visas.html"
    assert "US Visa Information" in text


@pytest.mark.asyncio
async def test_redirect_loop_handled_gracefully() -> None:
    """Redirect loops are caught by TooManyRedirects handling without raising uncaught exceptions."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if "loop1" in str(request.url):
            return httpx.Response(302, headers={"location": "https://immi.homeaffairs.gov.au/loop2"})
        return httpx.Response(302, headers={"location": "https://immi.homeaffairs.gov.au/loop1"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True, max_redirects=3) as client:
        final_url, text = await fetch_page_details(client, "https://immi.homeaffairs.gov.au/loop1", destination="AU")

    assert final_url == ""
    assert text == ""


@pytest.mark.asyncio
async def test_untrusted_initial_url_rejected_without_network_io() -> None:
    """An initial URL pointing to an unauthorized domain is rejected immediately without network requests."""
    called = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, text="Should not be fetched")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        final_url, text = await fetch_page_details(client, "https://scam-visa.com/fake", destination="JP")

    assert final_url == ""
    assert text == ""
    assert called is False, "Network I/O must not be initiated for untrusted initial URLs"


@pytest.mark.asyncio
async def test_private_ip_and_internal_target_blocked_ssrf() -> None:
    """Private IP ranges, loopback, link-local metadata, and internal hostnames are blocked from fetching."""
    called = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, text="Internal metadata")

    internal_targets = [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:8000/api/secret",
        "http://localhost:3000/metrics",
        "http://10.0.0.1/admin",
        "http://192.168.1.1/setup",
        "http://[::1]/internal",
        "http://metadata.google.internal/computeMetadata/v1/",
    ]

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        for target in internal_targets:
            called = False
            final_url, text = await fetch_page_details(client, target, destination="US")
            assert final_url == "", f"Expected empty final_url for {target}"
            assert text == "", f"Expected empty text for {target}"
            assert called is False, f"Network request was initiated for {target}!"


@pytest.mark.asyncio
async def test_redirect_to_private_ip_is_blocked() -> None:
    """Redirects targeting private/link-local cloud metadata are intercepted and blocked."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://travel.state.gov/visa":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})
        if "169.254" in str(request.url):
            return httpx.Response(200, text="ami-id: ami-12345678")
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        final_url, text = await fetch_page_details(client, "https://travel.state.gov/visa", destination="US")

    assert final_url == ""
    assert text == ""

