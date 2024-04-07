import asyncio
import inspect
from collections.abc import AsyncGenerator, Callable, Generator
from functools import wraps
from typing import (
    Annotated,
    Any,
    Concatenate,
    Coroutine,
    Generic,
    ParamSpec,
    Protocol,
    TypeVar,
    cast,
    overload,
)

from fastapi import Depends, FastAPI

Tcov = TypeVar("Tcov", covariant=True)
TMemo = TypeVar("TMemo")

TOwner = TypeVar("TOwner")
TResult = TypeVar("TResult")
TParams = ParamSpec("TParams")


def _replace_self_signature(
    func: Callable[TParams, TResult],
    self_param: inspect.Parameter,
) -> Callable[TParams, TResult]:
    """
    Replaces the signature of the `self` argument of `func` with the given one.

    Arguments:
        func: The function whose self argument should be replaced.
        self_param: The new parameter description for the `self` argument.

    Returns:
        The received function with the updated annotations.

    Raises:
        ValueError: If `func` has no `self` argument.
    """
    signature = inspect.signature(func)
    if "self" not in signature.parameters:
        raise ValueError("Method has no self argument.")

    func.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=(
            self_param,
            *(v for k, v in signature.parameters.items() if k != "self"),
        )
    )
    return func


class Dependency(Protocol[Tcov]):
    """Generic FastAPI dependency function protocol."""

    def __call__(
        self, *args: Any, **kwargs: Any
    ) -> Tcov | Coroutine[Any, Any, Tcov] | Generator[Tcov, Any, Any] | AsyncGenerator[Tcov, Any]:
        ...


class IdMemo(Generic[TMemo]):
    __slots__ = ("_hash", "_value")

    def __init__(self) -> None:
        self._hash: int | None = None
        self._value: TMemo | None = None

    def __contains__(self, key: int) -> bool:
        return self._hash == key

    @property
    def value(self) -> TMemo:
        if self._value is None:
            raise KeyError("Memo value accessed before first use.")

        return self._value

    def store(self, key: int, value: TMemo) -> TMemo:
        self._hash = key
        self._value = value
        return value

    def hash(self, *items: Any) -> int:
        return hash(tuple(id(i) for i in items))


class SelfWrapper:
    @classmethod
    def sync_method(
        cls,
        func: Callable[Concatenate[TOwner, TParams], TResult],
        owner: TOwner | None,
    ) -> Callable[TParams, TResult]:
        @wraps(func)
        def do(*args: TParams.args, **kwargs: TParams.kwargs) -> TResult:
            func_self: TOwner = kwargs.pop("self") if "self" in kwargs else owner  # type: ignore[assignment]
            if func_self is None:
                raise RuntimeError("Missing self argument.")

            return func(func_self, *args, **kwargs)

        return do

    @classmethod
    def sync_generator(
        cls,
        func: Callable[Concatenate[TOwner, TParams], Generator[TResult, Any, Any]],
        owner: TOwner | None,
    ) -> Callable[TParams, Generator[TResult, None, None]]:
        @wraps(func)
        def do(*args: TParams.args, **kwargs: TParams.kwargs) -> Generator[TResult, None, None]:
            func_self: TOwner = kwargs.pop("self") if "self" in kwargs else owner  # type: ignore[assignment]
            if func_self is None:
                raise RuntimeError("Missing self argument.")

            yield from func(func_self, *args, **kwargs)

        return do

    @classmethod
    def async_method(
        cls,
        func: Callable[Concatenate[TOwner, TParams], Coroutine[None, None, TResult]],
        owner: TOwner | None,
    ) -> Callable[TParams, Coroutine[None, None, TResult]]:
        @wraps(func)
        async def do(*args: TParams.args, **kwargs: TParams.kwargs) -> TResult:
            func_self: TOwner = kwargs.pop("self") if "self" in kwargs else owner  # type: ignore[assignment]
            if func_self is None:
                raise RuntimeError("Missing self argument.")

            return await func(func_self, *args, **kwargs)

        return do

    @classmethod
    def async_generator(
        cls,
        func: Callable[
            Concatenate[TOwner, TParams],
            AsyncGenerator[TResult, None],
        ],
        owner: TOwner | None,
    ) -> Callable[TParams, AsyncGenerator[TResult, None]]:
        @wraps(func)
        async def do(*args: TParams.args, **kwargs: TParams.kwargs) -> AsyncGenerator[TResult, None]:
            func_self: TOwner = kwargs.pop("self") if "self" in kwargs else owner  # type: ignore[assignment]
            if func_self is None:
                raise RuntimeError("Missing self argument.")

            async for res in func(func_self, *args, **kwargs):
                yield res

        return do


