import asyncio
from collections.abc import Generator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Overriding the default `event_loop` pytest-asyncio test fixture
    to keep the loop open for the full duration of testing.
    """
    loop: asyncio.AbstractEventLoop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    yield loop
    loop.close()
