from http import HTTPStatus

from fastapi import APIRouter
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from pydantic import ValidationError

from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import PatchOp
from scim2_models import ResourceType
from scim2_models import ResponseParameters
from scim2_models import SCIMException
from scim2_models import Schema
from scim2_models import SearchRequest
from scim2_models import User

from .integrations import PreconditionFailed
from .integrations import check_etag
from .integrations import delete_record
from .integrations import from_scim_user
from .integrations import get_record
from .integrations import get_resource_type
from .integrations import get_resource_types
from .integrations import get_schema
from .integrations import get_schemas
from .integrations import list_records
from .integrations import make_etag
from .integrations import save_record
from .integrations import service_provider_config
from .integrations import to_scim_user

# -- setup-start --
app = FastAPI()
router = APIRouter(prefix="/scim/v2")


@app.middleware("http")
async def add_scim_content_type(request: Request, call_next):
    """Set the SCIM media type on every response."""
    response = await call_next(request)
    response.headers["Content-Type"] = "application/scim+json"
    return response


def resource_location(request, app_record):
    """Return the canonical URL for a user record."""
    return str(request.url_for("get_user", user_id=app_record["id"]))
# -- setup-end --


# -- refinements-start --
# -- dependency-start --
def resolve_user(user_id: str):
    """Resolve a user identifier to an application record."""
    try:
        return get_record(user_id)
    except KeyError:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
# -- dependency-end --


# -- error-handlers-start --
@app.exception_handler(ValidationError)
async def handle_validation_error(request, error):
    """Turn Pydantic validation errors into SCIM error responses."""
    scim_error = Error.from_validation_error(error.errors()[0])
    return Response(scim_error.model_dump_json(), status_code=scim_error.status)


@app.exception_handler(HTTPException)
async def handle_http_exception(request, error):
    """Turn HTTP exceptions into SCIM error responses."""
    scim_error = Error(status=error.status_code, detail=error.detail or "")
    return Response(scim_error.model_dump_json(), status_code=error.status_code)


@app.exception_handler(SCIMException)
async def handle_scim_error(request, error):
    """Turn SCIM exceptions into SCIM error responses."""
    scim_error = error.to_error()
    return Response(scim_error.model_dump_json(), status_code=scim_error.status)


@app.exception_handler(PreconditionFailed)
async def handle_precondition_failed(request, error):
    """Turn ETag mismatches into SCIM 412 responses."""
    scim_error = Error(status=412, detail="ETag mismatch")
    return Response(
        scim_error.model_dump_json(), status_code=HTTPStatus.PRECONDITION_FAILED
    )
# -- error-handlers-end --
# -- refinements-end --


