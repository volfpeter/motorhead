from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .query import Field
    from .typing import Clause


# -- Clause


def ensure_dict(data: dict[str, Any] | Clause) -> dict[str, Any]:
    return data.to_mongo() if hasattr(data, "to_mongo") else data


# -- Base operator classes


class ClauseOperator:
    """
    Base class for clause sequence based operators.
    """

    __slots__ = ("_clauses",)

    _operator: str = None  # type: ignore[assignment]

    def __init__(self, *clauses: Clause) -> None:
        self._clauses = clauses

    def __init_subclass__(cls) -> None:
        if cls._operator is None:
            cls._operator = f"${cls.__name__.lower()}"

    @property
    def clauses(self) -> Generator[Clause, None, None]:
        for clause in self._clauses:
            yield clause

    def to_mongo(self) -> dict[str, Any]:
        return {self._operator: [c.to_mongo() for c in self._clauses]}


class KeyValueOperator:
    """
    Base class for key-value pair based operators.
    """

    __slots__ = ("_key", "_value")

    _operator: str = None  # type: ignore[assignment]

    def __init__(self, key: str | Field, value: Any) -> None:
        self._key = key if isinstance(key, str) else key.name
        self._value = value

    def __init_subclass__(cls) -> None:
        if cls._operator is None:
            cls._operator = f"${cls.__name__.lower()}"

    @property
    def key(self) -> str:
        return self._key

    @property
    def value(self) -> Any:
        return self._value

    def to_mongo(self) -> dict[str, Any]:
        return {self._key: {self._operator: self._value}}


# -- Raw operator


class Raw:
    """
    Clause that wraps a raw, MongoDB-compatible dict.
    """

    __slots__ = ("_data",)

    def __init__(self, value: dict[str, Any]) -> None:
        self._data = value

    def to_mongo(self) -> dict[str, Any]:
        return {**self._data}  # Just a shallow copy


# -- Comparison operators


class Eq(KeyValueOperator):
    """`$eq` MongoDB operator."""

    __slots__ = ()


class DirectEq(KeyValueOperator):
    """Plain equality operator, `{key: value}`."""

    __slots__ = ()
    _operator = ""

    def to_mongo(self) -> dict[str, Any]:
        return {self._key: self._value}


class Ne(KeyValueOperator):
    """`$ne` MongoDB operator."""

    __slots__ = ()


class Gt(KeyValueOperator):
    """`$gt` MongoDB operator."""

    __slots__ = ()


class Gte(KeyValueOperator):
    """`$gte` MongoDB operator."""

    __slots__ = ()


class Lt(KeyValueOperator):
    """`$lt` MongoDB operator."""

    __slots__ = ()


class Lte(KeyValueOperator):
    """`$lte` MongoDB operator."""

    __slots__ = ()


class In(KeyValueOperator):
    """`$in` MongoDB operator."""

    __slots__ = ()


class NotIn(KeyValueOperator):
    """`$nin` MongoDB operator."""

    __slots__ = ()
    _operator = "$nin"


# -- Logical operators


class And(ClauseOperator):
    """`$and` MongoDB operator."""

    __slots__ = ()


class Not(ClauseOperator):
    """`$not` MongoDB operator."""

    __slots__ = ()


class Or(ClauseOperator):
    """`$or` MongoDB operator."""

    __slots__ = ()


class Nor(ClauseOperator):
    """`$nor` MongoDB operator."""

    __slots__ = ()


# -- Element operators


class Exists(KeyValueOperator):
    """`$exists` MongoDB operator."""

    __slots__ = ()

    def __init__(self, key: str | Field, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("Exists field only accepts bool values.")

        super().__init__(key, value)


class Type(KeyValueOperator):
    """`$type` MongoDB operator."""

    __slots__ = ()

    def __init__(self, key: str | Field, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("Type field only accepts string values.")

        super().__init__(key, value)


# -- Array operators


class All(KeyValueOperator):
    """`$all` MongoDB operator."""

    __slots__ = ()

    def __init__(self, key: str | Field, value: list[Any]) -> None:
        if not isinstance(value, list):
            raise ValueError("All field only accepts list values.")
        super().__init__(key, value)


class ElemMatch(KeyValueOperator):
    """`$elemMatch` MongoDB operator."""

    __slots__ = ()
    _operator = "$elemMatch"

    def __init__(self, key: str | Field, value: dict[str, Any]) -> None:
        if not isinstance(value, dict):
            raise ValueError("ElemMatch field only accepts dict values.")
        super().__init__(key, value)


class Size(KeyValueOperator):
    """`$size` MongoDB operator."""

    __slots__ = ()

    def __init__(self, key: str | Field, value: int) -> None:
        if not isinstance(value, int):
            raise ValueError("Size field only accepts int values.")
        super().__init__(key, value)
