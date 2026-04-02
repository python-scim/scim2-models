from http import HTTPStatus

from flask import Blueprint
from flask import make_response
from flask import request
from pydantic import ValidationError
from werkzeug.routing import BaseConverter
from werkzeug.routing import ValidationError as RoutingValidationError

from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import PatchOp
from scim2_models import ResourceType
from scim2_models import ResponseParameters
from scim2_models import Schema
from scim2_models import SearchRequest
from scim2_models import UniquenessException
from scim2_models import User

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
from .integrations import PreconditionFailed
from .integrations import save_record
from .integrations import service_provider_config
from .integrations import to_scim_user

# -- setup-start --
bp = Blueprint("scim", __name__, url_prefix="/scim/v2")


@bp.after_request
def add_scim_content_type(response):
    """Expose every endpoint with the SCIM media type."""
    response.headers["Content-Type"] = "application/scim+json"
    return response
# -- setup-end --


# -- refinements-start --
# -- converters-start --
class UserConverter(BaseConverter):
    """Resolve a user identifier to an application record."""

    def to_python(self, id):
        try:
            return get_record(id)
        except KeyError:
            raise RoutingValidationError()

    def to_url(self, record):
        return record["id"]


@bp.record_once
def _register_converter(state):
    state.app.url_map.converters["user"] = UserConverter
# -- converters-end --


