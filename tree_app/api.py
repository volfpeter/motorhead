from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from motorhead import AgnosticDatabase, DatabaseProvider, DeleteError, DeleteResultModel, ObjectId

from .model import TreeNode, TreeNodeCreate, TreeNodeUpdate
from .service import TreeNodeService


def make_api(
    *,
    get_database: DatabaseProvider,
    prefix: str = "/tree-node",
) -> APIRouter:
    """
    Tree node `APIRouter` factory.

    Arguments:
        get_database: FastAPI dependency that returns the `AgnosticDatabase`
                      database instance for the API.
        prefix: The prefix for the created `APIRouter`.

    Returns:
        The created `APIRouter` instance.
    """
    DependsDatabase = Annotated[AgnosticDatabase, Depends(get_database)]

    def get_service(database: DependsDatabase) -> TreeNodeService:
        return TreeNodeService(database)

    DependsService = Annotated[TreeNodeService, Depends(get_service)]

    api = APIRouter(prefix=prefix)

    @api.get("/", response_model=list[TreeNode])
    async def get_all(service: DependsService) -> list[dict[str, Any]]:
        return [d async for d in service.find()]

    @api.post("/", response_model=TreeNode)
    async def create(data: TreeNodeCreate, service: DependsService) -> dict[str, Any]:
        try:
            result = await service.insert_one(data)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Creation failed.") from e

        if (created := await service.get_by_id(result.inserted_id)) is not None:
            return created

        raise HTTPException(status.HTTP_409_CONFLICT)

    @api.get("/{id}", response_model=TreeNode)
    async def get_by_id(id: ObjectId, service: DependsService) -> dict[str, Any]:
        if (result := await service.get_by_id(id)) is not None:
            return result

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(id))

    @api.put("/{id}", response_model=TreeNode)
    async def update_by_id(id: ObjectId, data: TreeNodeUpdate, service: DependsService) -> dict[str, Any]:
        try:
            result = await service.update_by_id(id, data)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(id)) from e

        if result.matched_count == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(id))

        if (updated := await service.get_by_id(id)) is not None:
            return updated

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(id))

    @api.delete("/{id}", response_model=DeleteResultModel)
    async def delete_by_id(id: ObjectId, service: DependsService) -> DeleteResultModel:
        try:
            result = await service.delete_by_id(id)
        except DeleteError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(id)) from e
        if result.deleted_count == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(id))

        return DeleteResultModel(delete_count=result.deleted_count)

    return api
