import pytest
from bson.objectid import ObjectId
from motor.core import AgnosticDatabase

from motorhead import BaseDocument, Document, Service


class Person(Document):
    name: str
    lucky_number: int


class PersonData(BaseDocument):
    name: str
    lucky_number: int


class PersonService(Service[PersonData, PersonData]):
    collection_name = "person"


@pytest.fixture
def person_service(*, database: AgnosticDatabase) -> PersonService:
    return PersonService(database)


class TestService:
    @pytest.mark.asyncio
    async def test_create(self, *, person_service: PersonService) -> None:
        pd = PersonData(name="Jack", lucky_number=6)
        insert_result = await person_service.insert_one(pd)
        assert insert_result.acknowledged

        result = await person_service.get_by_id(insert_result.inserted_id)
        assert isinstance(result, dict)
        assert result["name"] == pd.name
        assert result["lucky_number"] == pd.lucky_number
        assert isinstance(result["_id"], ObjectId)
        assert len(result) == 3

        p = Person(**result)
        assert isinstance(p.id, ObjectId)
