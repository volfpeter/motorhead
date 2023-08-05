# FastAPI example

In this is example we will:

- create a simple `TreeNode` document model with a name, a creation date, and an optional reference to a parent node;
- prepare all the services that are necessary to create, read, update, or delete documents;
- declare a couple of delete rules and validators that enforce consistency;
- declare a unique name index for the `TreeNode` collection;
- implement a `fastapi` `APIRouter` factory that can be included in `fastapi` applications;
- set up the `fastapi` application itself;
- implement automatic index creation in the application's lifespan method.

## Prerequisites

To follow and try this example, you will need:

- Python 3.10+;
- access to a MongoDB database (e.g. a Community Edition running locally);
- `fastapi` (version `>=0.100.1`) with all its dependencies (`pip install fastapi[all]`);
- and of course this library.

## Project layout

Create the _root directory_ of your project, for example `tree-app`.

Inside the _root directory_, create the root Python _package_ for the application -- `tree_app` -- and add the following empty files to:

- `__init__.py`
- `api.py`
- `main.py`
- `model.py`
- `service.py`

In the end, your directory structure should look like this:

<ul>
    <li><code>tree-app</code> (root directory)</li>
    <ul>
        <li><code>tree_app</code> (root package)</li>
        <ul>
            <li><code>__init__.py</code></li>
            <li><code>api.py</code></li>
            <li><code>main.py</code></li>
            <li><code>model.py</code></li>
            <li><code>service.py</code></li>
        </ul>
    </ul>
</ul>

## Model

First we will implement the data model in `model.py`. Actually, we will implement three (`pydantic`) model classes, one for document serialization, one for creation, and one for editing.

Additionally we will create a `Queryable` class using the `Q` factory that we will be able to use later to construct queries in an ODM-like manner.

```python
from motorhead import BaseDocument, Document, ObjectId, Q, UTCDatetime
from pydantic import ConfigDict


class TreeNode(Document):
    """
    Tree node document model.
    """

    name: str
    parent: ObjectId | None = None
    created_at: UTCDatetime


QTreeNode = Q(TreeNode)
"""Queryable class for the `TreeNode` collection."""


class TreeNodeCreate(BaseDocument):
    """
    Tree node creation model.
    """

    name: str
    parent: ObjectId | None = None


class TreeNodeUpdate(BaseDocument):
    """
    Tree node update model.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str | None = None
    parent: ObjectId | None = None
```

## Services

With the model in place, we can start working on the services (`service.py`) that we will use from the REST routes. This step is as simple as subclassing `Service` and specifying the collection name:

```python
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, cast

from bson import ObjectId
from motor.core import AgnosticClientSession
from motorhead import (
    ClauseOrMongoQuery,
    CollectionOptions,
    Field,
    IndexData,
    Service,
    delete_rule,
    validator,
)

from .model import QTreeNode, TreeNodeCreate, TreeNodeUpdate


class TreeNodeService(Service[TreeNodeCreate, TreeNodeUpdate]):
    """
    Tree node database services.
    """

    __slots__ = ()

    collection_name: str = "tree_nodes"

    collection_options: CollectionOptions | None = None

    async def _convert_for_insert(self, data: TreeNodeCreate) -> dict[str, Any]:
        return {
            **(await super()._convert_for_insert(data)),
            "created_at": datetime.now(timezone.utc),
        }
```

Noticate that `TreeNodeCreate` does not have a `created_at` attribute. Instead we inject this attribute during creation by overriding the `_convert_for_insert()` method of the service.

That could be it, but we want to enforce a level of consistency in the database. To do that, we will add a couple of delete rules and validators to the service.

Note that the rules below do _not_ fully enforce a tree structure, but they are good enough for demonstration purposes.

