from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, cast

from bson import ObjectId
from motor.core import AgnosticClientSession
from motorhead import (
    ClauseOrMongoQuery,
    CollectionOptions,
    Field,
    IndexData,
    Service,
    delete_rule,
    validator,
)

from .model import QTreeNode, TreeNodeCreate, TreeNodeUpdate


class TreeNodeService(Service[TreeNodeCreate, TreeNodeUpdate]):
    """
    Tree node database services.
    """

    __slots__ = ()

    collection_name: str = "tree_nodes"

    collection_options: CollectionOptions | None = None

    indexes = {
        "unique-name": IndexData(
            keys="name",
            unique=True,
            collation={"locale": "en", "strength": 1},
        ),
    }

    @delete_rule("pre")  # Delete rule that removes the subtrees of deleted nodes.
    async def dr_delete_subtree(self, session: AgnosticClientSession, ids: Sequence[ObjectId]) -> None:
        child_ids = await self.find_ids(cast(Field, QTreeNode.parent).In(ids).to_mongo(), session=session)
        if len(child_ids) > 0:
            # Recursion
            await self.delete_many(cast(Field, QTreeNode.id).In(child_ids), options={"session": session})

    @delete_rule("deny")  # Delete rule that prevents the removal of root nodes.
    async def dr_deny_if_root(self, session: AgnosticClientSession, ids: Sequence[ObjectId]) -> None:
        root_cnt = await self.count_documents(
            cast(Field, QTreeNode.id).In(ids) & (QTreeNode.parent == None),  # type: ignore[operator] # noqa [711]
            options={"session": session},
        )
        if root_cnt > 0:
            raise ValueError("Can not delete root nodes.")

    @validator("insert-update")
    async def v_parent_valid(
        self, query: ClauseOrMongoQuery | None, data: TreeNodeCreate | TreeNodeUpdate
    ) -> None:
        if data.parent is None:  # No parent node is always fine
            return

        if not await self.exists(data.parent):  # Parent must exist.
            raise ValueError("Parent does not exist.")

        if isinstance(data, TreeNodeCreate):  # No more checks during creation.
            return

        matched_ids = (await self.find_ids(query)) if isinstance(data, TreeNodeUpdate) else []
        if data.parent in matched_ids:  # Self reference is forbidden.
            raise ValueError("Self-reference.")

    async def _convert_for_insert(self, data: TreeNodeCreate) -> dict[str, Any]:
        return {
            **(await super()._convert_for_insert(data)),
            "created_at": datetime.now(timezone.utc),
        }
