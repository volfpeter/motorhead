from collections.abc import Sequence
from typing import Any

import pytest

from motorhead import operator as op
from motorhead.typing import Clause

# -- Base tests

key_value_operator_fixtures = (
    ("key", "value"),
    (
        ("int_prop", 42),
        ("str_prop", "42"),
        ("float_prop", 2.71),
        ("false_prop", False),
        ("true_prop", True),
        ("dict_prop", {"val": 0}),
        ("set_prop", {42}),
        ("list_prop", [1, 2, 3]),
        ("tuple_prop", (1, 2, 3)),
    ),
)


class _BaseKeyValueOperatorTest:
    Operator: type[op.KeyValueOperator] = None  # type: ignore[assignment]
    operator_string: str = None  # type: ignore[assignment]

    def test_operator(self) -> None:
        assert self.Operator._operator == self.operator_string

    @pytest.mark.parametrize(*key_value_operator_fixtures)
    def test_to_mongo(self, *, key: str, value: Any) -> None:
        co = self.Operator(key, value)
        assert co.key == key
        assert co.value == value
        self.assert_to_mongo_result(co.to_mongo(), key=key, value=value)

    def assert_to_mongo_result(self, result: Any, *, key: str, value: Any) -> None:
        assert result == {key: {self.Operator._operator: value}}


# -- Base operator classes


class TestClauseOperator:
    def test_default_subclassing(self) -> None:
        class CO(op.ClauseOperator): ...

        assert CO._operator == "$co"

    @pytest.mark.parametrize(
        ("operator",),
        (
            ("co",),
            ("__co",),
            ("$clause_operator",),
        ),
    )
    def test_subclass_with_custom_operator(self, *, operator: str) -> None:
        class CO(op.ClauseOperator):
            _operator = operator

        assert CO._operator == operator

    @pytest.mark.parametrize(
        ("clauses",),
        (
            ([],),
            ([op.Lt("prop_1", 1)],),
            (
                [
                    op.Gt("prop_1", 1),
                    op.In("prop_2", [1, 2, 3]),
                ],
            ),
        ),
    )
    def test_to_mongo_with_default_subclassing(self, *, clauses: Sequence["Clause"]) -> None:
        class CO(op.ClauseOperator): ...

        co = CO(*clauses)
        co_clauses = list(co.clauses)
        assert co_clauses is not clauses
        assert co_clauses == clauses
        assert co.to_mongo() == {"$co": [c.to_mongo() for c in co_clauses]}


class TestKeyValueOperator:
    def test_default_subclassing(self) -> None:
        class KVO(op.KeyValueOperator): ...

        assert KVO._operator == "$kvo"

    @pytest.mark.parametrize(
        ("operator",),
        (
            ("kvo",),
            ("__kvo",),
            ("$key_value_operator",),
        ),
    )
    def test_subclass_with_custom_operator(self, *, operator: str) -> None:
        class KVO(op.KeyValueOperator):
            _operator = operator

        assert KVO._operator == operator

    @pytest.mark.parametrize(
        ("property_name", "property_value"),
        (
            ("int_prop", 42),
            ("str_prop", "42"),
            ("float_prop", 2.71),
            ("dict_prop", {"val": 0}),
            ("set_prop", {42}),
            ("list_prop", [1, 2, 3]),
            ("tuple_prop", (1, 2, 3)),
        ),
    )
    def test_to_mongo_with_default_subclassing(self, *, property_name: str, property_value: Any) -> None:
        class KVO(op.KeyValueOperator): ...

        kvo = KVO(property_name, property_value)
        assert kvo.key == property_name
        assert kvo.value == property_value
        assert kvo.to_mongo() == {property_name: {"$kvo": property_value}}


# -- Raw operator


class TestRaw:
    def test_to_mongo(self) -> None:
        data = {"$and": {"first": 11, "second": "22", 3: 33, "rest": [44, 55, 66]}}
        raw = op.Raw(data)
        assert raw._data is data
        assert raw.to_mongo() is not data
        assert raw.to_mongo() == data


# -- Comparison operators


class TestEq(_BaseKeyValueOperatorTest):
    Operator = op.Eq
    operator_string = "$eq"


class TestDirectEq(_BaseKeyValueOperatorTest):
    Operator = op.DirectEq
    operator_string = ""

    def assert_to_mongo_result(self, result: Any, *, key: str, value: Any) -> None:
        assert result == {key: value}