```python
...

class TreeNodeService(Service[TreeNodeCreate, TreeNodeUpdate]):

    ...

    @delete_rule("pre")  # Delete rule that removes the subtrees of deleted nodes.
    async def dr_delete_subtree(self, session: AgnosticClientSession, ids: Sequence[ObjectId]) -> None:
        child_ids = await self.find_ids(cast(Field, QTreeNode.parent).In(ids).to_mongo(), session=session)
        if len(child_ids) > 0:
            # Recursion
            await self.delete_many(cast(Field, QTreeNode.id).In(child_ids), options={"session": session})

    @delete_rule("deny")  # Delete rule that prevents the removal of root nodes.
    async def dr_deny_if_root(self, session: AgnosticClientSession, ids: Sequence[ObjectId]) -> None:
        root_cnt = await self.count_documents(
            cast(Field, QTreeNode.id).In(ids) & (QTreeNode.parent == None),  # type: ignore[operator] # noqa [711]
            options={"session": session},
        )
        if root_cnt > 0:
            raise ValueError("Can not delete root nodes.")

    @validator("insert-update")
    async def v_parent_valid(
        self, query: ClauseOrMongoQuery | None, data: TreeNodeCreate | TreeNodeUpdate
    ) -> None:
        if data.parent is None:  # No parent node is always fine
            return

        if not await self.exists(data.parent):  # Parent must exist.
            raise ValueError("Parent does not exist.")

        if isinstance(data, TreeNodeCreate):  # No more checks during creation.
            return

        matched_ids = (await self.find_ids(query)) if isinstance(data, TreeNodeUpdate) else []
        if data.parent in matched_ids:  # Self reference is forbidden.
            raise ValueError("Self-reference.")

    ...
```

There are a couple of important things to notice in the code above:

- Validator methods can get either a MongoDB query `dict` or a `Clause` (any object with a `to_mongo()` method), that can be passed in to service methods for consumption.
- Instead of writing MongoDB query dicts, in delete rules we used the previously created `QTreeNode` queryable class to build queries in and ODM-like manner, e.g. `QTreeNode.id.In(ids) & (QTreeNode.parent == None)`.

Finally, we will declare the indexes of the collection by setting `TreeNodeService.indexes`, which must be an index name - `IndexData` dictionary. A unique, ascending, case-insensitive index on the `name` attribute can be declared like this:

```python
...

class TreeNodeService(Service[TreeNodeCreate, TreeNodeUpdate]):
    ...

    indexes = {
        "unique-name": IndexData(
            keys="name",
            unique=True,
            collation={"locale": "en", "strength": 1},
        ),
    }

    ...
```

