from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any

from bson import ObjectId as BSONObjectId
from bson.errors import InvalidId
from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema
from pydantic_core.core_schema import (
    ValidationInfo,
    str_schema,
)


class ObjectId(BSONObjectId):
    """
    Pydantic compatible `bson.objectid.ObjectId` field.
    """

    @classmethod
    def __get_validators__(cls) -> Generator[Callable[[Any, ValidationInfo], Any], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, v: Any, _: ValidationInfo) -> ObjectId:
        if isinstance(v, bytes):
            v = v.decode("utf-8")
        try:
            return ObjectId(v)
        except InvalidId as e:
            raise ValueError("Invalid ObjectId") from e

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.json_or_python_schema(
            python_schema=core_schema.general_plain_validator_function(cls.validate),
            json_schema=str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda instance: str(instance)),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(schema)
        json_schema.update(type="string", example="64c571cb685348872e3a2925")
        return json_schema
