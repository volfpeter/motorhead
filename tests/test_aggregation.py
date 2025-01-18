from dataclasses import dataclass
from typing import Any, get_args

import pytest

from motorhead import (
    Aggregation,
    AggregationStage,
    AgnosticDatabase,
    BaseDocument,
    Document,
    Service,
    make_aggregation_stage,
)

aggregation_stages = get_args(AggregationStage)


@dataclass(frozen=True)
class DummyClause:
    data: dict[str, Any]

    def to_mongo(self) -> dict[str, Any]:
        return self.data


class Person(Document):
    name: str
    lucky_number: int = -1
    group_id: int = 1

    @classmethod
    def group_id_from_int(cls, value: int) -> int:
        value = value % 10
        if value % 5 == 0:
            return 5
        if value % 3 == 0:
            return 3
        return 1


class PersonData(BaseDocument):
    name: str
    lucky_number: int = -1
    group_id: int = 1


class PersonService(Service[PersonData, PersonData]):
    collection_name = "test_aggregation_person"


@pytest.fixture(scope="session")
def person_service(*, database: AgnosticDatabase) -> PersonService:
    return PersonService(database)


@pytest.mark.parametrize(
    ("stage", "value"),
    [(stage, {"first": 1, "second": 2}) for stage in aggregation_stages],
)
def test_make_aggregation_stage(stage: AggregationStage, value: dict[str, Any]) -> None:
    result = make_aggregation_stage(stage, value)
    assert isinstance(result, dict)
    assert len(result) == 1
    assert result[stage] is value

    result = make_aggregation_stage(stage, DummyClause(value))
    assert isinstance(result, dict)
    assert len(result) == 1
    assert result[stage] is value


class TestAggregation:
    @pytest.mark.parametrize(
        ("stage", "value"),
        [(stage, {"first": 1, "second": 2}) for stage in aggregation_stages],
    )
    def test_stage(self, stage: AggregationStage, value: dict[str, Any]) -> None:
        aggr = Aggregation()
        result = aggr.stage(stage, value)
        assert isinstance(result, list)
        assert result is aggr
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0][stage] is value

        aggr = Aggregation()
        result = aggr.stage(stage, DummyClause(value))
        assert isinstance(result, list)
        assert result is aggr
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0][stage] is value

    def test_init(self) -> None:
        dummy_stage_data = {"first": 1, "second": 2}

        aggr = Aggregation(make_aggregation_stage(stage, dummy_stage_data) for stage in aggregation_stages)
        assert len(aggr) == len(aggregation_stages)

        for stage_id, stage_data in zip(aggregation_stages, aggr, strict=True):
            assert stage_data[stage_id] is dummy_stage_data

    def test_stage_chaining(self) -> None:
        dummy_stage_data = {"first": 1, "second": 2}

        original_aggr = aggr = Aggregation()

        for stage in aggregation_stages:
            aggr = aggr.stage(stage, dummy_stage_data)

        for stage_id, stage_data in zip(aggregation_stages, aggr, strict=True):
            assert stage_data[stage_id] is dummy_stage_data

        assert original_aggr == aggr
        assert len(aggr) == len(aggregation_stages)

        for stage_id, stage_data in zip(aggregation_stages, aggr, strict=True):
            assert stage_data[stage_id] is dummy_stage_data

    @pytest.mark.asyncio(loop_scope="session")
    async def test_with_service(self, database: AgnosticDatabase, person_service: PersonService) -> None:
        try:
            insert_result = await person_service.insert_many(
                PersonData(
                    name=f"Person {i}",
                    lucky_number=1000 + i,
                    group_id=Person.group_id_from_int(i),
                )
                for i in range(100)
            )
            assert len(insert_result.inserted_ids) == 100

            # -- Count all documents
            result = [doc async for doc in person_service.aggregate(Aggregation().stage("$count", "total"))]
            assert len(result) == 1
            assert isinstance(result[0], dict)
            assert len(result[0]) == 1
            assert result[0]["total"] == 100

            # -- Filter and count documents
            result = [
                doc
                async for doc in person_service.aggregate(
                    Aggregation().stage("$match", {"lucky_number": {"$lt": 1024}}).stage("$count", "total")
                )
            ]
            assert len(result) == 1
            assert isinstance(result[0], dict)
            assert len(result[0]) == 1
            assert result[0]["total"] == 24

            # -- Sort and count documents in groups
            result = [
                doc
                async for doc in person_service.aggregate(
                    Aggregation()
                    .stage("$sort", {"lucky_number": 1})
                    .stage("$group", {"_id": "$group_id", "size": {"$count": {}}})
                    .stage("$sort", {"size": -1})
                )
            ]
            assert result == [{"_id": 1, "size": 50}, {"_id": 3, "size": 30}, {"_id": 5, "size": 20}]

        finally:
            await database.drop_collection(person_service.collection_name)