For all indexing options, please see the [PyMongo documentation](https://pymongo.readthedocs.io/en/stable/index.html).

Combining everything together, the final service implementation looks like this:

```python
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, cast

from bson import ObjectId
from motor.core import AgnosticClientSession
from motorhead import (
    ClauseOrMongoQuery,
    CollectionOptions,
    Field,
    IndexData,
    Service,
    delete_rule,
    validator,
)

from .model import QTreeNode, TreeNodeCreate, TreeNodeUpdate


class TreeNodeService(Service[TreeNodeCreate, TreeNodeUpdate]):
    """
    Tree node database services.
    """

    __slots__ = ()

    collection_name: str = "tree_nodes"

    collection_options: CollectionOptions | None = None

    indexes = {
        "unique-name": IndexData(
            keys="name",
            unique=True,
            collation={"locale": "en", "strength": 1},
        ),
    }

    @delete_rule("pre")  # Delete rule that removes the subtrees of deleted nodes.
    async def dr_delete_subtree(self, session: AgnosticClientSession, ids: Sequence[ObjectId]) -> None:
        child_ids = await self.find_ids(cast(Field, QTreeNode.parent).In(ids).to_mongo(), session=session)
        if len(child_ids) > 0:
            # Recursion
            await self.delete_many(cast(Field, QTreeNode.id).In(child_ids), options={"session": session})

    @delete_rule("deny")  # Delete rule that prevents the removal of root nodes.
    async def dr_deny_if_root(self, session: AgnosticClientSession, ids: Sequence[ObjectId]) -> None:
        root_cnt = await self.count_documents(
            cast(Field, QTreeNode.id).In(ids) & (QTreeNode.parent == None),  # type: ignore[operator] # noqa [711]
            options={"session": session},
        )
        if root_cnt > 0:
            raise ValueError("Can not delete root nodes.")

    @validator("insert-update")
    async def v_parent_valid(
        self, query: ClauseOrMongoQuery | None, data: TreeNodeCreate | TreeNodeUpdate
    ) -> None:
        if data.parent is None:  # No parent node is always fine
            return

        if not await self.exists(data.parent):  # Parent must exist.
            raise ValueError("Parent does not exist.")

        if isinstance(data, TreeNodeCreate):  # No more checks during creation.
            return

        matched_ids = (await self.find_ids(query)) if isinstance(data, TreeNodeUpdate) else []
        if data.parent in matched_ids:  # Self reference is forbidden.
            raise ValueError("Self-reference.")

    async def _convert_for_insert(self, data: TreeNodeCreate) -> dict[str, Any]:
        return {
            **(await super()._convert_for_insert(data)),
            "created_at": datetime.now(timezone.utc),
        }
```

With the service implementation ready, we can move on to creating the REST API.

## Routing

In `api.py`, we will use the factory pattern to create an `APIRouter` instance for the `fastapi` application.

Notice how we get access to the `TreeNodeService` instance in routes with annotated FastAPI dependencies, and how the database interactions are simple one-liners in all routes.

```python
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from motorhead import AgnosticDatabase, DatabaseProvider, DeleteError, DeleteResultModel, ObjectId

from .model import TreeNode, TreeNodeCreate, TreeNodeUpdate
from .service import TreeNodeService


def make_api(
    *,
    get_database: DatabaseProvider,
    prefix: str = "/tree-node",
) -> APIRouter:
    """
    Tree node `APIRouter` factory.

    Arguments:
        get_database: FastAPI dependency that returns the `AgnosticDatabase`
                      database instance for the API.
        prefix: The prefix for the created `APIRouter`.

    Returns:
        The created `APIRouter` instance.
    """
    DependsDatabase = Annotated[AgnosticDatabase, Depends(get_database)]

    def get_service(database: DependsDatabase) -> TreeNodeService:
        return TreeNodeService(database)

    DependsService = Annotated[TreeNodeService, Depends(get_service)]

    api = APIRouter(prefix=prefix)

    @api.get("/", response_model=list[TreeNode])
    async def get_all(service: DependsService) -> list[dict[str, Any]]:
        return [d async for d in service.find()]

    @api.post("/", response_model=TreeNode)
    async def create(data: TreeNodeCreate, service: DependsService) -> dict[str, Any]:
        try:
            return await service.create(data)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Creation failed.") from e

    @api.get("/{id}", response_model=TreeNode)
    async def get_by_id(id: ObjectId, service: DependsService) -> dict[str, Any]:
        if (result := await service.get_by_id(id)) is not None:
            return result

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(id))

    @api.put("/{id}", response_model=TreeNode)
    async def update_by_id(id: ObjectId, data: TreeNodeUpdate, service: DependsService) -> dict[str, Any]:
        try:
            return await service.update(id, data)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(id)) from e

    @api.delete("/{id}", response_model=DeleteResultModel)
    async def delete_by_id(id: ObjectId, service: DependsService) -> DeleteResultModel:
        try:
            result = await service.delete_by_id(id)
        except DeleteError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(id)) from e
        if result.deleted_count == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(id))

        return DeleteResultModel(delete_count=result.deleted_count)

    return api
```

## The application

Finally, we can create the application itself and include our routes in it:

```python
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI
from motor.core import AgnosticClient, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient


@lru_cache(maxsize=1)
def get_database() -> AgnosticDatabase:
    """Database provider dependency for the created API."""
    mongo_connection_string = "mongodb://127.0.0.1:27017"
    database_name = "tree-db"
    client: AgnosticClient = AsyncIOMotorClient(mongo_connection_string)
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
```

Notice the async `lifespan()` method (context manager) that creates the declared indexes before the application starts serving requests by calling the `create_indexes()` method of each service. There are of course many other ways for adding index creation (or recreation) to an application, like database migration or command line tools. Doing it in the `lifespan` method of the application is just one, easy to implement solution that works well for relatively small databases and for this demo application.

## Run

With everything ready, we can start the application by executing `uvicorn tree_app.main:create_app --reload --factory` in the root directory and go to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to try the created REST API.
