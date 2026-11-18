#!/usr/bin/env python3
"""Open the public calculator and wake it if Streamlit has put it to sleep.

A plain web request is not enough. Streamlit Community Cloud only counts a
real browser visit, and a sleeping app shows a button that has to be clicked.
This script uses Playwright with Chromium. Install that in the workflow only;
it is not one of the app's dependencies.

The address is STREAMLIT_APP_URL when that variable is set. Otherwise the
public address below is used.
"""

from __future__ import annotations

import os
import re
import sys
import time

DEFAULT_URL = "https://sip-rolling-returns.streamlit.app/"
WAKE_TEXT = re.compile(r"Yes,\s*get this app back up!?", re.IGNORECASE)
# Phrases that appear on the calculator itself, not on the sleep page.
READY_TEXT = re.compile(
    r"Calculate Rolling Returns|Select Mutual Fund",
    re.IGNORECASE,
)
GOTO_TIMEOUT_MS = 60_000
# An already-open calculator can be slow on a cold start. Wait this long
# before deciding it never loaded.
AWAKE_TIMEOUT_S = 180
# After the wake-up button is clicked, Streamlit still has to start the app.
AFTER_CLICK_TIMEOUT_S = 180
# Hard stop so a stuck page cannot run on forever.
ABSOLUTE_TIMEOUT_S = 360
POLL_MS = 2_000


def resolve_url() -> str:
    configured = os.environ.get("STREAMLIT_APP_URL", "").strip()
    if not configured:
        print(
            "Keep-awake: STREAMLIT_APP_URL is not set. "
            f"Using the public address {DEFAULT_URL}",
            flush=True,
        )
        return DEFAULT_URL
    if not configured.startswith(("http://", "https://")):
        configured = "https://" + configured
    print(f"Keep-awake: using STREAMLIT_APP_URL {configured}", flush=True)
    return configured


def _note(message: str) -> None:
    print(message, flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    with open(summary, "a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def _frames(page):
    try:
        return list(page.frames)
    except Exception:
        return []


def _first_visible(frame, pattern):
    """Return a visible locator for pattern, or None. Ignore detached frames."""
    for finder in (
        lambda: frame.get_by_role("button", name=pattern),
        lambda: frame.get_by_text(pattern),
    ):
        try:
            matches = finder()
            if matches.count() > 0 and matches.first.is_visible():
                return matches.first
        except Exception:
            continue
    return None


def app_is_loaded(page) -> bool:
    for frame in _frames(page):
        if _first_visible(frame, READY_TEXT) is not None:
            return True
    return False


def find_wake_button(page):
    for frame in _frames(page):
        found = _first_visible(frame, WAKE_TEXT)
        if found is not None:
            return found
    return None


def _snippet(page) -> str:
    parts = []
    for frame in _frames(page):
        try:
            text = " ".join(frame.inner_text("body").split())
        except Exception:
            continue
        if text:
            parts.append(text[:400])
    if not parts:
        return "(no readable text on the page)"
    return " | ".join(parts)[:800]


def _save_picture(page) -> None:
    path = os.environ.get("KEEP_AWAKE_SCREENSHOT", "/tmp/keep-awake-failure.png")
    try:
        page.screenshot(path=path, full_page=True)
        _note(f"Keep-awake: saved a picture of the page to {path}")
    except Exception as exc:
        _note(f"Keep-awake: could not save a picture of the page ({exc})")


def main() -> int:
    url = resolve_url()
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        _note(
            "Keep-awake: Playwright is not installed. "
            "The workflow installs it; it is not part of the calculator."
        )
        return 1

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            _note(f"Keep-awake: opening {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                _note("Keep-awake: the address did not open within 60 seconds.")
                _save_picture(page)
                return 1

            started = time.monotonic()
            clicked_at = None
            saw_button = False
            last_click = -999.0
            while True:
                now = time.monotonic()
                if app_is_loaded(page):
                    title = ""
                    try:
                        title = page.title()
                    except Exception:
                        title = ""
                    if clicked_at is None:
                        _note(
                            "Keep-awake: the app was already awake. "
                            "The calculator is on screen."
                        )
                    else:
                        waited = int(now - clicked_at)
                        _note(
                            "Keep-awake: the app was asleep and has been woken. "
                            f"The calculator is on screen (about {waited} seconds after the click)."
                        )
                    if title:
                        _note(f"Keep-awake: page title is {title!r}.")
                    return 0

                button = find_wake_button(page)
                if button is not None:
                    saw_button = True
                if button is not None and now - last_click >= 45:
                    _note(
                        'Keep-awake: the app was asleep. '
                        'Clicking "Yes, get this app back up!".'
                    )
                    last_click = now
                    try:
                        button.scroll_into_view_if_needed(timeout=5_000)
                        button.click(timeout=15_000)
                    except Exception as exc:
                        _note(
                            "Keep-awake: the click did not go through "
                            f"({exc}). Will try again if the button is still there."
                        )
                    else:
                        if clicked_at is None:
                            clicked_at = now

                if clicked_at is not None and now - clicked_at >= AFTER_CLICK_TIMEOUT_S:
                    break
                if clicked_at is None and now - started >= AWAKE_TIMEOUT_S:
                    break
                if now - started >= ABSOLUTE_TIMEOUT_S:
                    break
                page.wait_for_timeout(POLL_MS)

            if clicked_at is None and saw_button:
                _note(
                    "Keep-awake: the wake-up button was shown, but clicking it "
                    "did not open the calculator."
                )
            elif clicked_at is None:
                _note(
                    "Keep-awake: the calculator did not load, and the wake-up "
                    "button was not shown."
                )
            else:
                _note(
                    "Keep-awake: the wake-up button was clicked, but the "
                    "calculator did not load in time."
                )
            try:
                _note(f"Keep-awake: page title is {page.title()!r}.")
            except Exception:
                pass
            _note(f"Keep-awake: page text: {_snippet(page)}")
            _save_picture(page)
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
