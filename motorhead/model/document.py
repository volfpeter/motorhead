from pydantic import BaseModel, ConfigDict, Field

from .objectid import ObjectId


class BaseDocument(BaseModel):
    """
    Pydantic `BaseModel` for documents, embedded documents, and related models.

    It's just a convenience class that adds a default Pydantic `ConfigDict` with the
    necessary settings to enable custom types (e.g. `ObjectId`) and population by name
    in subclasses, so you don't have to set these settings yourself.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)


class Document(BaseDocument):
    """
    Pydantic base model for MongoDB documents.

    It exposes the `_id` attribute as `id`.
    """

    id: ObjectId = Field(alias="_id")
