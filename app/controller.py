from typing import List

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from snakesist.exist_client import ExistClient
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware

from service import Service
from models import EntityMeta
from .config import CFG, ROOT_COLLECTION, XSLT_FLAG, ENTITY_NAMES


db = ExistClient(host="db")
db.root_collection = ROOT_COLLECTION
service = Service(db, CFG, watch_updates=True)

app = FastAPI()


class XMLResponse(Response):
    media_type = "application/xml"


def create_endpoints_for(entity_name):
    """
    Generate index and detail endpoints for a specified entity
    :param entity_name: Name of the entity as configured in the manifest
    """

    @app.get(f"/{entity_name}", response_model=List[EntityMeta])
    async def read_collection():
        """
        Retrieve all entities of a specific type
        """
        collection = service.get_entities(entity_name)
        return collection

    @app.get(
        f"/{entity_name}/{{entity_id}}",
        responses={
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
        """
        Retrieve an entity by its ID
        """
        if request.headers["accept"] == "application/json":
            retrieved_entity = service.get_entity(entity_name, entity_id, output_format="json")
            if retrieved_entity:
                return JSONResponse(content=retrieved_entity)
            else:
                return JSONResponse(status_code=404, content={"message": "Item not found"})
        retrieved_entity = service.get_entity(entity_name, entity_id, output_format="xml")
        if entity:
            return XMLResponse(content=retrieved_entity)
        else:
            return XMLResponse(
                status_code=404,
                content="<message>Item not found</message>"
            )
    
    if XSLT_FLAG:
        @app.post(
            f"/{entity_name}/{{entity_id}}", 
            responses={
                200: {
                    "description": f"Transform an item from {entity_name} via XSL.",
                    "content": {
                        "application/html": {},
                    }
                }
            }
        )
        async def transform_entity(entity_id: str, request: Request, xslt: bool = False):
            """
            Perform XSL transformation on an XML entity endpoint
            """
            if xslt:
                stylesheet = await request.body()
                return service.xslt_transform_entity(entity_name, entity_id, stylesheet)
            else:
                return XMLResponse(
                    status_code=400,
                    content="<message>Bad request</message>"
                )


for entity in ENTITY_NAMES:
    create_endpoints_for(entity)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Gregorovius Correspondence Edition API",
        version="1.0.0",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

