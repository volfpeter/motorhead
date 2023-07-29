from pydantic import BaseModel


class DeleteResultModel(BaseModel):
    """
    Delete result model.
    """

    delete_count: int
