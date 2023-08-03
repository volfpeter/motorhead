from datetime import date, datetime
from typing import Any

import pytest
from pydantic import BaseModel

from motorhead import Clause, Document, Field, Q, Query, Queryable
from motorhead import operator as op


@pytest.fixture
def name_field() -> Field:
    return Field(name="name")


class User(Document):
    name: str
    lucky_number: int


QUser = Q(User)


class TestField:
    def test_field_name(self, *, name_field: Field) -> None:
        assert name_field.name == "name"

    def test_lt(self, *, name_field: Field) -> None:
        self.assert_query_clause(
            name_field < 42,
            operator=op.Lt,
            value=42,
        )

    def test_le(self, *, name_field: Field) -> None:
        self.assert_query_clause(
            name_field <= 42,
            operator=op.Lte,
            value=42,
        )

    @pytest.mark.parametrize(
        ("value", "operator"),
        (
            (
                (42, op.DirectEq),
                (3.14, op.DirectEq),
                ("42", op.DirectEq),
                (date.today(), op.DirectEq),
                (datetime.now(), op.DirectEq),
                ([], op.Eq),
                ([1, 2, 3], op.Eq),
                ((1, 2, 3), op.Eq),
                ({1, 2, 3}, op.Eq),
                ({1: 11, 2: 22, 3: 33}, op.Eq),
            )
        ),
    )
    def test_eq(self, *, name_field: Field, operator: type[op.KeyValueOperator], value: Any) -> None:
        self.assert_query_clause(
            name_field == value,
            operator=operator,
            value=value,
        )

    def test_ne(self, *, name_field: Field) -> None:
        self.assert_query_clause(
            name_field != 42,
            operator=op.Ne,
            value=42,
        )

    def test_gt(self, *, name_field: Field) -> None:
        self.assert_query_clause(
            name_field > 42,
            operator=op.Gt,
            value=42,
        )

    def test_ge(self, *, name_field: Field) -> None:
        self.assert_query_clause(
            name_field >= 42,
            operator=op.Gte,
            value=42,
        )

    def test_in(self, *, name_field: Field) -> None:
        self.assert_query_clause(
            name_field.In(42),
            operator=op.In,
            value=42,
        )

    def test_not_in(self, *, name_field: Field) -> None:
        self.assert_query_clause(
            name_field.NotIn(42),
            operator=op.NotIn,
            value=42,
        )

    def test_exists(self, *, name_field: Field) -> None:
        self.assert_query_clause(
            name_field.Exists(True),
            operator=op.Exists,
            value=True,
        )
        self.assert_query_clause(
            name_field.Exists(False),
            operator=op.Exists,
            value=False,
        )

    def test_all(self, *, name_field: Field) -> None:
        items = [1, 2, 3]
        self.assert_query_clause(
            name_field.All(items),
            operator=op.All,
            value=items,
        )

    def test_elem_match(self, *, name_field: Field) -> None:
        data = {"one": 2, "two": 4}
        self.assert_query_clause(
            name_field.ElemMatch(data),
            operator=op.ElemMatch,
            value=data,
        )

    def test_size(self, *, name_field: Field) -> None:
        self.assert_query_clause(
            name_field.Size(42),
            operator=op.Size,
            value=42,
        )

    @pytest.mark.parametrize(("value",), (("",), ("number",), ("string",), ("date",)))
    def test_type(self, *, name_field: Field, value: str) -> None:
        self.assert_query_clause(
            name_field.Type(value),
            operator=op.Type,
            value=value,
        )

    def assert_query_clause(
        self, query: Any, *, operator: type[op.KeyValueOperator], field_name: str = "name", value: Any
    ) -> None:
        assert isinstance(query, Query)
        assert isinstance(query._clause, operator)
        assert query._clause.key == field_name
        assert query._clause.value == value


class TestQ:
    def test_result(self) -> None:
        assert not issubclass(QUser, Query)
        assert issubclass(QUser, Queryable)
        assert not issubclass(QUser, Document)
        assert not issubclass(QUser, BaseModel)

    def test_fields(self) -> None:
        assert "id" in User.model_fields
        assert "name" in User.model_fields
        assert "lucky_number" in User.model_fields

        for field_name in User.model_fields.keys():
            field = getattr(QUser, field_name)
            assert isinstance(field, Field)
            assert field.name == field_name if field_name != "id" else "_id"

    @pytest.mark.parametrize(
        ("property_name",),
        (
            # Not a complete list of BaseModel methods, just some important ones.
            ("from_orm",),
            ("model_config",),
            ("model_fields",),
            ("model_dump",),
            ("model_copy",),
            ("model_dump",),
            ("model_dump_json",),
            ("model_dump_python",),
        ),
    )
    def test_missing_basemodel_properties(self, *, property_name: str) -> None:
        assert not hasattr(QUser, property_name)


