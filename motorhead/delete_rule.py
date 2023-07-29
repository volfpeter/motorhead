from collections.abc import Callable, Coroutine, Sequence
from typing import Literal, TypeVar

from bson.objectid import ObjectId
from motor.core import AgnosticClientSession

from .bound_method_wrapper import BoundMethodWrapper

__all__ = (
    "DeleteError",
    "DeleteConfig",
    "DeleteRule",
    "delete_rule",
)


class DeleteError(Exception):
    ...


TOwner = TypeVar("TOwner")
DeleteConfig = Literal["deny", "pre", "post"]
"""
Delete rule configuration that specifies when a given delete rule must be executed.
"""


class DeleteRule(BoundMethodWrapper[TOwner, [AgnosticClientSession, Sequence[ObjectId]], DeleteConfig]):
    """
    Delete rule wrapper.

    Delete rules receive an `AgnosticClientSession` instance and a list of `ObjectId`s,
    and implement any deny, pre- or post-delete behavior.

    Delete rule execution sequence:

    - "deny" rules are executed first - delete rules whose role is to prevent
      a delete operation should have this config.
    - "pre" rules are executed next.
    - Then the requested delete operation takes place.
    - Finally the "post" delete rules are executed.

    Delete rules are always called in a transaction. Well-behaved delete rules must:

    - always use the received session instance to interact with the database,
      i.e. forward the received session to every database driver call;
    - *not* commit the session;
    - *not* start a new transaction (see `session.in_transaction`);
    - raise an exception if the operation can or must not complete.

    Example:

    ```python
    class SVC(Service):
        @delete_rule("pre")
        async def delete_cascade(self, session: AgnosticClientSession, ids: Sequence[ObjectId]) -> None:
            from x.y.z import OtherService

            other_service = OtherService(self._database)
            await other_service.delete_many({"foo_ref": {"$in": ids}}, options={"session": session})
    ```
    """

    __slots__ = ()

    exception = DeleteError


def delete_rule(
    config: DeleteConfig = "pre",
) -> Callable[
    [Callable[[TOwner, AgnosticClientSession, Sequence[ObjectId]], Coroutine[None, None, None]]],
    "DeleteRule[TOwner]",
]:
    """
    Decorator that converts a `Service` method into a `DeleteRule` that is then
    automatically applied by the service during delete operations.

    Arguments:
        config: Delete rule configuration.
    """

    def decorator(
        func: Callable[[TOwner, AgnosticClientSession, Sequence[ObjectId]], Coroutine[None, None, None]], /
    ) -> "DeleteRule[TOwner]":
        return DeleteRule(func=func, config=config)

    return decorator
