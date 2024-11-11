from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Coroutine, Generator, Iterable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypedDict, TypeVar, get_args

from bson import ObjectId
from pydantic import BaseModel
from pymongo.results import DeleteResult, InsertManyResult, InsertOneResult, UpdateResult

from .operator import ensure_dict
from .typing import ClauseOrMongoQuery

if TYPE_CHECKING:
    from .typing import (
        AgnosticClient,
        AgnosticClientSession,
        AgnosticCollection,
        AgnosticCommandCursor,
        AgnosticCursor,
        AgnosticDatabase,
        AgnosticLatentCommandCursor,
        Collation,
        CollectionOptions,
        DeleteOptions,
        FindOptions,
        IndexData,
        InsertManyOptions,
        InsertOneOptions,
        MongoProjection,
        UpdateManyOptions,
        UpdateObject,
        UpdateOneOptions,
    )

from .delete_rule import DeleteRule
from .validator import Validator

__all__ = (
    "BaseService",
    "DeleteResult",
    "InsertManyResult",
    "InsertOneResult",
    "Service",
    "UpdateResult",
)

TInsert = TypeVar("TInsert", bound=BaseModel)
TUpdate = TypeVar("TUpdate", bound=BaseModel)
TPrimaryKey = TypeVar("TPrimaryKey")


class ServiceException(Exception):
    """
    Base class for custom exceptions that can be raised by `Service`.
    """

    ...


class ServiceConfig(TypedDict, total=False):
    """Service configuration."""

    exclude_unset_on_insert: bool
    """Whether to exclude fields that have not been explicitly set on the data during insert operations."""


class _default_service_config:
    """Default service configuration."""

    exclude_unset_on_insert: ClassVar[bool] = False
    """See `ServiceConfig.exclude_unset_on_insert` for details."""


