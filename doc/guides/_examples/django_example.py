from http import HTTPStatus

from django.http import HttpResponse
from django.http import JsonResponse
from django.urls import path
from django.urls import register_converter
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import parse_etags
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import Group
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
from .integrations import list_group_records
from .integrations import page_of
from .integrations import make_etag
from .integrations import save_record
from .integrations import service_provider_config
from .integrations import to_scim_user
from .integrations import to_scim_group


# -- setup-start --
class SCIMJsonResponse(JsonResponse):
    """JSON response with the ``application/scim+json`` media type.

    Keeps a reference to the original data dict in :attr:`scim_data` so that
    ``dispatch()`` can inspect it without re-parsing the serialised body.
    """

    def __init__(self, data, **kwargs):
        self.scim_data = data
        kwargs.setdefault("content_type", "application/scim+json")
        super().__init__(data, **kwargs)


@method_decorator(csrf_exempt, name="dispatch")
class SCIMView(View):
    """Base view for SCIM endpoints.

    Extracts the ``ETag`` header from ``meta.version``, handles
    ``If-None-Match`` (304) on GET, and checks ``If-Match`` (412) on
    write operations.
    """

    # -- etag-start --
    def dispatch(self, request, *args, **kwargs):
        """Dispatch with ETag handling."""
        if request.method in ("PUT", "PATCH", "DELETE"):
            app_record = kwargs.get("app_record")
            if app_record is not None:
                if_match = request.META.get("HTTP_IF_MATCH")
                if if_match and if_match.strip() != "*":
                    etag = make_etag(app_record)
                    if etag not in parse_etags(if_match):
                        scim_error = Error(status=412, detail="ETag mismatch")
                        return SCIMJsonResponse(
                            scim_error.model_dump(), status=412
                        )

        response = super().dispatch(request, *args, **kwargs)

        data = getattr(response, "scim_data", None)
        if data is None:
            return response

        if meta := data.get("meta"):
            if version := meta.get("version"):
                response["ETag"] = version

        if request.method == "GET" and (etag := response.get("ETag")):
            if_none_match = request.META.get("HTTP_IF_NONE_MATCH")
            if if_none_match and etag in parse_etags(if_none_match):
                return HttpResponse(status=HTTPStatus.NOT_MODIFIED)

        return response
    # -- etag-end --


def resource_location(request, app_record):
    """Return the canonical URL for a user record."""
    return request.build_absolute_uri(
        reverse("scim_user", kwargs={"app_record": app_record})
    )
# -- setup-end --


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
    return SCIMJsonResponse(scim_error.model_dump(), status=scim_error.status)
# -- validation-helper-end --


# -- scim-exception-helper-start --
def scim_exception_error(error):
    """Turn SCIM exceptions into a SCIM error response."""
    scim_error = error.to_error()
    return SCIMJsonResponse(scim_error.model_dump(), status=scim_error.status)
# -- scim-exception-helper-end --


# -- error-handler-start --
def handler404(request, exception):
    """Turn Django 404 errors into SCIM error responses."""
    scim_error = Error(status=404, detail=str(exception))
    return SCIMJsonResponse(
        scim_error.model_dump(),
        status=HTTPStatus.NOT_FOUND,
    )
# -- error-handler-end --
# -- refinements-end --


