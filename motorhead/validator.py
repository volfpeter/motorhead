from collections.abc import Callable, Coroutine
from typing import Literal, TypeVar

from .bound_method_wrapper import BoundMethodWrapper
from .typing import ClauseOrMongoQuery

__all__ = (
    "ValidationError",
    "Validator",
    "validator",
)


class ValidationError(Exception): ...


TOwner = TypeVar("TOwner")
TInsertOrUpdate = TypeVar("TInsertOrUpdate")
InsertUpdateConfig = Literal["insert", "update", "insert-update"]


class Validator(
    BoundMethodWrapper[TOwner, [TInsertOrUpdate, ClauseOrMongoQuery | None], InsertUpdateConfig]
):
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
    [Callable[[TOwner, TInsertOrUpdate, ClauseOrMongoQuery | None], Coroutine[None, None, None]]],
    "Validator[TOwner, TInsertOrUpdate]",
]:
    """
    Service method decorator factory that converts the decorated method into a `Validator` instance.

    Example:

    ```python
    class SVC(Service):
        @validator("update")
        def check_something(self, data: InsertData | CreateData, query: ClauseOrMongoQuery | None) -> None:
            raise ValueError("Always fail.")
    ```

    Arguments:
        config: Validatator config.
    """

    def decorator(
        func: Callable[[TOwner, TInsertOrUpdate, ClauseOrMongoQuery | None], Coroutine[None, None, None]],
        /,
    ) -> "Validator[TOwner, TInsertOrUpdate]":
        return Validator(wrapped=func, config=config)

    return decorator
