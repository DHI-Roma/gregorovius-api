from fastapi import FastAPI
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from typing import List
from .model import EntityMeta
from .service import Service, ENTITY_NAMES

app = FastAPI()
app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
)




class XMLResponse(Response):
    media_type = "application/xml"


def create_endpoints_for(entity_name):

    @app.get(f"/{entity_name}", response_model=List[EntityMeta])
    async def read_collection():
        collection = Service.get_entities(entity_name)
        return collection


    @app.get(
        f"/{entity_name}/{{entity_id}}", 
        responses= {
            200: {
                "description": f"Get an item from {entity_name}",
                "content": {
                    "application/xml": {},
                    "application/json": {}
                }
            }
        }
    )
    async def read_entity(entity_id: str, request: Request):
        if request.headers["accept"] == "application/json":
            entity = Service.get_entity(entity_name, entity_id, format="json")
            if entity:
                return JSONResponse(content=entity)
            else:
                return JSONResponse(status_code=404,content={"message": "Item not found"})
        entity = Service.get_entity(entity_name, entity_id, format="xml")
        if entity:
            return XMLResponse(content=entity)
        else:
            return XMLResponse(
                status_code=404,
                content="<message>Item not found</message>"
            )


for entity in ENTITY_NAMES:
    create_endpoints_for(entity)