# -- endpoints-start --
# -- single-resource-start --
class UserView(SCIMView):
    """Handle GET, PUT, PATCH and DELETE on one SCIM user resource."""

    def get(self, request, app_record):
        try:
            req = ResponseParameters.model_validate(request.GET.dict())
        except ValidationError as error:
            return scim_validation_error(error)

        scim_user = to_scim_user(app_record, resource_location(request, app_record))
        return SCIMJsonResponse(
            scim_user.model_dump(
                scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
                attributes=req.attributes,
                excluded_attributes=req.excluded_attributes,
            )
        )

    def delete(self, request, app_record):
        delete_record(app_record["id"])
        return HttpResponse(status=HTTPStatus.NO_CONTENT)

    def put(self, request, app_record):
        req = ResponseParameters.model_validate(request.GET.dict())
        existing_user = to_scim_user(app_record, resource_location(request, app_record))
        try:
            replacement = User.model_validate_json(
                request.body,
                scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
            )
            replacement.replace(existing_user)
        except ValidationError as error:
            return scim_validation_error(error)
        except SCIMException as error:
            return scim_exception_error(error)

        updated_record = from_scim_user(replacement)
        try:
            save_record(updated_record)
        except SCIMException as error:
            return scim_exception_error(error)

        response_user = to_scim_user(
            updated_record, resource_location(request, updated_record)
        )
        return SCIMJsonResponse(
            response_user.model_dump(
                scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE,
                attributes=req.attributes,
                excluded_attributes=req.excluded_attributes,
            )
        )

    def patch(self, request, app_record):
        req = ResponseParameters.model_validate(request.GET.dict())
        try:
            patch = PatchOp[User].model_validate_json(
                request.body,
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

        return SCIMJsonResponse(
            scim_user.model_dump(
                scim_ctx=Context.RESOURCE_PATCH_RESPONSE,
                attributes=req.attributes,
                excluded_attributes=req.excluded_attributes,
            )
        )
# -- single-resource-end --


# -- collection-start --
def users_response(request, req, scim_ctx):
    """Return one page of users as a serialized SCIM ListResponse.

    A query applies to the SCIM representation rather than to the stored
    records, so the store is mapped before it is ordered and paginated.

    :param request: The incoming request, used to build resource locations.
    :param req: The parsed query, whichever verb carried it.
    :param scim_ctx: The context to serialize the response in.
    """
    users = [
        to_scim_user(record, resource_location(request, record))
        for record in list_records()
    ]
    total, page = page_of(users, req)
    response = ListResponse[User](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(page),
        resources=page,
    )
    return SCIMJsonResponse(
        response.model_dump(
            scim_ctx=scim_ctx,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        )
    )


class UsersView(SCIMView):
    """Handle GET and POST on the SCIM users collection."""

    def get(self, request):
        try:
            req = SearchRequest[User].model_validate(request.GET.dict())
        except ValidationError as error:
            return scim_validation_error(error)

        return users_response(request, req, Context.RESOURCE_QUERY_RESPONSE)

    def post(self, request):
        req = ResponseParameters.model_validate(request.GET.dict())
        try:
            request_user = User.model_validate_json(
                request.body,
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
        return SCIMJsonResponse(
            response_user.model_dump(
                scim_ctx=Context.RESOURCE_CREATION_RESPONSE,
                attributes=req.attributes,
                excluded_attributes=req.excluded_attributes,
            ),
            status=HTTPStatus.CREATED,
        )


# -- collection-end --


# -- search-users-start --
class UsersSearchView(SCIMView):
    """Answer the same query as GET /Users, with the parameters in the body."""

    def post(self, request):
        try:
            req = SearchRequest[User].model_validate_json(
                request.body, scim_ctx=Context.SEARCH_REQUEST
            )
        except ValidationError as error:
            return scim_validation_error(error)

        return users_response(request, req, Context.SEARCH_RESPONSE)
# -- search-users-end --


# -- search-root-start --
class RootSearchView(SCIMView):
    """Query every resource type the server serves.

    :rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>` has a root query cover them
    all, so the request is parameterised with a union and the response gathers
    groups alongside users. These guides expose no ``/Groups`` endpoint; the
    groups they gather are read-only fixtures.
    """

    def post(self, request):
        try:
            req = SearchRequest[User | Group].model_validate_json(
                request.body, scim_ctx=Context.SEARCH_REQUEST
            )
        except ValidationError as error:
            return scim_validation_error(error)

        resources = [
            to_scim_user(record, resource_location(request, record))
            for record in list_records()
        ]
        resources += [to_scim_group(record) for record in list_group_records()]
        total, page = page_of(resources, req)
        response = ListResponse[User | Group](
            total_results=total,
            start_index=req.start_index or 1,
            items_per_page=len(page),
            resources=page,
        )
        return SCIMJsonResponse(
            response.model_dump(
                scim_ctx=Context.SEARCH_RESPONSE,
                attributes=req.attributes,
                excluded_attributes=req.excluded_attributes,
            )
        )
# -- search-root-end --


# -- urls-start --
# ``/Users/.search`` comes first: the ``user`` converter would otherwise read
# ``.search`` as a resource id.
urlpatterns = [
    path("scim/v2/Users", UsersView.as_view(), name="scim_users"),
    path("scim/v2/Users/.search", UsersSearchView.as_view(), name="scim_users_search"),
    path("scim/v2/.search", RootSearchView.as_view(), name="scim_root_search"),
    path("scim/v2/Users/<user:app_record>", UserView.as_view(), name="scim_user"),
]
# -- urls-end --


# -- discovery-start --
# -- schemas-start --
class SchemasView(SCIMView):
    """Handle GET on the SCIM schemas collection."""

    def get(self, request):
        try:
            req = SearchRequest[Schema].model_validate(request.GET.dict())
        except ValidationError as error:
            return scim_validation_error(error)

        total, page = page_of(get_schemas(), req)
        response = ListResponse[Schema](
            total_results=total,
            start_index=req.start_index or 1,
            items_per_page=len(page),
            resources=page,
        )
        return SCIMJsonResponse(
            response.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
        )


class SchemaView(SCIMView):
    """Handle GET on a single SCIM schema."""

    def get(self, request, schema_id):
        try:
            schema = get_schema(schema_id)
        except KeyError:
            scim_error = Error(status=404, detail=f"Schema {schema_id!r} not found")
            return SCIMJsonResponse(
                scim_error.model_dump(), status=HTTPStatus.NOT_FOUND
            )
        return SCIMJsonResponse(
            schema.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
        )
# -- schemas-end --


# -- resource-types-start --
class ResourceTypesView(SCIMView):
    """Handle GET on the SCIM resource types collection."""

    def get(self, request):
        try:
            req = SearchRequest[ResourceType].model_validate(request.GET.dict())
        except ValidationError as error:
            return scim_validation_error(error)

        total, page = page_of(get_resource_types(), req)
        response = ListResponse[ResourceType](
            total_results=total,
            start_index=req.start_index or 1,
            items_per_page=len(page),
            resources=page,
        )
        return SCIMJsonResponse(
            response.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
        )


class ResourceTypeView(SCIMView):
    """Handle GET on a single SCIM resource type."""

    def get(self, request, resource_type_id):
        try:
            rt = get_resource_type(resource_type_id)
        except KeyError:
            scim_error = Error(
                status=404, detail=f"ResourceType {resource_type_id!r} not found"
            )
            return SCIMJsonResponse(
                scim_error.model_dump(), status=HTTPStatus.NOT_FOUND
            )
        return SCIMJsonResponse(
            rt.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
        )
# -- resource-types-end --


# -- service-provider-config-start --
class ServiceProviderConfigView(SCIMView):
    """Handle GET on the SCIM service provider configuration."""

    def get(self, request):
        return SCIMJsonResponse(
            service_provider_config.model_dump(
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
