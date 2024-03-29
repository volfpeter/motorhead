from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from typing import cast

import pytest
from bson.objectid import ObjectId
from motor.core import AgnosticClientSession, AgnosticDatabase

from motorhead import (
    BaseDocument,
    ClauseOrMongoQuery,
    DeleteError,
    Document,
    Field,
    Q,
    Service,
    ValidationError,
    delete_rule,
    validator,
)


class Person(Document):
    name: str
    lucky_number: int


QPerson = Q(Person)


class PersonData(BaseDocument):
    name: str
    lucky_number: int


class PersonService(Service[PersonData, PersonData]):
    collection_name = "person"


class PersonServiceWithRules(PersonService):
    @delete_rule("pre")
    async def _dr_never_delete_root(self, session: AgnosticClientSession, ids: Sequence[ObjectId]) -> None:
        cnt = await self.count_documents(
            cast(Field, QPerson.id).In(ids) & (QPerson.name == "root"),  # type: ignore[operator]
            options={"session": session},
        )
        if cnt > 0:
            raise ValueError("Cannot delete root.")

    @validator("insert-update")
    async def _v_root_case_insensitive(
        self,
        data: Person | PersonData,
        query: ClauseOrMongoQuery | None,
    ) -> None:
        if data.name.lower() == "root" and data.name != "root":
            raise ValueError("Root user name must be in lower-case.")

    @validator("insert-update")
    async def _v_root_unique(
        self,
        data: Person | PersonData,
        query: ClauseOrMongoQuery | None,
    ) -> None:
        if data.name.lower() != "root":
            return

        cnt = await self.count_documents(QPerson.name == "root")  # type: ignore[arg-type]
        if cnt > 0:
            raise ValueError("There can only be one root.")


@pytest.fixture(scope="session")
def person_service(*, database: AgnosticDatabase) -> PersonService:
    return PersonService(database)


@pytest.fixture(scope="session")
def person_service_with_rules(*, database: AgnosticDatabase) -> PersonServiceWithRules:
    return PersonServiceWithRules(database)


@asynccontextmanager
async def make_person(
    service: PersonService,
    *,
    name: str = "John",
    lucky_number: int = 401009,
    delete_service: PersonService | None = None,
) -> AsyncGenerator[Person, None]:
    pd = PersonData(name=name, lucky_number=lucky_number)
    person = Person(**await service.create(pd))

    yield person

    await (delete_service or service).delete_by_id(person.id)


class TestService:
    @pytest.mark.asyncio
    async def test_create(self, *, person_service: PersonService) -> None:
        pd = PersonData(name="Jack", lucky_number=6)
        result = await person_service.create(pd)
        assert isinstance(result, dict)
        assert result["name"] == pd.name
        assert result["lucky_number"] == pd.lucky_number
        assert isinstance(result["_id"], ObjectId)
        assert len(result) == 3

        p = Person(**result)
        assert isinstance(p.id, ObjectId)

        delete_result = await person_service.delete_by_id(p.id)
        assert delete_result.deleted_count == 1

    @pytest.mark.asyncio
    async def test_insert_one(self, *, person_service: PersonService) -> None:
        pd = PersonData(name="Jack", lucky_number=6)
        insert_result = await person_service.insert_one(pd)
        assert isinstance(insert_result.inserted_id, ObjectId)

        result = await person_service.get_by_id(insert_result.inserted_id)
        assert isinstance(result, dict)
        assert result["name"] == pd.name
        assert result["lucky_number"] == pd.lucky_number
        assert isinstance(result["_id"], ObjectId)
        assert len(result) == 3

        p = Person(**result)
        assert isinstance(p.id, ObjectId)

        delete_result = await person_service.delete_by_id(p.id)
        assert delete_result.deleted_count == 1

    @pytest.mark.asyncio
    async def test_insert_many(self, *, person_service: PersonService) -> None:
        pds = [PersonData(name=f"Person - {i}", lucky_number=i) for i in range(997)]
        insert_result = await person_service.insert_many(pds)
        assert len(insert_result.inserted_ids) == len(pds)
        assert await person_service.count_documents() == 997
        assert (await person_service.delete_many(None)).deleted_count == 997

    @pytest.mark.asyncio
    async def test_update(self, *, person_service: PersonService) -> None:
        async with make_person(person_service) as p:
            p_id = p.id
            assert p.name == "John"
            assert p.lucky_number == 401009

            updated = await person_service.update(p.id, PersonData(name="Paul", lucky_number=420618))
            updated_p = Person(**updated)

            assert updated["_id"] == p_id
            assert len(updated) == 3

            assert updated_p.name == "Paul"
            assert updated_p.lucky_number == 420618

            documents = await person_service.find().to_list(None)
            assert len(documents) == 1

    @pytest.mark.asyncio
    async def test_update_by_id(self, *, person_service: PersonService) -> None:
        async with make_person(person_service) as p:
            p_id = p.id
            assert p.name == "John"
            assert p.lucky_number == 401009

            update_result = await person_service.update_by_id(
                p.id, PersonData(name="Paul", lucky_number=420618)
            )
            assert update_result.modified_count == 1
            updated = await person_service.get_by_id(p.id)
            assert updated is not None
            updated_p = Person(**updated)

            assert updated["_id"] == p_id
            assert len(updated) == 3

            assert updated_p.name == "Paul"
            assert updated_p.lucky_number == 420618

            documents = await person_service.find().to_list(None)
            assert len(documents) == 1

    @pytest.mark.asyncio
    async def test_delete_rules_and_validators(
        self,
        *,
        person_service: PersonService,
        person_service_with_rules: PersonServiceWithRules,
    ) -> None:
        with pytest.raises(ValidationError, match="PersonServiceWithRules._v_root_case_insensitive"):
            async with make_person(person_service_with_rules, name="Root"):
                ...

        async with make_person(
            person_service_with_rules, name="root", delete_service=person_service
        ) as root:
            with pytest.raises(ValidationError, match="PersonServiceWithRules._v_root_unique"):
                async with make_person(person_service_with_rules, name="root"):
                    ...

            with pytest.raises(DeleteError, match="PersonServiceWithRules._dr_never_delete_root"):
                await person_service_with_rules.delete_by_id(root.id)