class SelfDependent(Generic[TOwner, TParams, TResult]):
    """
    Descriptor whose value is a method (FastAPI dependency) with an annotated
    `self` argument that can be processed and used by FastAPI as a dependency.
    """

    __slots__ = ("_wrapped", "_factory", "_memo")

    def __init__(
        self,
        wrapped: Callable[Concatenate[TOwner, TParams], TResult],
        *,
        factory: Dependency[TOwner] | None = None,
    ) -> None:
        """
        Initialization.

        Arguments:
            wrapped: The wrapped function.
            factory: An optional factory for creating `self` instances.
        """
        self._wrapped = wrapped
        self._factory = factory
        self._memo = IdMemo[Callable[TParams, TResult]]()

    def __get__(self, owner: TOwner | None, obj_type: type[TOwner]) -> Callable[TParams, TResult]:
        memo = self._memo
        hcurrent = memo.hash(owner, obj_type)
        if hcurrent in memo:
            return self._memo.value

        result: Callable[TParams, TResult]
        wrapped = self._wrapped
        if inspect.isgeneratorfunction(wrapped):
            result = SelfWrapper.sync_generator(wrapped, owner)  # type: ignore[assignment]
        elif inspect.isasyncgenfunction(wrapped):
            result = SelfWrapper.async_generator(wrapped, owner)  # type: ignore[assignment]
        elif asyncio.iscoroutinefunction(wrapped):
            result = SelfWrapper.async_method(wrapped, owner)  # type: ignore[assignment]
        else:
            result = SelfWrapper.sync_method(wrapped, owner)

        _replace_self_signature(
            result,
            inspect.Parameter(
                "self",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Annotated[obj_type, Depends(self._factory or obj_type)],
            ),
        )

        return self._memo.store(hcurrent, result)


BoundMethod = Callable[Concatenate[TOwner, TParams], TResult]


@overload
def selfdependent(
    factory: None = None,
) -> Callable[[BoundMethod[TOwner, TParams, TResult]], SelfDependent[TOwner, TParams, TResult]]:
    ...


@overload
def selfdependent(
    factory: Dependency[TOwner],
) -> Callable[[BoundMethod[TOwner, TParams, TResult]], SelfDependent[TOwner, TParams, TResult]]:
    ...


def selfdependent(
    factory: Dependency[TOwner] | None = None,
) -> Callable[[BoundMethod[TOwner, TParams, TResult]], SelfDependent[TOwner, TParams, TResult]]:
    def decorator(
        func: Callable[Concatenate[TOwner, TParams], TResult],
    ) -> SelfDependent[TOwner, TParams, TResult]:
        return SelfDependent[TOwner, TParams, TResult](wrapped=func, factory=factory)

    return decorator


def make_foo(base_1: float, base_2: float) -> "Foo":
    return Foo(base_1 + base_2)


class Foo:
    def __init__(self, base: float) -> None:
        self._base = base

    @selfdependent(make_foo)
    def sync_method(self, mul: float | None = None) -> float:
        return self._base if mul is None else (self._base * mul)

    @selfdependent()
    async def async_method(self, mul: float | None = None) -> float:
        return self._base if mul is None else (self._base * mul)

    @selfdependent()
    def sync_generator(self, exp: float) -> Generator[float, None, None]:
        yield cast(float, self._base**exp)

    @selfdependent()
    async def async_generator(self, exp: float) -> AsyncGenerator[float, None]:
        yield cast(float, self._base**exp)


DependsSyncMethod = Annotated[float, Depends(Foo.sync_method)]
DependsAsyncMethod = Annotated[float, Depends(Foo.async_method)]
DependsSyncGenerator = Annotated[float, Depends(Foo.sync_generator)]
DependsAsyncGenerator = Annotated[float, Depends(Foo.async_generator)]
app = FastAPI()


@app.get("/manual")
async def manual() -> float:
    foo = Foo(3)
    # Validate that there are no mypy errors and every method behaves as expected.
    result = await foo.async_method()
    if foo.sync_method() != result:
        raise ValueError("Should be equal.")

    generator_result = next(foo.sync_generator(2))
    if result**2 != generator_result:
        raise ValueError("Should be equal.")

    generator_result = await anext(foo.async_generator(2))
    if result**2 != generator_result:
        raise ValueError("Should be equal.")

    return result


@app.get("/sync-method")
def sync_methode(value: DependsSyncMethod) -> float:
    return value


@app.get("/async-method")
async def async_method(value: DependsAsyncMethod) -> float:
    return value


@app.get("/sync-generator")
async def sync_generator(value: DependsSyncGenerator) -> float:
    return value


@app.get("/async-generator")
async def async_generator(value: DependsAsyncGenerator) -> float:
    return value
