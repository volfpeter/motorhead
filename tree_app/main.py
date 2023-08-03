from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


@lru_cache(maxsize=1)
def get_database() -> AsyncIOMotorDatabase:
    """Database provider dependency for the created API."""
    mongo_connection_string = "mongodb://127.0.0.1:27017"
    database_name = "tree-db"
    client = AsyncIOMotorClient(mongo_connection_string)
    return client[database_name]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Create all indexes on startup if they don't exist already.
    from .service import TreeNodeService

    db = get_database()

    await TreeNodeService(db).create_indexes()

    yield  # Application starts


def register_routes(app: FastAPI) -> None:
    """Registers all routes of the application."""
    from .api import make_api as make_tree_node_api

    api_prefix = "/api/v1"

    app.include_router(
        make_tree_node_api(get_database=get_database),
        prefix=api_prefix,
    )


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)  # Set lifespan method.

    register_routes(app)

    return app
