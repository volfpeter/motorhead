from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from .operator import (
    All,
    And,
    DirectEq,
    ElemMatch,
    Eq,
    Exists,
    Gt,
    Gte,
    In,
    Lt,
    Lte,
    Ne,
    NotIn,
    Or,
    Size,
    Type,
)
from .typing import Clause

_T = TypeVar("_T", bound=BaseModel)

if TYPE_CHECKING:
    from .typing import MongoQuery


class Field:
    """
    Queryable field with support for MongoDB operators in the form of
    overridden built-in operators or MongoDB-specific methods.
    """

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        """
        The name of the field as well as the name of the corresponding property
        in the MongoDB model.
        """
        return self._name

    # -- Operators

    def __lt__(self, value: Any) -> Query:
        return Query(Lt(self._name, value))

    def __le__(self, value: Any) -> Query:
        return Query(Lte(self._name, value))

    def __eq__(self, value: Any) -> Query:  # type: ignore[override]
        if isinstance(value, (list, set, tuple, dict)):
            return Query(Eq(self._name, value))

        return Query(DirectEq(self._name, value))

    def __ne__(self, value: Any) -> Query:  # type: ignore[override]
        return Query(Ne(self._name, value))

    def __gt__(self, value: Any) -> Query:
        return Query(Gt(self._name, value))

    def __ge__(self, value: Any) -> Query:
        return Query(Gte(self._name, value))

    # -- Methods

    def All(self, value: list[Any]) -> Query:
        """
        `$all` operator.

        Arguments:
            value: The operator's argument.
        """
        return Query(All(self._name, value))

    def ElemMatch(self, value: dict[str, Any]) -> Query:
        """
        `$elemMatch` operator.

        Arguments:
            value: The operator's argument.
        """
        return Query(ElemMatch(self._name, value))

    def Exists(self, value: bool) -> Query:
        """
        `$exists` operator.

        Arguments:
            value: The operator's argument.
        """
        return Query(Exists(self._name, value))

    def In(self, value: Any) -> Query:
        """
        `$in` operator.

        Arguments:
            value: The operator's argument.
        """
        return Query(In(self._name, value))

    def NotIn(self, value: Any) -> Query:
        """
        `$nin` operator.

        Arguments:
            value: The operator's argument.
        """
        return Query(NotIn(self._name, value))

    def Size(self, value: int) -> Query:
        """
        `$size` operator.

        Arguments:
            value: The operator's argument.
        """
        return Query(Size(self._name, value))

    def Type(self, value: str) -> Query:
        """
        `$type` operator.

        Arguments:
            value: The operator's argument.
        """
        return Query(Type(self._name, value))


class Query:
    """
    Query implementation.
    """

    __slots__ = ("_clause",)

    def __init__(self, clause: Clause | None = None) -> None:
        """
        Initialization.

        Arguments:
            clause: The default clause of the query.
        """
        self._clause = clause

    def __and__(self, value: Clause) -> Query:
        result = self.clone()
        clause = value._clause if isinstance(value, Query) else value
        if clause is None:
            result._clause = self._clause
        elif isinstance(self._clause, And):
            result._clause = And(*self._clause.clauses, clause)
        else:
            result._clause = clause if self._clause is None else And(self._clause, clause)

        return result

    def __or__(self, value: Clause) -> Query:
        result = self.clone()
        clause = value._clause if isinstance(value, Query) else value
        if clause is None:
            result._clause = self._clause
        elif isinstance(self._clause, Or):
            result._clause = Or(*self._clause.clauses, clause)
        else:
            result._clause = clause if self._clause is None else Or(self._clause, clause)

        return result

    def clone(self) -> Query:
        """
        Returns a clone of the query.
        """
        result = type(self)()
        self._clone_attributes(result)
        return result

    def _clone_attributes(self, item: Query) -> None:
        """
        Clones the attributes of the query.

        Arguments:
            item: The query on which clonable properties must be set.
        """
        item._clause = self._clause

    def to_mongo(self) -> MongoQuery:
        """
        Returns the `MongoQuery` representation of the query.
        """
        return {} if self._clause is None else self._clause.to_mongo()


class Queryable:
    """
    Base class for queryable models.

    It expects a Pydantic `BaseModel` class during subclassing in its `model` argument and
    adds a queryable `Field` descriptor to the subclass for each field of the Pydantic model.

    Example:

    ```python
    from pydantic import BaseModel

    class Person(BaseModel):
        name: str
        lucky_number: int

    class QPerson(Queryable, model=Person):
        __slots__ = ()
    ```

    It's recommended to use the `Q` helper to achieve the above result, so you can have
    at least ORM-level type hints and autocompletion for the created queryable class.

    ```python
    from pydantic import BaseModel

    class Person(BaseModel):
        name: str
        lucky_number: int

    QPerson = Q(Person)
    ```
    """

    __slots__ = ()

    def __init_subclass__(cls, *, model: type[BaseModel]) -> None:
        """
        Subclass initialization.

        Arguments:
            model: The Pydantic model the `Queryable` is created for.
        """
        super().__init_subclass__()
        for name, info in model.model_fields.items():
            field_name = name
            if name == "id" and info.alias == "_id":
                field_name = "_id"

            setattr(cls, name, Field(field_name))


# TODO: fix type hint when the Intersection and Not types are available.
def Q(model: type[_T]) -> type[_T]:
    """
    Creates a new `Queryable` class that can be used to construct queries for documents
    with the given Pydantic model.

    The created `Queryable` class will have a property (`Field`) for all properties
    that were declared in the given Pydantic class. For usage examples and more details,
    plase see `Queryable`.

    Arguments:
        model: The Pydantic model the `Queryable` class should be created for.
    """

    class Result(Queryable, model=model):
        __slots__ = ()

    return Result  # type: ignore[return-value]
