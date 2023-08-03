from motorhead import BaseDocument, Document, ObjectId, Q, UTCDatetime
from pydantic import ConfigDict


class TreeNode(Document):
    """
    Tree node document model.
    """

    name: str
    parent: ObjectId | None = None
    created_at: UTCDatetime


QTreeNode = Q(TreeNode)
"""Queryable class for the `TreeNode` collection."""


class TreeNodeCreate(BaseDocument):
    """
    Tree node creation model.
    """

    name: str
    parent: ObjectId | None = None


class TreeNodeUpdate(BaseDocument):
    """
    Tree node update model.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str | None = None
    parent: ObjectId | None = None
