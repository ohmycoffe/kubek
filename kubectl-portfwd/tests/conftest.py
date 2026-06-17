"""Shared pytest fixtures for the portfwd test-suite.

Reusable test doubles live in `fakes.py`; this module exposes them as fixtures
and centralizes the one place `patch` is still needed: intercepting the event
loop's signal handlers so tests can simulate Ctrl+C.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
import pytest_asyncio
from portfwd.application.ports import KubeGateway
from portfwd_test_utils.fakes import make_fake_api


@pytest.fixture
def fake_api() -> KubeGateway:
    return make_fake_api()


@pytest_asyncio.fixture
async def captured_signal_handlers() -> AsyncIterator[dict[int, object]]:
    """Intercept the loop's signal registration so tests can fire Ctrl+C manually.

    The streamer registers real SIGINT/SIGTERM handlers on the running loop.
    This fixture records the callbacks in a dict (keyed by signal number) instead,
    letting a test invoke `handlers[signal.SIGINT]()` to simulate a shutdown.
    """
    handlers: dict[int, object] = {}
    loop = asyncio.get_running_loop()

    def register(sig: int, callback: object) -> None:
        handlers[sig] = callback

    with (
        patch.object(loop, "add_signal_handler", side_effect=register),
        patch.object(loop, "remove_signal_handler"),
    ):
        yield handlers
