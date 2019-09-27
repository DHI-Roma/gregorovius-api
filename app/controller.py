from fastapi import FastAPI
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from typing import List
from .model import EntityMeta
from .service import Service, ENTITY_NAMES

app = FastAPI(
    title="Gregorovius Briefedition API",
    version="1.0.0-beta",
)

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

    @app.get(
        f"/{entity_name}", response_model=List[EntityMeta],
        summary=f"Read {entity_name} collection" 
    )
    async def read_collection():
        collection = Service.get_entities(entity_name)
        return collection


    @app.get(
        f"/{entity_name}/{{entity_id}}", 
        responses= {
            200: {
                "description": f"an item from the {entity_name} collection",
                "content": {
                    "application/xml": {},
                    "application/json": {}
                }
            },
        },
        response_model_skip_defaults=True,
        status_code=200,
        summary=f"Read {entity_name} item" 
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
