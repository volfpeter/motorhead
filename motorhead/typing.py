from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, Union

from motor.core import AgnosticClient as _AgnosticClient
from motor.core import AgnosticClientSession as AgnosticClientSession
from motor.core import AgnosticCollection as _AgnosticCollection
from motor.core import AgnosticCommandCursor as _AgnosticCommandCursor
from motor.core import AgnosticCursor as _AgnosticCursor
from motor.core import AgnosticDatabase as _AgnosticDatabase
from motor.core import AgnosticLatentCommandCursor as _AgnosticLatentCommandCursor
from pymongo.collation import Collation as PMCollation

if TYPE_CHECKING:
    from bson.codec_options import CodecOptions
    from pymongo.read_concern import ReadConcern
    from pymongo.read_preferences import Nearest, Primary, PrimaryPreferred, Secondary, SecondaryPreferred
    from pymongo.write_concern import WriteConcern

# -- Fix the generic type of some motor types that emulate generics with __class_getitem__()

AgnosticClient = _AgnosticClient[Any]
AgnosticCollection = _AgnosticCollection[Any]
AgnosticCommandCursor = _AgnosticCommandCursor[Any]
AgnosticCursor = _AgnosticCursor[Any]
AgnosticDatabase = _AgnosticDatabase[Any]
AgnosticLatentCommandCursor = _AgnosticLatentCommandCursor[Any]

# -- Typing

MongoProjection = dict[str, Any]
"""
MongoDB projection object.
"""


MongoQuery = dict[str, Any]
"""
MongoDB query object.
"""

UpdateObject = dict[str, Any] | Sequence[dict[str, Any]]
"""
MongoDB update object.
"""


class Clause(Protocol):
    """
    Protocol for clauses that service methods can convert to dictionaries
    that can be consumed by MongoDB.
    """

    def to_mongo(self) -> dict[str, Any]: ...


ClauseOrMongoQuery = Union[Clause, MongoQuery]
ClauseOrProjecttion = Union[Clause, MongoProjection]


class CollationDict(TypedDict, total=False):
    """
    Collation definition as a dict.
    """

    locale: str
    caseLevel: bool | None
    caseFirst: str | None
    strength: int | None
    numericOrdering: bool | None
    alternate: str | None
    maxVariable: str | None
    normalization: bool | None
    backwards: bool | None


Collation = PMCollation | CollationDict


class CollectionOptions(TypedDict, total=False):
    """
    Collection options.
    """

    codec_options: CodecOptions[Any] | None  # Default is None
    read_preference: (
        Primary | PrimaryPreferred | Secondary | SecondaryPreferred | Nearest | None
    )  # Default  None
    write_concern: WriteConcern | None  # Default is None
    read_concern: ReadConcern | None  # Default is None


class DeleteOptions(TypedDict, total=False):
    """
    Delete options.
    """

    collation: Mapping[str, Any] | Collation | None  # Default is None
    hint: str | Sequence[tuple[str, int | str | Mapping[str, Any]]] | None  # Default is None
    session: AgnosticClientSession | None  # Default is None
    let: Mapping[str, Any] | None  # Default is None
    comment: Any | None  # Default is None


class FindOptions(TypedDict, total=False):
    """
    Find options.
    """

    skip: int  # Default is 0
    limit: int  # Default is 0
    no_cursor_timeout: bool  # Default is False
    cursor_type: int  # Default is pymongo.cursor.CursorType.NON_TAILABLE
    sort: Sequence[tuple[str, int | str | Mapping[str, Any]]] | None  # Default is None
    allow_partial_results: bool  # Default is False
    oplog_replay: bool  # Default is False
    batch_size: int  # Default is 0
    collation: Mapping[str, Any] | Collation | None  # Default is None
    hint: str | Sequence[tuple[str, int | str | Mapping[str, Any]]] | None  # Default is None
    max_scan: int | None  # Default is None
    max_time_ms: int | None  # Default is None
    max: Sequence[tuple[str, int | str | Mapping[str, Any]]] | None  # Default is None
    min: Sequence[tuple[str, int | str | Mapping[str, Any]]] | None  # Default is None
    return_key: bool | None  # Default is None
    show_record_id: bool | None  # Default is None
    snapshot: bool | None  # Default is None
    comment: Any | None  # Default is None
    session: AgnosticClientSession | None  # Default is None
    allow_disk_use: bool | None  # Default is None
    let: bool | None  # Default is None


@dataclass(frozen=True, kw_only=True, slots=True)
class IndexData:
    """
    Index data description.
    """

    keys: str | Sequence[tuple[str, int | str | Mapping[str, Any]]]
    unique: bool = False
    background: bool = False
    collation: Collation | None = None
    sparse: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class InsertManyOptions(TypedDict, total=False):
    """
    Options for insert many operation.
    """

    bypass_document_validation: bool  # Default is False
    comment: Any | None  # Default is None
    ordered: bool  # Default is True
    session: AgnosticClientSession | None  # Default is None


class InsertOneOptions(TypedDict, total=False):
    """
    Insert options.
    """

    bypass_document_validation: bool  # Default is False
    session: AgnosticClientSession | None  # Default is None
    comment: Any | None  # Default is None


class UpdateOneOptions(TypedDict, total=False):
    """
    Update-one options.
    """

    upsert: bool  # Default is False
    bypass_document_validation: bool  # Default is False
    collation: Mapping[str, Any] | Collation | None  # Default is None
    array_filters: Sequence[Mapping[str, Any]]  # Default is None
    hint: str | Sequence[tuple[str, int | str | Mapping[str, Any]]] | None  # Default is None
    session: AgnosticClientSession | None  # Default is None
    let: Mapping[str, Any] | None  # Default is None
    comment: Any | None  # Default is None


class UpdateManyOptions(TypedDict, total=False):
    """
    Update-many options.
    """

    upsert: bool  # Default is False
    array_filters: Sequence[Mapping[str, Any]] | None  # Default is None
    bypass_document_validation: bool  # Default is None
    collation: Mapping[str, Any] | Collation | None  # Default is None
    hint: str | Sequence[tuple[str, int | str | Mapping[str, Any]]] | None  # Default is None
    session: AgnosticClientSession | None  # Default is None
    let: Mapping[str, Any] | None  # Default is None
    comment: Any | None  # Default is None


class ClientProvider(Protocol):
    """
    Client provider protocol for FastAPI database dependencies.
    """

    def __call__(self) -> AgnosticClient: ...


class DatabaseProvider(Protocol):
    """
    Database provider protocol for FastAPI database dependencies.
    """

    def __call__(self) -> AgnosticDatabase: ...
