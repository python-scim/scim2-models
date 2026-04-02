import json
from http import HTTPStatus

from django.http import HttpResponse
from django.urls import path
from django.urls import register_converter
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import PatchOp
from scim2_models import ResponseParameters
from scim2_models import SearchRequest
from scim2_models import UniquenessException
from scim2_models import User

from .integrations import delete_record
from .integrations import from_scim_user
from .integrations import get_record
from .integrations import list_records
from .integrations import save_record
from .integrations import to_scim_user

# -- setup-start --
def scim_response(payload, status=HTTPStatus.OK):
    """Build a Django response with the SCIM media type."""
    return HttpResponse(
        payload,
        status=status,
        content_type="application/scim+json",
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
    return scim_response(scim_error.model_dump_json(), scim_error.status)
# -- validation-helper-end --


# -- uniqueness-helper-start --
def scim_uniqueness_error(error):
    """Turn uniqueness errors into a SCIM 409 response."""
    scim_error = UniquenessException(detail=str(error)).to_error()
    return scim_response(scim_error.model_dump_json(), HTTPStatus.CONFLICT)
# -- uniqueness-helper-end --


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

        scim_user = to_scim_user(app_record)
        return scim_response(
            scim_user.model_dump_json(
                scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
                attributes=req.attributes,
                excluded_attributes=req.excluded_attributes,
            )
        )

    def delete(self, request, app_record):
        delete_record(app_record["id"])
        return scim_response("", HTTPStatus.NO_CONTENT)

    def put(self, request, app_record):
        existing_user = to_scim_user(app_record)
        try:
            replacement = User.model_validate(
                json.loads(request.body),
                scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
                original=existing_user,
            )
        except ValidationError as error:
            return scim_validation_error(error)

        replacement.id = existing_user.id
        updated_record = from_scim_user(replacement)
        try:
            save_record(updated_record)
        except ValueError as error:
            return scim_uniqueness_error(error)

        response_user = to_scim_user(updated_record)
        return scim_response(
            response_user.model_dump_json(
                scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE
            )
        )

    def patch(self, request, app_record):
        try:
            patch = PatchOp[User].model_validate(
                json.loads(request.body),
                scim_ctx=Context.RESOURCE_PATCH_REQUEST,
            )
        except ValidationError as error:
            return scim_validation_error(error)

        scim_user = to_scim_user(app_record)
        patch.patch(scim_user)

        updated_record = from_scim_user(scim_user)
        try:
            save_record(updated_record)
        except ValueError as error:
            return scim_uniqueness_error(error)

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

        all_records = list_records()
        page = all_records[req.start_index_0 : req.stop_index_0]
        resources = [to_scim_user(record) for record in page]
        response = ListResponse[User](
            total_results=len(all_records),
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
        except ValueError as error:
            return scim_uniqueness_error(error)

        response_user = to_scim_user(app_record)
        return scim_response(
            response_user.model_dump_json(scim_ctx=Context.RESOURCE_CREATION_RESPONSE),
            HTTPStatus.CREATED,
        )


urlpatterns = [
    path("scim/v2/Users", UsersView.as_view(), name="scim_users"),
    path("scim/v2/Users/<user:app_record>", UserView.as_view(), name="scim_user"),
]
# -- collection-end --
# -- endpoints-end --
