from typing import List

import requests
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from snakesist.exist_client import ExistClient
from starlette.responses import Response, JSONResponse, PlainTextResponse, FileResponse, StreamingResponse
from starlette.requests import Request
from random import choice
from string import ascii_letters
from pathlib import Path
from multiprocessing import Manager
from diskcache import Cache

from service import Service, beacon_service, image_service, letter_index_service
from models import EntityMeta
from .config import CFG, ROOT_COLLECTION, XSLT_FLAG, ENTITY_NAMES, STAGE

from starlette.middleware.cors import CORSMiddleware
from PIL import Image
from io import BytesIO

origins = [
    "http://localhost:8080",
    "http://localhost:8081",
]


# db = ExistClient(host="db")
db = ExistClient(host="localhost")
db.root_collection = ROOT_COLLECTION
service = Service(db, CFG, watch_updates=True)

cache = Cache()

app = FastAPI()
meta = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class XMLResponse(Response):
    media_type = "application/xml"

@app.on_event('startup')
async def on_startup():
    try:
        db_version_file = Path(__file__).parent / "../.db-version"
        with db_version_file.open('r') as version:
            db_version_hash = version.read().strip("\n")
    except FileNotFoundError:
        db_version_hash = ''.join(choice(ascii_letters) for i in range(12))

    meta['version'] = db_version_hash


@app.get(
    "/cmif",
    responses={
        200: {
            "content": {"application/xml": {}},
            "description": "Get correspondence metadata in CMI format",
        }
    },
)
async def cmif_api():
    """
    Get correspondence metadata in CMI format
    """
    return XMLResponse(
        content=str(db.retrieve_resources("//*:TEI[@type='cmif']").pop())
    )


@app.get(
    "/search",
    responses={
        200: {
            "description": "Get full text search results",
        }
    },
)
async def search(q, entity, width=50):
    """
    Get full text search results
    """
    return service.get_search_results(keyword=q, entity=entity, width=width)


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
        cache_key = f"/{entity_name}"
        if cache_key not in cache:
            cache[cache_key] = service.get_entities(entity_name)

        collection = cache[cache_key]
        return collection

    @app.get(
        f"/{entity_name}/{{entity_id}}",
        responses={
            200: {
                "description": f"Get an item from {entity_name}",
                "content": {"application/xml": {}, "application/json": {}},
            }
        },
    )
    async def read_entity(entity_id: str, request: Request):
        """
        Retrieve an entity by its ID
        """
        if request.headers["accept"] == "application/json":
            cache_key = f"{entity_name}_{entity_id}_json"
            if cache_key not in cache:
                cache[cache_key] = service.get_entity(
                    entity_name, entity_id, output_format="json"
                )
            retrieved_entity = cache[cache_key]
            if retrieved_entity:
                return JSONResponse(content=retrieved_entity)
            else:
                return JSONResponse(
                    status_code=404, content={"message": "Item not found"}
                )

        cache_key = f"{entity_name}_{entity_id}_xml"
        if cache_key not in cache:
            cache[cache_key] = service.get_entity(
                entity_name, entity_id, output_format="xml"
            )
        retrieved_entity = cache[cache_key]
        if retrieved_entity:
            return XMLResponse(content=retrieved_entity)
        else:
            return XMLResponse(
                status_code=404, content="<message>Item not found</message>"
            )

    if XSLT_FLAG:

        @app.post(
            f"/{entity_name}/{{entity_id}}",
            responses={
                200: {
                    "description": f"Transform an item from {entity_name} via XSL.",
                    "content": {"application/html": {}},
                }
            },
        )
        async def transform_entity(
            entity_id: str, request: Request, xslt: bool = False
        ):
            """
            Perform XSL transformation on an XML entity endpoint
            """
            if xslt:
                stylesheet = await request.body()
                return service.xslt_transform_entity(entity_name, entity_id, stylesheet)
            else:
                return XMLResponse(
                    status_code=400, content="<message>Bad request</message>"
                )


for entity in ENTITY_NAMES:
    create_endpoints_for(entity)

