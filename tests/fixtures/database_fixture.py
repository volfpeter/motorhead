import asyncio

import pytest
from motor.core import AgnosticClient, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from pytest_docker.plugin import Services as DockerServices


@pytest.fixture(scope="session")
def db_connect_string(*, docker_ip: str, docker_services: DockerServices) -> str:
    return f"mongodb://{docker_ip}:{docker_services.port_for('db', 27017)}"


@pytest.fixture(scope="session")
def db_client(*, db_connect_string: str) -> AgnosticClient:
    return AsyncIOMotorClient(db_connect_string)


def _ping_database(db_client: AgnosticClient) -> bool:
    try:
        db_client.admin.command("ping")
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def database(
    *,
    db_client: AgnosticClient,
    docker_services: DockerServices,
    event_loop: asyncio.AbstractEventLoop,
) -> AgnosticDatabase:
    docker_services.wait_until_responsive(
        timeout=30,
        pause=0.5,
        check=lambda: _ping_database(db_client),
    )

    return db_client["motorhead-test-db"]
