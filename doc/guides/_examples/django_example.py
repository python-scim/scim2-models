import json
from http import HTTPStatus

from django.http import HttpResponse
from django.urls import path
from django.urls import register_converter
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import PatchOp
from scim2_models import ResourceType
from scim2_models import ResponseParameters
from scim2_models import Schema
from scim2_models import SCIMException
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
def scim_response(payload, status=HTTPStatus.OK):
    """Build a Django response with the SCIM media type.

    Automatically sets the ``ETag`` header from ``meta.version`` when present.
    """
    response = HttpResponse(
        payload,
        status=status,
        content_type="application/scim+json",
    )
    meta = json.loads(payload).get("meta", {})
    if version := meta.get("version"):
        response["ETag"] = version
    return response


def resource_location(request, app_record):
    """Return the canonical URL for a user record."""
    return request.build_absolute_uri(
        reverse("scim_user", kwargs={"app_record": app_record})
    )
# -- setup-end --


# -- etag-start --
def check_etag(record, request):
    """Compare the record's ETag against the ``If-Match`` request header.

    :param record: The application record.
    :param request: The Django request.
    :return: A 412 SCIM error response if the ETag does not match, or :data:`None`.
    """
    if_match = request.META.get("HTTP_IF_MATCH")
    if not if_match:
        return None
    if if_match.strip() == "*":
        return None
    etag = make_etag(record)
    tags = [t.strip() for t in if_match.split(",")]
    if etag not in tags:
        scim_error = Error(status=412, detail="ETag mismatch")
        return scim_response(
            scim_error.model_dump_json(), HTTPStatus.PRECONDITION_FAILED
        )
    return None
# -- etag-end --


# -- refinements-start --
# -- converters-start --
class UserConverter:
    regex = "[^/]+"

    def to_python(self, id):
        try:
            return get_record(id)
        except KeyError:
            raise ValueError

    def to_url(self, record):
        return record["id"]


register_converter(UserConverter, "user")
# -- converters-end --


# -- validation-helper-start --
def scim_validation_error(error):
    """Turn Pydantic validation errors into a SCIM error response."""
    scim_error = Error.from_validation_error(error.errors()[0])
    return scim_response(scim_error.model_dump_json(), scim_error.status)
# -- validation-helper-end --


# -- scim-exception-helper-start --
def scim_exception_error(error):
    """Turn SCIM exceptions into a SCIM error response."""
    scim_error = error.to_error()
    return scim_response(scim_error.model_dump_json(), scim_error.status)
# -- scim-exception-helper-end --


# -- error-handler-start --
def handler404(request, exception):
    """Turn Django 404 errors into SCIM error responses."""
    scim_error = Error(status=404, detail=str(exception))
    return scim_response(scim_error.model_dump_json(), HTTPStatus.NOT_FOUND)
# -- error-handler-end --
# -- refinements-end --


# -- endpoints-start --
# -- single-resource-start --
@method_decorator(csrf_exempt, name="dispatch")
class UserView(View):
    """Handle GET, PUT, PATCH and DELETE on one SCIM user resource."""

    def get(self, request, app_record):
        try:
            req = ResponseParameters.model_validate(request.GET.dict())
        except ValidationError as error:
            return scim_validation_error(error)

        etag = make_etag(app_record)
        if_none_match = request.META.get("HTTP_IF_NONE_MATCH")
        if if_none_match and etag in [t.strip() for t in if_none_match.split(",")]:
            return HttpResponse(status=HTTPStatus.NOT_MODIFIED)

        scim_user = to_scim_user(app_record, resource_location(request, app_record))
        return scim_response(
            scim_user.model_dump_json(
                scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
                attributes=req.attributes,
                excluded_attributes=req.excluded_attributes,
            )
        )

    def delete(self, request, app_record):
        if resp := check_etag(app_record, request):
            return resp
        delete_record(app_record["id"])
        return scim_response("", HTTPStatus.NO_CONTENT)

    def put(self, request, app_record):
        if resp := check_etag(app_record, request):
            return resp
        existing_user = to_scim_user(app_record, resource_location(request, app_record))
        try:
            replacement = User.model_validate(
                json.loads(request.body),
                scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
            )
            replacement.replace(existing_user)
        except ValidationError as error:
            return scim_validation_error(error)
        except SCIMException as error:
            return scim_exception_error(error)

        replacement.id = existing_user.id
        updated_record = from_scim_user(replacement)
        try:
            save_record(updated_record)
        except SCIMException as error:
            return scim_exception_error(error)

        response_user = to_scim_user(
            updated_record, resource_location(request, updated_record)
        )
        return scim_response(
            response_user.model_dump_json(
                scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE
            )
        )

    def patch(self, request, app_record):
        if resp := check_etag(app_record, request):
            return resp
        try:
            patch = PatchOp[User].model_validate(
                json.loads(request.body),
                scim_ctx=Context.RESOURCE_PATCH_REQUEST,
            )
        except ValidationError as error:
            return scim_validation_error(error)

        scim_user = to_scim_user(app_record, resource_location(request, app_record))
        patch.patch(scim_user)

        updated_record = from_scim_user(scim_user)
        try:
            save_record(updated_record)
        except SCIMException as error:
            return scim_exception_error(error)

        return scim_response(
            scim_user.model_dump_json(scim_ctx=Context.RESOURCE_PATCH_RESPONSE)
        )