# -- error-handlers-start --
@bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Turn Pydantic validation errors into SCIM error responses."""
    scim_error = Error.from_validation_error(error.errors()[0])
    return scim_error.model_dump_json(), scim_error.status


@bp.errorhandler(404)
def handle_not_found(error):
    """Turn Flask 404 errors into SCIM error responses."""
    scim_error = Error(status=404, detail=str(error.description))
    return scim_error.model_dump_json(), HTTPStatus.NOT_FOUND


@bp.errorhandler(ValueError)
def handle_value_error(error):
    """Turn uniqueness errors into SCIM 409 responses."""
    scim_error = UniquenessException(detail=str(error)).to_error()
    return scim_error.model_dump_json(), HTTPStatus.CONFLICT


@bp.errorhandler(PreconditionFailed)
def handle_precondition_failed(error):
    """Turn ETag mismatches into SCIM 412 responses."""
    scim_error = Error(status=412, detail="ETag mismatch")
    return scim_error.model_dump_json(), HTTPStatus.PRECONDITION_FAILED
# -- error-handlers-end --
# -- refinements-end --


# -- endpoints-start --
# -- single-resource-start --
# -- get-user-start --
@bp.get("/Users/<user:app_record>")
def get_user(app_record):
    """Return one SCIM user."""
    req = ResponseParameters.model_validate(request.args.to_dict())
    scim_user = to_scim_user(app_record)
    resp = make_response(
        scim_user.model_dump_json(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        )
    )
    resp.headers["ETag"] = make_etag(app_record)
    resp.make_conditional(request)
    return resp
# -- get-user-end --


# -- patch-user-start --
@bp.patch("/Users/<user:app_record>")
def patch_user(app_record):
    """Apply a SCIM PatchOp to an existing user."""
    check_etag(app_record, request.headers.get("If-Match"))
    scim_user = to_scim_user(app_record)
    patch = PatchOp[User].model_validate(
        request.get_json(),
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    patch.patch(scim_user)

    updated_record = from_scim_user(scim_user)
    save_record(updated_record)

    return (
        scim_user.model_dump_json(scim_ctx=Context.RESOURCE_PATCH_RESPONSE),
        HTTPStatus.OK,
        {"ETag": make_etag(updated_record)},
    )
# -- patch-user-end --


# -- put-user-start --
@bp.put("/Users/<user:app_record>")
def replace_user(app_record):
    """Replace an existing user with a full SCIM resource."""
    check_etag(app_record, request.headers.get("If-Match"))
    existing_user = to_scim_user(app_record)
    replacement = User.model_validate(
        request.get_json(),
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
        original=existing_user,
    )

    replacement.id = existing_user.id
    updated_record = from_scim_user(replacement)
    save_record(updated_record)

    response_user = to_scim_user(updated_record)
    return (
        response_user.model_dump_json(
            scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE
        ),
        HTTPStatus.OK,
        {"ETag": make_etag(updated_record)},
    )
# -- put-user-end --


# -- delete-user-start --
@bp.delete("/Users/<user:app_record>")
def delete_user(app_record):
    """Delete an existing user."""
    check_etag(app_record, request.headers.get("If-Match"))
    delete_record(app_record["id"])
    return "", HTTPStatus.NO_CONTENT
# -- delete-user-end --
# -- single-resource-end --


# -- collection-start --
# -- list-users-start --
@bp.get("/Users")
def list_users():
    """Return one page of users as a SCIM ListResponse."""
    req = SearchRequest.model_validate(request.args.to_dict())
    total, page = list_records(req.start_index_0, req.stop_index_0)
    resources = [to_scim_user(record) for record in page]
    response = ListResponse[User](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(resources),
        resources=resources,
    )
    return (
        response.model_dump_json(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
        HTTPStatus.OK,
    )
# -- list-users-end --


# -- create-user-start --
@bp.post("/Users")
def create_user():
    """Validate a SCIM creation payload and store the new user."""
    request_user = User.model_validate(
        request.get_json(),
        scim_ctx=Context.RESOURCE_CREATION_REQUEST,
    )
    app_record = from_scim_user(request_user)
    save_record(app_record)

    response_user = to_scim_user(app_record)
    return (
        response_user.model_dump_json(scim_ctx=Context.RESOURCE_CREATION_RESPONSE),
        HTTPStatus.CREATED,
        {"ETag": make_etag(app_record)},
    )
# -- create-user-end --
# -- collection-end --


# -- discovery-start --
# -- schemas-start --
@bp.get("/Schemas")
def list_schemas():
    """Return one page of SCIM schemas the server exposes."""
    req = SearchRequest.model_validate(request.args.to_dict())
    total, page = get_schemas(req.start_index_0, req.stop_index_0)
    response = ListResponse[Schema](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(page),
        resources=page,
    )
    return (
        response.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        HTTPStatus.OK,
    )


@bp.get("/Schemas/<path:schema_id>")
def get_schema_by_id(schema_id):
    """Return one SCIM schema by its URI identifier."""
    try:
        schema = get_schema(schema_id)
    except KeyError:
        scim_error = Error(status=404, detail=f"Schema {schema_id!r} not found")
        return scim_error.model_dump_json(), HTTPStatus.NOT_FOUND
    return (
        schema.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        HTTPStatus.OK,
    )
# -- schemas-end --


# -- resource-types-start --
@bp.get("/ResourceTypes")
def list_resource_types():
    """Return one page of SCIM resource types the server exposes."""
    req = SearchRequest.model_validate(request.args.to_dict())
    total, page = get_resource_types(req.start_index_0, req.stop_index_0)
    response = ListResponse[ResourceType](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(page),
        resources=page,
    )
    return (
        response.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        HTTPStatus.OK,
    )


@bp.get("/ResourceTypes/<resource_type_id>")
def get_resource_type_by_id(resource_type_id):
    """Return one SCIM resource type by its identifier."""
    try:
        rt = get_resource_type(resource_type_id)
    except KeyError:
        scim_error = Error(
            status=404, detail=f"ResourceType {resource_type_id!r} not found"
        )
        return scim_error.model_dump_json(), HTTPStatus.NOT_FOUND
    return (
        rt.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE),
        HTTPStatus.OK,
    )
# -- resource-types-end --


# -- service-provider-config-start --
@bp.get("/ServiceProviderConfig")
def get_service_provider_config():
    """Return the SCIM service provider configuration."""
    return (
        service_provider_config.model_dump_json(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        ),
        HTTPStatus.OK,
    )
# -- service-provider-config-end --
# -- discovery-end --
# -- endpoints-end --