class BaseService(Generic[TInsert, TUpdate, TPrimaryKey]):
    """
    Base service with typed utility methods for MongoDB (`motor` asyncio).

    The service provides a limited subset of `motor`'s capabilities.

    For undocumented keyword arguments, please see the `motor` or `pymongo` documentation.

    For delete rule support, see `DeleteRule`, `delete_many()`, and `delete_one()`.

    For insert and update data validation, see `Validator`, `_validate_insert()`, and `_validate_update()`

    Class attributes:
        collection_name: The name of the collection the service operates on. Must be set by subclasses.
        collection_options: Optional `CollectionOptions` dict.
    """

    __slots__ = (
        "_collection",
        "_database",
        "_supports_transactions",
    )

    collection_name: ClassVar[str]
    """
    The name of the collection the service operates on. Must be set by subclasses.
    """

    collection_options: ClassVar[CollectionOptions | None] = None
    """
    Optional `CollectionOptions` dict.
    """

    indexes: ClassVar[dict[str, IndexData] | None] = None
    """
    The full description of the indexes (if any) of the collection.
    """

    service_config: ClassVar[ServiceConfig] = {}
    """Service configuration. Partial override of parent class configuration is not supported."""

    def __init__(self, database: AgnosticDatabase) -> None:
        """
        Initialization.

        Arguments:
            database: The database driver.
        """
        if self.collection_name is None:
            raise ValueError("Service.collection_name is not initialized.")

        self._database = database
        self._collection: AgnosticCollection | None = None
        self._supports_transactions: bool | None = None

    @property
    def client(self) -> AgnosticClient:
        """
        The database client.
        """
        return self._database.client

    @property
    def collection(self) -> AgnosticCollection:
        """
        The collection instance of the service.
        """
        if self._collection is None:
            self._collection = self._create_collection()

        return self._collection

    async def supports_transactions(self) -> bool:
        """
        Queries the database if it supports transactions or not.

        Note: transactions are only supported in replica set configuration.
        """
        if self._supports_transactions is None:
            self._supports_transactions = "system.replset" in (
                await self.client["local"].list_collection_names()
            )

        return self._supports_transactions

    def aggregate(
        self,
        pipeline: Sequence[dict[str, Any]],
        session: AgnosticClientSession | None = None,
        **kwargs: Any,
    ) -> AgnosticCommandCursor:
        """
        Performs an aggregation.

        For undocumented keyword arguments, see the documentation of
        `pymongo.collection.Collection.aggregate()`.

        Arguments:
            pipeline: The aggregation pipeline.
            session: An optional session to use.
        """
        return self.collection.aggregate(pipeline, session=session, **kwargs)

    async def count_documents(
        self, query: ClauseOrMongoQuery | None = None, *, options: FindOptions | None = None
    ) -> int:
        """
        Returns the number of documents that match the given query.

        Arguments:
            query: The query object.
            options: Query options, see the arguments of `collection.count_documents()` for details.

        Returns:
            The number of matching documents.
        """
        query = {} if query is None else ensure_dict(query)
        return await self.collection.count_documents(query, **(options or {}))

    async def create_index(
        self,
        keys: str | Sequence[tuple[str, int | str | Mapping[str, Any]]],
        *,
        name: str,
        unique: bool = False,
        session: AgnosticClientSession | None = None,
        background: bool = False,
        collation: Collation | None = None,
        sparse: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        Creates the specified index on collection of the service.

        Arguments:
            keys: Index description.
            name: Index name.
            unique: Whether to create a uniqueness constraint on the index.
            session: An optional session to use.
            background: Whether the index should be created in the background.
            collation: A `Collation` instance.
            sparse: Whether to omit documents from the index that doesn't have the indexed field.
        """
        return await self.collection.create_index(
            keys,
            name=name,
            unique=unique,
            session=session,
            background=background,
            collation=collation,
            sparse=sparse,
            **kwargs,
        )

    async def create_indexes(self, session: AgnosticClientSession | None = None) -> None:
        """
        Creates all declared indexes (see cls.indexes) on the collection of the service.

        Arguments:
            session: An optional session to use.
        """
        if self.indexes is None:
            return

        for name, idx in self.indexes.items():
            await self.create_index(
                idx.keys,
                name=name,
                unique=idx.unique,
                background=idx.background,
                collation=idx.collation,
                sparse=idx.sparse,
                session=session,
                **idx.extra,
            )

    async def drop_index(
        self,
        index_or_name: str | Sequence[tuple[str, int | str | Mapping[str, Any]]],
        session: AgnosticClientSession | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Drops the given index from the collection of the service.

        Arguments:
            index_or_name: The index to drop.
            session: An optional session to use.
        """
        return await self.collection.drop_index(
            index_or_name,
            session=session,
            **kwargs,
        )

    async def drop_indexes(self, session: AgnosticClientSession | None = None, **kwargs: Any) -> None:
        """
        Drops all indexes from the collection of the service.

        Arguments:
            session: An optional session to use.
        """
        return await self.collection.drop_indexes(session, **kwargs)

    def list_indexes(
        self,
        session: AgnosticClientSession | None = None,
        **kwargs: Any,
    ) -> AgnosticLatentCommandCursor:
        """
        Returns a cursor over the indexes of the collection of the service.

        Arguments:
            session: An optional session to use.
        """
        return self.collection.list_indexes(session, **kwargs)

    async def delete_by_id(
        self,
        id: TPrimaryKey,
        *,
        options: DeleteOptions | None = None,
    ) -> DeleteResult:
        """
        Deletes the document with the given ID.

        This method is just a convenience wrapper around `delete_one()`, see that
        method for more details.

        Arguments:
            id: The ID of the document to delete.
            options: Delete options, see the arguments of `collection.delete_one()`.

        Returns:
            The result of the operation.
        """
        return await self.delete_one({"_id": id}, options=options)

    async def delete_many(
        self,
        query: ClauseOrMongoQuery | None,
        *,
        options: DeleteOptions | None = None,
    ) -> DeleteResult:
        """
        The default `delete_many()` implementation of the service.

        The method enforces delete rules and executes the operation as follows:

        1. Enforce `"deny"` delete rules.
        2. Enforce `"pre"` delete rules.
        3. Execute the delete operation.
        4. Enforce `"post"` delete rules.

        See `DeleteRule` for more information.

        Arguments:
            query: Query object that matches the documents that should be deleted.
            options: Delete options, see the arguments of `collection.delete_many()`.

        Returns:
            The result of the operation.
        """
        query = {} if query is None else ensure_dict(query)
        session_manager = self._get_session_context_manager(
            options.get("session", None) if options else None
        )
        async with await session_manager() as session:
            opts: DeleteOptions = options or {}
            opts["session"] = session
            ctxman = (
                nullcontext
                if (
                    session.in_transaction  # type: ignore[truthy-function]
                    or not await self.supports_transactions()
                )
                else session.start_transaction
            )

            ids = await self.find_ids(query, session=session) if self._has_delete_rules() else None

            has_ids = ids is not None and len(ids) > 0

            async with ctxman():
                if has_ids:
                    await self._validate_deny_delete(
                        session,
                        ids,  # type: ignore[arg-type] # can not be None if has_ids is True
                    )
                    await self._validate_pre_delete(
                        session,
                        ids,  # type: ignore[arg-type] # can not be None if has_ids is True
                    )

                result = await self.collection.delete_many(query, **opts)

                if has_ids:
                    await self._validate_post_delete(
                        session,
                        ids,  # type: ignore[arg-type] # can not be None if has_ids is True
                    )

                return result

    async def delete_one(
        self,
        query: ClauseOrMongoQuery | None,
        *,
        options: DeleteOptions | None = None,
    ) -> DeleteResult:
        """
        The default `delete_one()` implementation of the service.

        The method enforces delete rules and executes the operation as follows:

        1. Enforce `"deny"` delete rules.
        2. Enforce `"pre"` delete rules.
        3. Execute the delete operation.
        4. Enforce `"post"` delete rules.

        See `DeleteRule` for more information.

        Arguments:
            query: Query object that matches the document that should be deleted.
            options: Delete options, see the arguments of `collection.delete_one()`.

        Returns:
            The result of the operation.
        """
        query = {} if query is None else ensure_dict(query)
        session_manager = self._get_session_context_manager(
            options.get("session", None) if options else None
        )
        async with await session_manager() as session:
            opts: DeleteOptions = options or {}
            opts["session"] = session
            ctxman = (
                nullcontext
                if (
                    session.in_transaction  # type: ignore[truthy-function]
                    or not await self.supports_transactions()
                )
                else session.start_transaction
            )

            ids = await self.find_ids(query, session=session) if self._has_delete_rules() else None

            async with ctxman():
                if ids is not None:
                    if len(ids) > 1:
                        # Only when the service has delete rules...
                        raise ValueError("Ambigous delete_one() - multiple documents match the query.")

                    await self._validate_deny_delete(session, ids)
                    await self._validate_pre_delete(session, ids)

                result = await self.collection.delete_one(query, **opts)

                if ids is not None:
                    await self._validate_post_delete(session, ids)

                return result

    async def exists(self, id: TPrimaryKey, *, options: FindOptions | None = None) -> bool:
        """
        Returns whether the document with the given ID exists.

        Arguments:
            id: The ID of the document to check.
            options: Query options, see the arguments of `collection.count_documents()` for details.

        Returns:
            Whether the document with the given ID exists.
        """
        return await self.count_documents({"_id": id}, options=options) == 1

    def find(
        self,
        query: ClauseOrMongoQuery | None = None,
        projection: MongoProjection | None = None,
        *,
        options: FindOptions | None = None,
    ) -> AgnosticCursor:
        """
        The default `find()` implementation of the service.

        Arguments:
            query: The query object.
            projection: Optional projection.
            options: Query options, see the arguments of `collection.find()` for details.

        Returns:
            An async database cursor.
        """
        query = {} if query is None else ensure_dict(query)
        return self.collection.find(query, projection, **(options or {}))

    async def find_ids(
        self,
        query: ClauseOrMongoQuery | None,
        *,
        session: AgnosticClientSession | None = None,
    ) -> list[TPrimaryKey]:
        """
        Returns the IDs of all documents that match the given query.

        Arguments:
            query: The query object.
            session: An optional database session to use.

        Returns:
            The IDs of all matching documents.
        """
        query = {} if query is None else ensure_dict(query)
        return [
            doc["_id"]
            for doc in await self.collection.find(query, {"_id": True}, session=session).to_list(None)
        ]

    async def find_one(
        self,
        query: ClauseOrMongoQuery | None = None,
        projection: MongoProjection | None = None,
        *,
        options: FindOptions | None = None,
    ) -> dict[str, Any] | None:
        """
        The default `find_one()` implementation of the service.

        Arguments:
            query: The query object.
            projection: Optional projection.
            options: Query options, see the arguments of `collection.find()` for details.

        Returns:
            A single matching document or `None` if there are no matches.
        """
        query = {} if query is None else ensure_dict(query)
        return await self.collection.find_one(query, projection, **(options or {}))

    async def get_by_id(
        self,
        id: TPrimaryKey,
        projection: MongoProjection | None = None,
        *,
        options: FindOptions | None = None,
    ) -> dict[str, Any] | None:
        """
        Returns the document with the given ID if it exists.

        Arguments:
            id: The ID of the queried document.
            projection: Optional projection.
            options: Query options, see the arguments of `collection.find()` for details.

        Returns:
            The queried document if such a document exists.
        """
        return await self.find_one({"_id": id}, projection, options=options)

    async def create(self, data: TInsert, *, options: InsertOneOptions | None = None) -> dict[str, Any]:
        """
        Inserts the given data into the collection and immediately queries
        and returns the created document.

        Arguments:
            data: The data to be inserted.
            options: Insert options, see the arguments of `collection.insert_one()` for details.

        Returns:
            The result of the operation.

        Raises:
            ServiceException: If the service failed to access the newly created document.
            Exception: If the data is invalid.
        """
        insert_result = await self.insert_one(data, options=options)
        result = await self.get_by_id(insert_result.inserted_id)
        if result is None:
            raise ServiceException("Failed to query the inserted document by its ID.")

        return result

    async def insert_many(
        self, data: Iterable[TInsert], *, options: InsertManyOptions | None = None
    ) -> InsertManyResult:
        """
        Inserts all the given objects into the collection.

        Arguments:
            data: The documents to be inserted.
            options: Insert options, see the arguments of `collection.insert_many()` for details.

        Returns
            The result of the operation.

        Raises:
            Exception: If any of the documents is invalid.
        """
        insert_data = [await self._prepare_for_insert(d) for d in data]
        return await self.collection.insert_many(
            insert_data,
            **(options or {}),
        )

    async def insert_one(
        self, data: TInsert, *, options: InsertOneOptions | None = None
    ) -> InsertOneResult:
        """
        Inserts the given data into the collection.

        Arguments:
            data: The data to be inserted.
            options: Insert options, see the arguments of `collection.insert_one()` for details.

        Returns:
            The result of the operation.

        Raises:
            Exception: If the data is invalid.
        """
        return await self.collection.insert_one(
            await self._prepare_for_insert(data),
            **(options or {}),
        )

    async def update(
        self,
        id: TPrimaryKey,
        changes: TUpdate,
        *,
        options: UpdateOneOptions | None = None,
    ) -> dict[str, Any]:
        """
        Updates the document with the given ID and immediately queries and returns
        the updated document.

        Arguments:
            id: The ID of the document to update.
            changes: The changes to make.
            options: Update options, see the arguments of `collection.update_one()` for details.

        Returns:
            The updated document.

        Raises:
            ServiceException: If the service failed to query the updated document.
            Exception: If the data is invalid.
        """
        await self.update_by_id(id, changes, options=options)
        result = await self.get_by_id(id)
        if result is None:
            raise ServiceException("Failed to query the updated document by its ID.")

        return result

    async def update_by_id(
        self,
        id: TPrimaryKey,
        changes: TUpdate,
        *,
        options: UpdateOneOptions | None = None,
    ) -> UpdateResult:
        """
        Updates the document with the given ID.

        Arguments:
            id: The ID of the document to update.
            changes: The changes to make.
            options: Update options, see the arguments of `collection.update_one()` for details.

        Returns:
            The result of the operation.

        Raises:
            Exception: If the data is invalid.
        """
        return await self.update_one({"_id": id}, changes, options=options)

    async def update_many(
        self,
        query: ClauseOrMongoQuery | None,
        changes: TUpdate,
        *,
        options: UpdateManyOptions | None = None,
    ) -> UpdateResult:
        """
        The default `delete_many()` implementation of the service.

        Arguments:
            query: Query that matches the documents that should be updated.
            changes: The changes to make.
            options: Update options, see the arguments of `collection.update_many()` for details.

        Returns:
            The result of the operation.

        Raises:
            Exception: If the data is invalid.
        """
        query = {} if query is None else ensure_dict(query)
        return await self.collection.update_many(
            query,
            await self._prepare_for_update(changes, query),
            **(options or {}),
        )

    async def update_one(
        self,
        query: ClauseOrMongoQuery | None,
        changes: TUpdate,
        *,
        options: UpdateOneOptions | None = None,
    ) -> UpdateResult:
        """
        The default `delete_one()` implementation of the service.

        Arguments:
            query: Query that matches the document that should be updated.
            changes: The changes to make.
            options: Update options, see the arguments of `collection.update_one()` for details.

        Returns:
            The result of the operation.

        Raises:
            Exception: If the data is invalid.
        """
        query = {} if query is None else ensure_dict(query)
        return await self.collection.update_one(
            query,
            await self._prepare_for_update(changes, query),
            **(options or {}),
        )

    @classmethod
    def get_objectid_fields(cls, model: type[BaseModel]) -> set[str]:
        """
        Returns the names of all `ObjectId` fields.

        Arguments:
            model: The model to collect `ObjectId` field
        """
        result: set[str] = set()
        for name, info in model.model_fields.items():
            if info.annotation is None:
                continue

            if args := get_args(info.annotation):
                try:
                    if any(issubclass(a, ObjectId) for a in args):
                        result.add(name)
                except TypeError:
                    continue
            elif issubclass(info.annotation, ObjectId):
                result.add(name)

        return result

    async def _convert_for_insert(self, data: TInsert) -> dict[str, Any]:
        """
        Converts the given piece of the into its database representation.

        The default implementation is `self._mongo_dump(data)`.

        Arguments:
            data: The data to be inserted.

        Returns:
            The MongoDB-compatible, insertable data.

        Raises:
            Exception: If the data is invalid.
        """
        return self._mongo_dump(
            data,
            exclude_unset=self.service_config.get(
                "exclude_unset_on_insert", _default_service_config.exclude_unset_on_insert
            ),
        )

    async def _convert_for_update(self, data: TUpdate) -> UpdateObject:
        """
        Converts the given piece of data into an update object.

        The default implementation is `{"$set": self._mongo_dump(data)}`.

        Arguments:
            data: The update data.

        Returns:
            The MongoDB-compatible update object.

        Raises:
            Exception: If the data is invalid.
        """
        return {"$set": self._mongo_dump(data, exclude_unset=True)}

    def _create_collection(self) -> AgnosticCollection:
        """
        Creates a new `AgnosticCollection` instance for the service.
        """
        return self._database.get_collection(self.collection_name, **(self.collection_options or {}))

    def _delete_rules(
        self,
    ) -> Generator[DeleteRule["BaseService[TInsert, TUpdate, TPrimaryKey]", TPrimaryKey], None, None]:
        """
        Generator that yields the delete rules that are registered on this service
        in the order they are present in `__class__.__dict__`.
        """
        for rule in self.__class__.__dict__.values():
            if isinstance(rule, DeleteRule):
                yield rule

    def _has_delete_rules(self) -> bool:
        """
        Returns whether the service has any delete rules.
        """
        for rule in self.__class__.__dict__.values():
            if isinstance(rule, DeleteRule):
                return True

        return False

    def _get_session_context_manager(
        self,
        session: AgnosticClientSession | None,
    ) -> Callable[[], Coroutine[None, None, AbstractAsyncContextManager[AgnosticClientSession]]]:
        """
        Returns a session context manager
        """
        if session is None:
            # Return a context manager that actually starts a session.
            return self.client.start_session

        async def start_session() -> AbstractAsyncContextManager[AgnosticClientSession]:
            @asynccontextmanager
            async def ctx_manager() -> AsyncGenerator[AgnosticClientSession, None]:
                yield session

            return ctx_manager()

        return start_session

    def _mongo_dump(self, data: BaseModel, *, exclude_unset: bool) -> dict[str, Any]:
        """
        Dumps the given model instance for consumption by MongoDB.

        Arguments:
            data: The model instance to dump.
            exclude_unset: Whether to exclude fields that have not been explicitly set on the data.

        Returns:
            The MongoDB-compatible, dumped dictionary.
        """
        objectid_fields = self.get_objectid_fields(type(data))
        return {
            **{
                k: None if v is None else ObjectId(v)
                for k, v in data.model_dump(
                    include=objectid_fields,
                    by_alias=True,
                    exclude_unset=exclude_unset,
                ).items()
            },
            **data.model_dump(
                exclude=objectid_fields,
                by_alias=True,
                exclude_unset=exclude_unset,
            ),
        }

    async def _prepare_for_insert(
        self, data: TInsert, query: ClauseOrMongoQuery | None = None
    ) -> dict[str, Any]:
        """
        Validates the given piece of data and converts it into its database representation
        if validation was successful.

        Arguments:
            data: The data to be inserted.
            query: Query that matches the documents that will be updated.

        Returns:
            The MongoDB-compatible, insertable data.

        Raises:
            Exception: If the data is invalid.
        """
        await self._validate_insert(data, query)
        return await self._convert_for_insert(data)

    async def _prepare_for_update(self, data: TUpdate, query: ClauseOrMongoQuery | None) -> UpdateObject:
        """
        Validates the given piece of data and converts it into an update object.

        Arguments:
            data: The update data.
            query: Query that matches the documents that will be updated.

        Returns:
            The MongoDB-compatible update object.

        Raises:
            Exception: If the data is invalid.
        """
        await self._validate_update(data, query)
        return await self._convert_for_update(data)

    async def _validate_insert(self, data: TInsert, query: ClauseOrMongoQuery | None = None) -> None:
        """
        Validates the given piece of data for insertion by executing all insert validators.

        See `Validator` for more information.

        Arguments:
            query: Query that matches the documents that will be updated.
            data: The data to validate.

        Raises:
            ValidationError: If validation failed.
        """
        # Sequential validation, slow but safe.
        for validator in self._validators():
            if "insert" in validator.config:
                await validator(self, data, query)

    async def _validate_deny_delete(
        self, session: AgnosticClientSession, ids: Sequence[TPrimaryKey]
    ) -> None:
        """
        Executes all "deny" delete rules.

        See `DeleteRule` for more information.

        Arguments:
            session: The current database session.
            ids: The IDs that will be removed.

        Raises:
            DeleteError: if one of the executed delete rules prevent the operation.
        """
        for rule in self._delete_rules():
            if isinstance(rule, DeleteRule) and rule.config == "deny":
                await rule(self, session, ids)

    async def _validate_pre_delete(
        self, session: AgnosticClientSession, ids: Sequence[TPrimaryKey]
    ) -> None:
        """
        Executes all "pre" delete rules.

        See `DeleteRule` for more information.

        Arguments:
            session: The current database session.
            ids: The IDs that will be removed.

        Raises:
            DeleteError: if one of the executed delete rules fail.
        """
        for rule in self._delete_rules():
            if isinstance(rule, DeleteRule) and rule.config == "pre":
                await rule(self, session, ids)

    async def _validate_post_delete(
        self, session: AgnosticClientSession, ids: Sequence[TPrimaryKey]
    ) -> None:
        """
        Executes all "post" delete rules.

        See `DeleteRule` for more information.

        Arguments:
            session: The current database session.
            ids: The IDs that will be removed.

        Raises:
            DeleteError: if one of the executed delete rules fail.
        """
        for rule in self._delete_rules():
            if isinstance(rule, DeleteRule) and rule.config == "post":
                await rule(self, session, ids)

    async def _validate_update(self, data: TUpdate, query: ClauseOrMongoQuery | None = None) -> None:
        """
        Validates the given piece of data for update by executing all update validators.

        See `Validator` for more information.

        Arguments:
            data: The data to validate.
            query: Query that matches the documents that will be updated.

        Raises:
            ValidationError: If validation failed.
        """
        # Sequential validation, slow but safe.
        for validator in self._validators():
            if "update" in validator.config:
                await validator(self, data, query)

    def _validators(
        self,
    ) -> Generator[Validator["BaseService[TInsert, TUpdate, TPrimaryKey]", TInsert | TUpdate], None, None]:
        """
        Generator that yields the validators that are registered on this service
        in the order they are present in `__class__.__dict__`.
        """
        for validator in self.__class__.__dict__.values():
            if isinstance(validator, Validator):
                yield validator


class Service(BaseService[TInsert, TUpdate, ObjectId]):
    """Base service for documents with an `ObjectId` `_id`."""
