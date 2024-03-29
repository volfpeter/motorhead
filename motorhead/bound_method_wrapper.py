from collections.abc import Callable, Coroutine
from typing import Concatenate, Generic, ParamSpec, TypeVar

__all__ = ("BoundMethodWrapper",)

TOwner = TypeVar("TOwner")
TParams = ParamSpec("TParams")
TConfig = TypeVar("TConfig")


class BoundMethodWrapper(Generic[TOwner, TParams, TConfig]):
    """
    Async method wrapper that also acts as a bound instance method when it replaces
    an instance method of a class.

    Note: the wrapped method will be unbound.

    Caveats:
        This class acts as if it was a bound method of the instance using the
        descriptor protocol, but of course it is not a bound method, which becomes
        important when trying to apply decorators on the wrapper instance. In those
        cases the wrapper acts as a static method whose first argument is the instance,
        so you need to apply decorators that match this signature.

    Configuration:
        exception: An optional exception factory (or type) that accepts a single string
                   argument and returns an exception. If not `None`, then exceptions
                   raised by the wrapped method will be caught and replaced by the exception
                   this method produces.
    """

    __slots__ = ("_config", "_wrapped", "_exec", "_owner")

    exception: Callable[[str], Exception] | None = None

    def __init__(
        self,
        wrapped: Callable[Concatenate[TOwner, TParams], Coroutine[None, None, None]],
        config: TConfig,
    ) -> None:
        """
        Initialization.

        Arguments:
            wrapped: The wrapped method.
            config: Wrapper configuration.
        """
        self._config = config
        self._wrapped = wrapped
        self._exec: Callable[TParams, Coroutine[None, None, None]] | None = None
        self._owner: TOwner | None = None

    @property
    def config(self) -> TConfig:
        """
        Wrapper configuration.
        """
        return self._config

    @property
    def name(self) -> str:
        """
        The (qualified) name of the wrapped method.
        """
        return self._wrapped.__qualname__

    def __get__(
        self, owner: TOwner, obj_type: type[TOwner] | None = None
    ) -> Callable[TParams, Coroutine[None, None, None]]:
        """
        Descriptor implementation that makes the wrapper work as a bound method of its owner.
        """
        if owner is self._owner and self._exec is not None:
            return self._exec

        async def exec(*args: TParams.args, **kwargs: TParams.kwargs) -> None:
            return await self(owner, *args, **kwargs)

        self._exec = exec
        self._owner = owner

        return exec

    async def __call__(self, owner: TOwner, *args: TParams.args, **kwargs: TParams.kwargs) -> None:
        """
        Executes the wrapped *unbound* method with the given `owner`.

        Exceptions raised by the wrapped method will be transformed by the `exception` attribute.

        Arguments:
            owner: The owner instance of the wrapper (the `self` argument of the wrapped instance method).
            *args: The wrapped method's positional arguments.
            *kwargs: The wrapped method's keyword arguments.
        """
        try:
            await self._wrapped(owner, *args, **kwargs)
        except Exception as e:
            raise e if self.exception is None else self.exception(f"Method failed: {self.name}") from e
