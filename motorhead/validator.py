from collections.abc import Callable, Coroutine
from typing import Literal, TypeVar

from .bound_method_wrapper import BoundMethodWrapper
from .typing import MongoQuery

__all__ = (
    "ValidationError",
    "Validator",
    "validator",
)


class ValidationError(Exception):
    ...


TOwner = TypeVar("TOwner")
TInsertOrUpdate = TypeVar("TInsertOrUpdate")
InsertUpdateConfig = Literal["insert", "update", "insert-update"]


class Validator(BoundMethodWrapper[TOwner, [MongoQuery | None, TInsertOrUpdate], InsertUpdateConfig]):
    """
    Validator method wrapper.

    Validator methods receive an insert or update object, and execute some - potentially
    async - operations to make sure the inserted or updated data is valid.
    """

    __slots__ = ()

    exception = ValidationError


def validator(
    config: InsertUpdateConfig = "insert-update",
) -> Callable[
    [Callable[[TOwner, MongoQuery | None, TInsertOrUpdate], Coroutine[None, None, None]]],
    "Validator[TOwner, TInsertOrUpdate]",
]:
    """
    Service method decorator factory that converts the decorated method into a `Validator` instance.

    Example:

    ```python
    class SVC(Service):
        @validator("update")
        def check_something(self, data: InsertData | CreateData) -> None:
            raise ValueError("Always fail.")
    ```

    Arguments:
        config: Validatator config.
    """

    def decorator(
        func: Callable[[TOwner, MongoQuery | None, TInsertOrUpdate], Coroutine[None, None, None]], /
    ) -> "Validator[TOwner, TInsertOrUpdate]":
        return Validator(func=func, config=config)

    return decorator