@app.get(f"/facsimiles/")
def get_facsimiles() -> JSONResponse:
    cache_key = f"/facsimiles"
    if cache_key not in cache:
        cache[cache_key] = image_service.generate_image_map()
    return JSONResponse(cache[cache_key])

@app.get(f"/facsimiles/{{letter_id}}/")
def get_facsimile_for_letter(letter_id: str)  -> Response:
    cache_key = f"/facsimiles"
    if cache_key not in cache:
        cache[cache_key] = image_service.generate_image_map()

    facsimiles = cache[cache_key]
    if letter_id not in facsimiles:
        return PlainTextResponse(f"No facsimiles found for letter {letter_id}", 400)

    return JSONResponse(facsimiles[letter_id])

@app.get(f"/facsimiles/{{letter_id}}/{{page}}/{{rotation}}")
async def get_facsimile_image(letter_id: str, page: int, rotation: int) -> Response:
    cache_key = f"/facsimiles"
    if cache_key not in cache:
        cache[cache_key] = image_service.generate_image_map()

    facsimiles = cache[cache_key]
    if letter_id not in facsimiles:
        return PlainTextResponse(f"No facsimiles found for letter {letter_id}", 400)

    if page not in facsimiles[letter_id]:
        return PlainTextResponse(f"No facsimile with {page} found for letter {letter_id}", 400)

    img = Image.open(f"./img/webp/{facsimiles[letter_id][page]['name']}", mode="r")
    img = img.rotate(rotation, expand=True)

    rotated_image = BytesIO()
    img.save(rotated_image, "WEBP")
    rotated_image.seek(0)

    return StreamingResponse(rotated_image, media_type="image/webp")

@app.get(f"/beacon/all")
def get_beacon() -> PlainTextResponse:
    """
    Generate BEACON file for all persons and organizations identified with a GND number
    """
    collection = service.get_entities('persons')
    gnds = beacon_service.get_gnd_ids(collection)
    header = beacon_service.make_beacon_header()
    beacon = header + "\n".join(gnds)
    return PlainTextResponse(beacon)

@app.get(f"/beacon/persons")
def get_beacon_person() -> PlainTextResponse:
    """
    Generate BEACON file for all persons identified with a GND number, without organizations
    """
    collection = service.get_entities('persons')
    gnds = beacon_service.get_gnd_ids(collection, beacon_service.FILTER_PERSON)
    header = beacon_service.make_beacon_header(beacon_service.FILTER_PERSON)
    beacon = header + "\n".join(gnds)
    return PlainTextResponse(beacon)

@app.get(f"/beacon/organizations")
def get_beacon_person() -> PlainTextResponse:
    """
    Generate BEACON file for all organizations identified with a GND number, without actual persons
    """
    collection = service.get_entities('persons')
    gnds = beacon_service.get_gnd_ids(collection, beacon_service.FILTER_ORGANIZATION)
    header = beacon_service.make_beacon_header(beacon_service.FILTER_ORGANIZATION)
    beacon = header + "\n".join(gnds)
    return PlainTextResponse(beacon)

@app.get(f"/beacon/seeAlso/{{gnd}}")
async def get_beacon_see_also(gnd: str):
    """
    Get references in other data sources for a given GND number
    """
    headers =  {'Content-Type': 'application/json'}
    url = 'https://beacon.findbuch.de/seealso/pnd-aks?format=seealso&id=' + gnd
    findbuch_response = requests.get(url, headers=headers)
    findbuch_response.encoding = 'UTF-8'

    transformed_data = beacon_service.map_seealso_data(findbuch_response.json())
    return JSONResponse(transformed_data)

@app.get(f"/full-letter-index/")
async def get_full_letter_index():
    return letter_index_service.parse_gesamtdatenbank()

@app.get(f"/version/")
def get_version_hash() -> JSONResponse:
    response = {"version": meta['version']}
    return JSONResponse(response)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Gregorovius Correspondence Edition API",
        version="1.4.0",
        routes=app.routes,
    )

    if STAGE == "prod":
        openapi_schema["servers"] = [
            { "url" : "/api" }
        ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
