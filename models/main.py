from pydantic import BaseModel
from typing import Dict


class EntityMeta(BaseModel):
    id: str
    entity: str
    properties: Dict = {}
