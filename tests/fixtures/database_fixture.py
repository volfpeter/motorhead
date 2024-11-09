from typing import Any

import pymongo
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from pytest_docker.plugin import Services as DockerServices

from motorhead.typing import AgnosticClient, AgnosticDatabase


@pytest.fixture(scope="session")
def db_connect_string(*, docker_ip: str, docker_services: DockerServices) -> str:
    return f"mongodb://{docker_ip}:{docker_services.port_for('db', 27017)}"


@pytest.fixture(scope="session")
def db_client(*, db_connect_string: str) -> AgnosticClient:
    return AsyncIOMotorClient(db_connect_string)


@pytest.fixture(scope="session")
def sync_db_client(*, db_connect_string: str) -> pymongo.MongoClient[Any]:
    return pymongo.MongoClient(db_connect_string)


def _ping_database(db_client: pymongo.MongoClient[Any]) -> bool:
    try:
        db_client.admin.command("ping")
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def database(
    *,
    db_client: AgnosticClient,
    sync_db_client: pymongo.MongoClient[Any],
    docker_services: DockerServices,
) -> AgnosticDatabase:
    docker_services.wait_until_responsive(
        timeout=30,
        pause=0.5,
        check=lambda: _ping_database(sync_db_client),
    )

    return db_client["motorhead-test-db"]
