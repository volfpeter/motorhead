from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import TypeAlias

    from typing_extensions import Self

    from .typing import Clause

AggregationStage = Literal[
    "$addFields",
    "$bucket",
    "$bucketAuto",
    "$changeStream",
    "$changeStreamSplitLargeEvent",
    "$collStats",
    "$count",
    "$currentOp",
    "$densify",
    "$documents",
    "$facet",
    "$fill",
    "$geoNear",
    "$graphLookup",
    "$group",
    "$indexStats",
    "$limit",
    "$listLocalSessions",
    "$listSampledQueries",
    "$listSearchIndexes",
    "$listSessions",
    "$lookup",
    "$match",
    "$merge",
    "$out",
    "$planCacheStats",
    "$project",
    "$querySettings",
    "$redact",
    "$replaceRoot",
    "$replaceWith",
    "$sample",
    "$search",
    "$searchMeta",
    "$set",
    "$setWindowFields",
    "$shardedDataDistribution",
    "$skip",
    "$sort",
    "$sortByCount",
    "$unionWith",
    "$unset",
    "$unwind",
    "$vectorSearch",
]
"""Aggregation pipeline stage."""


AggregationData: TypeAlias = Any


def make_aggregation_stage(
    stage: AggregationStage, value: AggregationData | Clause
) -> dict[str, AggregationData]:
    """
    Creates an aggregation pipeline stage.

    Arguments:
        stage: The stage operator.
        value: The stage operator's content.

    Returns:
        The aggregation pipeline stage.
    """
    return {stage: value.to_mongo() if hasattr(value, "to_mongo") else value}


class Aggregation(list[dict[str, AggregationData]]):
    """Aggregation pipeline."""

    def __init__(self, stages: Iterable[AggregationData] = ()) -> None:
        """
        Initialization.

        Arguments:
            stages: The aggregation pipeline stages.
        """
        super().__init__(stages)

    def stage(self, stage: AggregationStage, value: AggregationData | Clause) -> Self:
        """
        Adds the stage to the aggregation pipeline.

        Arguments:
            stage: The stage operator.
            value: The stage operator's content.

        Returns:
            The aggregation pipeline.
        """
        self.append(make_aggregation_stage(stage, value))
        return self