# -- endpoints-start --
# -- single-resource-start --
# -- get-user-start --
@router.get("/Users/{user_id}")
async def get_user(request: Request, app_record: dict = Depends(resolve_user)):
    """Return one SCIM user."""
    req = ResponseParameters.model_validate(dict(request.query_params))
    scim_user = to_scim_user(app_record, resource_location(request, app_record))
    etag = make_etag(app_record)
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and etag in [t.strip() for t in if_none_match.split(",")]:
        return Response(status_code=HTTPStatus.NOT_MODIFIED)
    return Response(
        scim_user.model_dump_json(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
        headers={"ETag": etag},
    )
# -- get-user-end --


# -- patch-user-start --
@router.patch("/Users/{user_id}")
async def patch_user(request: Request, app_record: dict = Depends(resolve_user)):
    """Apply a SCIM PatchOp to an existing user."""
    check_etag(app_record, request.headers.get("If-Match"))
    scim_user = to_scim_user(app_record, resource_location(request, app_record))
    patch = PatchOp[User].model_validate(
        await request.json(),
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    patch.patch(scim_user)

    updated_record = from_scim_user(scim_user)
    save_record(updated_record)

    return Response(
        scim_user.model_dump_json(scim_ctx=Context.RESOURCE_PATCH_RESPONSE),
        headers={"ETag": make_etag(updated_record)},
    )
# -- patch-user-end --


# -- put-user-start --
@router.put("/Users/{user_id}")
async def replace_user(request: Request, app_record: dict = Depends(resolve_user)):
    """Replace an existing user with a full SCIM resource."""
    check_etag(app_record, request.headers.get("If-Match"))
    existing_user = to_scim_user(app_record, resource_location(request, app_record))
    replacement = User.model_validate(
        await request.json(),
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
    )
    replacement.replace(existing_user)

    replacement.id = existing_user.id
    updated_record = from_scim_user(replacement)
    save_record(updated_record)

    response_user = to_scim_user(
        updated_record, resource_location(request, updated_record)
    )
    return Response(
        response_user.model_dump_json(
            scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE
        ),
        headers={"ETag": make_etag(updated_record)},
    )
# -- put-user-end --


# -- delete-user-start --
@router.delete("/Users/{user_id}")
async def delete_user(request: Request, app_record: dict = Depends(resolve_user)):
    """Delete an existing user."""
    check_etag(app_record, request.headers.get("If-Match"))
    delete_record(app_record["id"])
    return Response(status_code=HTTPStatus.NO_CONTENT)
# -- delete-user-end --
# -- single-resource-end --


# -- collection-start --
# -- list-users-start --
@router.get("/Users")
async def list_users(request: Request):
    """Return one page of users as a SCIM ListResponse."""
    req = SearchRequest.model_validate(dict(request.query_params))
    total, page = list_records(req.start_index_0, req.stop_index_0)
    resources = [
        to_scim_user(record, resource_location(request, record)) for record in page
    ]
    response = ListResponse[User](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(resources),
        resources=resources,
    )
    return Response(
        response.model_dump_json(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
    )
# -- list-users-end --


# -- create-user-start --
@router.post("/Users")
async def create_user(request: Request):
    """Validate a SCIM creation payload and store the new user."""
    request_user = User.model_validate(
        await request.json(),
        scim_ctx=Context.RESOURCE_CREATION_REQUEST,
    )
    app_record = from_scim_user(request_user)
    save_record(app_record)

    response_user = to_scim_user(app_record, resource_location(request, app_record))
    return Response(
        response_user.model_dump_json(scim_ctx=Context.RESOURCE_CREATION_RESPONSE),
        status_code=HTTPStatus.CREATED,
        headers={"ETag": make_etag(app_record)},
    )
# -- create-user-end --
# -- collection-end --


# -- discovery-start --
# -- schemas-start --
@router.get("/Schemas")
async def list_schemas(request: Request):
    """Return one page of SCIM schemas the server exposes."""
    req = SearchRequest.model_validate(dict(request.query_params))
    total, page = get_schemas(req.start_index_0, req.stop_index_0)
    response = ListResponse[Schema](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(page),
        resources=page,
    )
    return Response(
        response.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
    )


@router.get("/Schemas/{schema_id:path}")
async def get_schema_by_id(schema_id: str):
    """Return one SCIM schema by its URI identifier."""
    try:
        schema = get_schema(schema_id)
    except KeyError:
        scim_error = Error(status=404, detail=f"Schema {schema_id!r} not found")
        return Response(scim_error.model_dump_json(), status_code=HTTPStatus.NOT_FOUND)
    return Response(
        schema.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
    )
# -- schemas-end --


# -- resource-types-start --
@router.get("/ResourceTypes")
async def list_resource_types(request: Request):
    """Return one page of SCIM resource types the server exposes."""
    req = SearchRequest.model_validate(dict(request.query_params))
    total, page = get_resource_types(req.start_index_0, req.stop_index_0)
    response = ListResponse[ResourceType](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(page),
        resources=page,
    )
    return Response(
        response.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
    )


@router.get("/ResourceTypes/{resource_type_id}")
async def get_resource_type_by_id(resource_type_id: str):
    """Return one SCIM resource type by its identifier."""
    try:
        rt = get_resource_type(resource_type_id)
    except KeyError:
        scim_error = Error(
            status=404, detail=f"ResourceType {resource_type_id!r} not found"
        )
        return Response(scim_error.model_dump_json(), status_code=HTTPStatus.NOT_FOUND)
    return Response(
        rt.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
    )
# -- resource-types-end --


# -- service-provider-config-start --
@router.get("/ServiceProviderConfig")
async def get_service_provider_config():
    """Return the SCIM service provider configuration."""
    return Response(
        service_provider_config.model_dump_json(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        ),
    )
# -- service-provider-config-end --
# -- discovery-end --

app.include_router(router)
# -- endpoints-end --