class TestNe(_BaseKeyValueOperatorTest):
    Operator = op.Ne
    operator_string = "$ne"


class TestGt(_BaseKeyValueOperatorTest):
    Operator = op.Gt
    operator_string = "$gt"


class TestGte(_BaseKeyValueOperatorTest):
    Operator = op.Gte
    operator_string = "$gte"


class TestLt(_BaseKeyValueOperatorTest):
    Operator = op.Lt
    operator_string = "$lt"


class TestLte(_BaseKeyValueOperatorTest):
    Operator = op.Lte
    operator_string = "$lte"


class TestIn(_BaseKeyValueOperatorTest):
    Operator = op.In
    operator_string = "$in"


class TestNotIn(_BaseKeyValueOperatorTest):
    Operator = op.NotIn
    operator_string = "$nin"


# -- Logical operators


class _BaseClauseOperatorTest:
    Operator: type[op.ClauseOperator] = None  # type: ignore[assignment]
    operator_string: str = None  # type: ignore[assignment]

    def test_operator(self) -> None:
        assert self.Operator._operator == self.operator_string

    @pytest.mark.parametrize(
        ("clauses",),
        (
            ([],),
            ([op.Lt("prop_1", 1)],),
            (
                [
                    op.Gt("prop_1", 1),
                    op.In("prop_2", [1, 2, 3]),
                ],
            ),
        ),
    )
    def test_to_mongo(self, *, clauses: Sequence["Clause"]) -> None:
        lo = self.Operator(*clauses)
        lo_clauses = list(lo.clauses)
        assert lo_clauses is not clauses
        assert lo_clauses == clauses
        self.assert_to_mongo_result(lo.to_mongo(), clauses=clauses)

    def assert_to_mongo_result(self, result: Any, *, clauses: Sequence["Clause"]) -> None:
        assert result == {self.operator_string: [c.to_mongo() for c in clauses]}


class TestAnd(_BaseClauseOperatorTest):
    Operator = op.And
    operator_string = "$and"


class TestNot(_BaseClauseOperatorTest):
    Operator = op.Not
    operator_string = "$not"


class TestOr(_BaseClauseOperatorTest):
    Operator = op.Or
    operator_string = "$or"


class TestNor(_BaseClauseOperatorTest):
    Operator = op.Nor
    operator_string = "$nor"


# -- Element operators


class TestExists(_BaseKeyValueOperatorTest):
    Operator = op.Exists
    operator_string = "$exists"

    @pytest.mark.parametrize(*key_value_operator_fixtures)
    def test_to_mongo(self, *, key: str, value: Any) -> None:
        if isinstance(value, bool):
            super().test_to_mongo(key=key, value=value)
        else:
            with pytest.raises(ValueError):
                self.Operator(key, value)


class TestType(_BaseKeyValueOperatorTest):
    Operator = op.Type
    operator_string = "$type"

    @pytest.mark.parametrize(*key_value_operator_fixtures)
    def test_to_mongo(self, *, key: str, value: Any) -> None:
        if isinstance(value, str):
            super().test_to_mongo(key=key, value=value)
        else:
            with pytest.raises(ValueError):
                self.Operator(key, value)


# -- Array operators


class TestAll(_BaseKeyValueOperatorTest):
    Operator = op.All
    operator_string = "$all"

    @pytest.mark.parametrize(*key_value_operator_fixtures)
    def test_to_mongo(self, *, key: str, value: Any) -> None:
        if isinstance(value, list):
            super().test_to_mongo(key=key, value=value)
        else:
            with pytest.raises(ValueError):
                self.Operator(key, value)


class TestElemMatch(_BaseKeyValueOperatorTest):
    Operator = op.ElemMatch
    operator_string = "$elemMatch"

    @pytest.mark.parametrize(*key_value_operator_fixtures)
    def test_to_mongo(self, *, key: str, value: Any) -> None:
        if isinstance(value, dict):
            super().test_to_mongo(key=key, value=value)
        else:
            with pytest.raises(ValueError):
                self.Operator(key, value)


class TestSize(_BaseKeyValueOperatorTest):
    Operator = op.Size
    operator_string = "$size"

    @pytest.mark.parametrize(*key_value_operator_fixtures)
    def test_to_mongo(self, *, key: str, value: Any) -> None:
        if isinstance(value, int):
            super().test_to_mongo(key=key, value=value)
        else:
            with pytest.raises(ValueError):
                self.Operator(key, value)
