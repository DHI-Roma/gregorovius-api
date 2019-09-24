from pydantic import BaseModel
from typing import List, Dict


class EntityMeta(BaseModel):
    id: str
    db_id: Dict
    entity: str
    properties: Dict = {}
