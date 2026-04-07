from http import HTTPStatus
from typing import Annotated
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from scim2_models import Context
from scim2_models import CreationRequestContext
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import PatchOp
from scim2_models import PatchRequestContext
from scim2_models import QueryResponseContext
from scim2_models import ReplacementRequestContext
from scim2_models import ResourceType
from scim2_models import ResponseParameters
from scim2_models import Schema
from scim2_models import SCIMException
from scim2_models import ServiceProviderConfig
from scim2_models import SearchRequest
from scim2_models import User

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


class SCIMResponse(JSONResponse):
    """SCIM JSON response that auto-extracts the ``ETag`` from ``meta.version``."""

    media_type = "application/scim+json"

    def __init__(self, content: Any = None, **kwargs: Any) -> None:
        super().__init__(content, **kwargs)
        if meta := (content or {}).get("meta", {}):
            if version := meta.get("version"):
                self.headers["ETag"] = version


router = APIRouter(prefix="/scim/v2", default_response_class=SCIMResponse)


def resource_location(request, app_record):
    """Return the canonical URL for a user record."""
    return str(request.url_for("get_user", user_id=app_record["id"]))
# -- setup-end --


# -- etag-start --
def check_etag(record, request: Request):
    """Compare the record's ETag against the ``If-Match`` request header.

    :param record: The application record.
    :param request: The incoming request.
    :raises ~fastapi.HTTPException: If the header is present and does not match.
    """
    if_match = request.headers.get("If-Match")
    if not if_match:
        return
    if if_match.strip() == "*":
        return
    etag = make_etag(record)
    tags = [t.strip() for t in if_match.split(",")]
    if etag not in tags:
        raise HTTPException(status_code=412, detail="ETag mismatch")
# -- etag-end --


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
    return SCIMResponse(scim_error.model_dump(), status_code=scim_error.status)


@app.exception_handler(HTTPException)
async def handle_http_exception(request, error):
    """Turn HTTP exceptions into SCIM error responses."""
    scim_error = Error(status=error.status_code, detail=error.detail or "")
    return SCIMResponse(scim_error.model_dump(), status_code=error.status_code)


@app.exception_handler(SCIMException)
async def handle_scim_error(request, error):
    """Turn SCIM exceptions into SCIM error responses."""
    scim_error = error.to_error()
    return SCIMResponse(scim_error.model_dump(), status_code=scim_error.status)
# -- error-handlers-end --
# -- refinements-end --


# -- endpoints-start --
# -- single-resource-start --
# -- get-user-start --
@router.get("/Users/{user_id}")
async def get_user(
    request: Request,
    req: Annotated[ResponseParameters, Query()],
    app_record: dict = Depends(resolve_user),
):
    """Return one SCIM user."""
    scim_user = to_scim_user(app_record, resource_location(request, app_record))
    etag = make_etag(app_record)
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and etag in [t.strip() for t in if_none_match.split(",")]:
        return Response(status_code=HTTPStatus.NOT_MODIFIED)
    return SCIMResponse(
        scim_user.model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
    )
# -- get-user-end --


# -- patch-user-start --
@router.patch("/Users/{user_id}")
async def patch_user(
    request: Request,
    patch: PatchRequestContext[PatchOp[User]],
    req: Annotated[ResponseParameters, Query()],
    app_record: dict = Depends(resolve_user),
):
    """Apply a SCIM PatchOp to an existing user."""
    check_etag(app_record, request)
    scim_user = to_scim_user(app_record, resource_location(request, app_record))
    patch.patch(scim_user)

    updated_record = from_scim_user(scim_user)
    save_record(updated_record)

    response_user = to_scim_user(updated_record, resource_location(request, updated_record))
    return SCIMResponse(
        response_user.model_dump(
            scim_ctx=Context.RESOURCE_PATCH_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
    )
# -- patch-user-end --


# -- put-user-start --
@router.put("/Users/{user_id}")
async def replace_user(
    request: Request,
    replacement: ReplacementRequestContext[User],
    req: Annotated[ResponseParameters, Query()],
    app_record: dict = Depends(resolve_user),
):
    """Replace an existing user with a full SCIM resource."""
    check_etag(app_record, request)
    existing_user = to_scim_user(app_record, resource_location(request, app_record))
    replacement.replace(existing_user)

    updated_record = from_scim_user(replacement)
    save_record(updated_record)

    response_user = to_scim_user(updated_record, resource_location(request, updated_record))
    return SCIMResponse(
        response_user.model_dump(
            scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
    )
# -- put-user-end --


# -- delete-user-start --
@router.delete("/Users/{user_id}")
async def delete_user(request: Request, app_record: dict = Depends(resolve_user)):
    """Delete an existing user."""
    check_etag(app_record, request)
    delete_record(app_record["id"])
    return Response(status_code=HTTPStatus.NO_CONTENT)
# -- delete-user-end --
# -- single-resource-end --


# -- collection-start --
# -- list-users-start --
@router.get("/Users")
async def list_users(
    request: Request, req: Annotated[SearchRequest, Query()]
):
    """Return one page of users as a SCIM ListResponse."""
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
    return SCIMResponse(
        response.model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
    )
# -- list-users-end --


# -- create-user-start --
@router.post("/Users", status_code=HTTPStatus.CREATED)
async def create_user(
    request: Request,
    request_user: CreationRequestContext[User],
    req: Annotated[ResponseParameters, Query()],
):
    """Validate a SCIM creation payload and store the new user."""
    app_record = from_scim_user(request_user)
    save_record(app_record)

    response_user = to_scim_user(app_record, resource_location(request, app_record))
    return SCIMResponse(
        response_user.model_dump(
            scim_ctx=Context.RESOURCE_CREATION_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
        status_code=HTTPStatus.CREATED,
    )
# -- create-user-end --
# -- collection-end --


# -- discovery-start --
# -- schemas-start --
@router.get("/Schemas")
async def list_schemas(req: Annotated[SearchRequest, Query()]):
    """Return one page of SCIM schemas the server exposes."""
    total, page = get_schemas(req.start_index_0, req.stop_index_0)
    response = ListResponse[Schema](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(page),
        resources=page,
    )
    return SCIMResponse(
        response.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
    )


@router.get("/Schemas/{schema_id:path}")
async def get_schema_by_id(schema_id: str):
    """Return one SCIM schema by its URI identifier."""
    try:
        schema = get_schema(schema_id)
    except KeyError:
        scim_error = Error(status=404, detail=f"Schema {schema_id!r} not found")
        return SCIMResponse(scim_error.model_dump(), status_code=HTTPStatus.NOT_FOUND)
    return SCIMResponse(
        schema.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
    )
# -- schemas-end --


# -- resource-types-start --
@router.get("/ResourceTypes")
async def list_resource_types(req: Annotated[SearchRequest, Query()]):
    """Return one page of SCIM resource types the server exposes."""
    total, page = get_resource_types(req.start_index_0, req.stop_index_0)
    response = ListResponse[ResourceType](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(page),
        resources=page,
    )
    return SCIMResponse(
        response.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
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
        return SCIMResponse(scim_error.model_dump(), status_code=HTTPStatus.NOT_FOUND)
    return SCIMResponse(
        rt.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
    )
# -- resource-types-end --


# -- service-provider-config-start --
@router.get("/ServiceProviderConfig")
async def get_service_provider_config() -> QueryResponseContext[
    ServiceProviderConfig
]:
    """Return the SCIM service provider configuration."""
    return service_provider_config
# -- service-provider-config-end --
# -- discovery-end --

app.include_router(router)
# -- endpoints-end --