class TestQuery:
    def test_empty(self) -> None:
        query = Query()
        assert query._clause is None
        assert query.to_mongo() == {}

    @pytest.mark.parametrize(
        ("clause",),
        (
            (op.Eq("name", "what"),),
            (op.And(op.Eq("name", "what"), op.Or(op.Eq("name", "notwhat"), op.Lt("lucky_number", 10))),),
        ),
    )
    def test_clone(self, *, clause: Clause | None) -> None:
        base = Query(clause)
        clone = base.clone()

        assert clone is not base
        assert base._clause == clone._clause
        assert base.to_mongo() == clone.to_mongo()

    def test_and(self) -> None:
        q_empty = Query()
        q_1: Query = QUser.name == "unknown"  # type: ignore[assignment]
        q_2: Query = QUser.lucky_number < 10  # type: ignore[assignment]

        empty_1 = q_empty & q_1
        assert isinstance(empty_1, Query)
        assert isinstance(empty_1._clause, op.DirectEq)
        assert empty_1._clause.key == "name"
        assert empty_1._clause.value == "unknown"

        empty_1_2 = empty_1 & q_2
        assert isinstance(empty_1_2, Query)
        assert isinstance(empty_1_2._clause, op.And)
        assert list(empty_1_2._clause.clauses) == [q_1._clause, q_2._clause]

        lte_clause = op.Gte("lucky_number", 5)
        q_full = empty_1_2 & lte_clause
        assert isinstance(q_full, Query)
        assert isinstance(q_full._clause, op.And)
        assert list(q_full._clause.clauses) == [q_1._clause, q_2._clause, lte_clause]
        assert q_full.to_mongo() == {
            "$and": [
                {"name": "unknown"},
                {"lucky_number": {"$lt": 10}},
                {"lucky_number": {"$gte": 5}},
            ]
        }

    def test_or(self) -> None:
        q_empty = Query()
        q_1: Query = QUser.name == "unknown"  # type: ignore[assignment]
        q_2: Query = QUser.lucky_number < 10  # type: ignore[assignment]

        empty_1 = q_empty | q_1
        assert isinstance(empty_1, Query)
        assert isinstance(empty_1._clause, op.DirectEq)
        assert empty_1._clause.key == "name"
        assert empty_1._clause.value == "unknown"

        empty_1_2 = empty_1 | q_2
        assert isinstance(empty_1_2, Query)
        assert isinstance(empty_1_2._clause, op.Or)
        assert list(empty_1_2._clause.clauses) == [q_1._clause, q_2._clause]

        lte_clause = op.Gte("lucky_number", 5)
        q_full = empty_1_2 | lte_clause
        assert isinstance(q_full, Query)
        assert isinstance(q_full._clause, op.Or)
        assert list(q_full._clause.clauses) == [q_1._clause, q_2._clause, lte_clause]
        assert q_full.to_mongo() == {
            "$or": [
                {"name": "unknown"},
                {"lucky_number": {"$lt": 10}},
                {"lucky_number": {"$gte": 5}},
            ]
        }

    def test_and_or(self) -> None:
        q_1: Query = QUser.name == "unknown"  # type: ignore[assignment]
        q_2: Query = QUser.lucky_number > 10  # type: ignore[assignment]
        q_3: Query = QUser.lucky_number < 0  # type: ignore[assignment]

        q_full = q_1 & (q_2 | q_3)
        assert isinstance(q_full, Query)
        assert isinstance(q_full._clause, op.And)
        assert q_full.to_mongo() == {
            "$and": [
                {"name": "unknown"},
                {
                    "$or": [
                        {"lucky_number": {"$gt": 10}},
                        {"lucky_number": {"$lt": 0}},
                    ]
                },
            ]
        }

        clone = q_full.clone()
        assert clone is not q_full
        assert clone.to_mongo() == q_full.to_mongo()

    def test_or_and(self) -> None:
        q_1: Query = QUser.name == "unknown"  # type: ignore[assignment]
        q_2: Query = QUser.lucky_number < 10  # type: ignore[assignment]
        q_3: Query = QUser.lucky_number > 0  # type: ignore[assignment]

        q_full = q_1 | (q_2 & q_3)
        assert isinstance(q_full, Query)
        assert isinstance(q_full._clause, op.Or)
        assert q_full.to_mongo() == {
            "$or": [
                {"name": "unknown"},
                {
                    "$and": [
                        {"lucky_number": {"$lt": 10}},
                        {"lucky_number": {"$gt": 0}},
                    ]
                },
            ]
        }

        clone = q_full.clone()
        assert clone is not q_full
        assert clone.to_mongo() == q_full.to_mongo()
