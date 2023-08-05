import asyncio
from collections.abc import Generator

import pytest

from .database_fixture import database as database
from .database_fixture import db_client as db_client
from .database_fixture import db_connect_string as db_connect_string


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