# -- single-resource-end --


# -- collection-start --
@method_decorator(csrf_exempt, name="dispatch")
class UsersView(View):
    """Handle GET and POST on the SCIM users collection."""

    def get(self, request):
        try:
            req = SearchRequest.model_validate(request.GET.dict())
        except ValidationError as error:
            return scim_validation_error(error)

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
        return scim_response(
            response.model_dump_json(
                scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
                attributes=req.attributes,
                excluded_attributes=req.excluded_attributes,
            )
        )

    def post(self, request):
        try:
            request_user = User.model_validate(
                json.loads(request.body),
                scim_ctx=Context.RESOURCE_CREATION_REQUEST,
            )
        except ValidationError as error:
            return scim_validation_error(error)

        app_record = from_scim_user(request_user)
        try:
            save_record(app_record)
        except SCIMException as error:
            return scim_exception_error(error)

        response_user = to_scim_user(app_record, resource_location(request, app_record))
        return scim_response(
            response_user.model_dump_json(scim_ctx=Context.RESOURCE_CREATION_RESPONSE),
            HTTPStatus.CREATED,
        )


urlpatterns = [
    path("scim/v2/Users", UsersView.as_view(), name="scim_users"),
    path("scim/v2/Users/<user:app_record>", UserView.as_view(), name="scim_user"),
]
# -- collection-end --


# -- discovery-start --
# -- schemas-start --
class SchemasView(View):
    """Handle GET on the SCIM schemas collection."""

    def get(self, request):
        try:
            req = SearchRequest.model_validate(request.GET.dict())
        except ValidationError as error:
            return scim_validation_error(error)

        total, page = get_schemas(req.start_index_0, req.stop_index_0)
        response = ListResponse[Schema](
            total_results=total,
            start_index=req.start_index or 1,
            items_per_page=len(page),
            resources=page,
        )
        return scim_response(
            response.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
        )


class SchemaView(View):
    """Handle GET on a single SCIM schema."""

    def get(self, request, schema_id):
        try:
            schema = get_schema(schema_id)
        except KeyError:
            scim_error = Error(status=404, detail=f"Schema {schema_id!r} not found")
            return scim_response(scim_error.model_dump_json(), HTTPStatus.NOT_FOUND)
        return scim_response(
            schema.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
        )
# -- schemas-end --


# -- resource-types-start --
class ResourceTypesView(View):
    """Handle GET on the SCIM resource types collection."""

    def get(self, request):
        try:
            req = SearchRequest.model_validate(request.GET.dict())
        except ValidationError as error:
            return scim_validation_error(error)

        total, page = get_resource_types(req.start_index_0, req.stop_index_0)
        response = ListResponse[ResourceType](
            total_results=total,
            start_index=req.start_index or 1,
            items_per_page=len(page),
            resources=page,
        )
        return scim_response(
            response.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
        )


class ResourceTypeView(View):
    """Handle GET on a single SCIM resource type."""

    def get(self, request, resource_type_id):
        try:
            rt = get_resource_type(resource_type_id)
        except KeyError:
            scim_error = Error(
                status=404, detail=f"ResourceType {resource_type_id!r} not found"
            )
            return scim_response(scim_error.model_dump_json(), HTTPStatus.NOT_FOUND)
        return scim_response(
            rt.model_dump_json(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
        )
# -- resource-types-end --


# -- service-provider-config-start --
class ServiceProviderConfigView(View):
    """Handle GET on the SCIM service provider configuration."""

    def get(self, request):
        return scim_response(
            service_provider_config.model_dump_json(
                scim_ctx=Context.RESOURCE_QUERY_RESPONSE
            )
        )
# -- service-provider-config-end --


discovery_urlpatterns = [
    path("scim/v2/Schemas", SchemasView.as_view(), name="scim_schemas"),
    path("scim/v2/Schemas/<path:schema_id>", SchemaView.as_view(), name="scim_schema"),
    path(
        "scim/v2/ResourceTypes",
        ResourceTypesView.as_view(),
        name="scim_resource_types",
    ),
    path(
        "scim/v2/ResourceTypes/<resource_type_id>",
        ResourceTypeView.as_view(),
        name="scim_resource_type",
    ),
    path(
        "scim/v2/ServiceProviderConfig",
        ServiceProviderConfigView.as_view(),
        name="scim_service_provider_config",
    ),
]
# -- discovery-end --
# -- endpoints-end --
