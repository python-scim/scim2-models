"""Framework-agnostic storage and mapping layer shared by the integration examples."""

import hashlib
from datetime import datetime
from datetime import timezone
from http import HTTPStatus
from uuid import uuid4

from scim2_models import AuthenticationScheme
from scim2_models import Bulk
from scim2_models import BulkOperation
from scim2_models import BulkResponse
from scim2_models import ChangePassword
from scim2_models import Error
from scim2_models import ETag
from scim2_models import Filter
from scim2_models import Group
from scim2_models import Meta
from scim2_models import Patch
from scim2_models import SCIMException
from scim2_models import ScimProvider
from scim2_models import ServiceProviderConfig
from scim2_models import Sort
from scim2_models import UniquenessException
from scim2_models import User

# -- storage-start --
records = {}

MAX_RESULTS = 50


def get_record(record_id):
    """Return the record for *record_id*, raising KeyError if absent."""
    if record_id not in records:
        raise KeyError(record_id)
    return records[record_id]


def list_records():
    """Return every stored record."""
    return list(records.values())


# -- sorting-start --
def page_of(resources, req):
    """Return the total count and the page a query asks for.

    Sorting comes before paging, so a page holds the same resources whatever
    the order asked for. A page never exceeds ``MAX_RESULTS`` entries, which is
    the bound the :class:`~scim2_models.ServiceProviderConfig` advertises.

    :param resources: The SCIM resources to answer from.
    :param req: The parsed query.
    :return: A ``(total, page)`` tuple.
    """
    resources = req.sort(resources)
    start = req.start_index_0 or 0
    limit = start + MAX_RESULTS
    stop = req.stop_index_0
    stop = limit if stop is None else min(stop, limit)
    return len(resources), resources[start:stop]


# -- sorting-end --


def save_record(record):
    """Persist *record*, raising UniquenessException if its userName is already taken."""
    if not record.get("id"):
        record["id"] = str(uuid4())
    for existing in records.values():
        if (
            existing["id"] != record["id"]
            and existing["user_name"] == record["user_name"]
        ):
            raise UniquenessException(
                detail=f"userName {record['user_name']!r} is already taken"
            )
    now = datetime.now(timezone.utc)
    record.setdefault("created_at", now)
    record["updated_at"] = now
    records[record["id"]] = record


def delete_record(record_id):
    """Remove the record identified by *record_id*."""
    del records[record_id]


# The root query needs a second resource type to gather. These guides do not
# implement the ``/Groups`` endpoints, so groups are read-only fixtures.
group_records = {
    "6c8a2e1f": {"id": "6c8a2e1f", "display_name": "Administrators"},
    "b3f1d049": {"id": "b3f1d049", "display_name": "Auditors"},
}


def list_group_records():
    """Return every stored group record."""
    return list(group_records.values())


# -- storage-end --


# -- mapping-start --
def to_scim_user(record, location=None):
    """Convert an application record into a SCIM User resource.

    :param record: The application record.
    :param location: Canonical URL of the resource, set in :attr:`~scim2_models.Meta.location`.
    """
    return User(
        id=record["id"],
        user_name=record["user_name"],
        display_name=record.get("display_name"),
        active=record.get("active", True),
        emails=(
            [User.Emails(value=record["email"], type=record.get("email_type"))]
            if record.get("email")
            else None
        ),
        meta=Meta(
            resource_type="User",
            version=make_etag(record),
            created=record["created_at"],
            last_modified=record["updated_at"],
            location=location,
        ),
    )


def from_scim_user(scim_user):
    """Convert a validated SCIM payload into the application shape."""
    email = scim_user.emails[0] if scim_user.emails else None
    return {
        "id": scim_user.id,
        "user_name": scim_user.user_name,
        "display_name": scim_user.display_name,
        "active": True if scim_user.active is None else scim_user.active,
        "email": email.value if email else None,
        "email_type": str(email.type) if email and email.type else None,
    }


def make_etag(record):
    """Compute a weak ETag from a record's content."""
    digest = hashlib.sha256(str(sorted(record.items())).encode()).hexdigest()[:16]
    return f'W/"{digest}"'


def to_scim_group(record):
    """Convert an application group record into a SCIM Group resource.

    ``meta.location`` is left out, as these guides expose no ``/Groups``
    endpoint to point it at.

    :param record: The application group record.
    """
    return Group(
        id=record["id"],
        display_name=record["display_name"],
        meta=Meta(resource_type="Group"),
    )


# -- mapping-end --


# -- discovery-start --
provider = ScimProvider(
    models=[User],
    config=ServiceProviderConfig(
        patch=Patch(supported=True),
        bulk=Bulk(supported=True, max_operations=100, max_payload_size=1048576),
        filter=Filter(supported=True, max_results=MAX_RESULTS),
        change_password=ChangePassword(supported=False),
        sort=Sort(supported=True),
        etag=ETag(supported=True),
        authentication_schemes=[
            AuthenticationScheme(
                type=AuthenticationScheme.Type.httpbasic,
                name="HTTP Basic",
                description="Authentication via HTTP Basic",
            ),
        ],
    ),
)
"""What this server serves, and what it announces of itself.

``provider.schemas`` and ``provider.resource_types`` are derived from the
models, so the three discovery endpoints and the resources they describe can
never drift apart.
"""


def get_schema(schema_id):
    """Return the :class:`~scim2_models.Schema` matching *schema_id*, or raise KeyError."""
    for schema in provider.schemas:
        if schema.id == schema_id:
            return schema
    raise KeyError(schema_id)


def get_resource_type(resource_type_id):
    """Return the :class:`~scim2_models.ResourceType` matching *resource_type_id*, or raise KeyError."""
    for resource_type in provider.resource_types:
        if resource_type.id == resource_type_id:
            return resource_type
    raise KeyError(resource_type_id)


# -- discovery-end --


# -- bulk-start --
class PayloadTooLargeException(SCIMException):
    """A bulk job beyond the limits the service provider announces.

    :rfc:`RFC7644 §3.7.4 <7644#section-3.7.4>` answers 413 here, a status the
    scimType table of §3.12 does not cover, so the hierarchy scim2-models
    exposes is extended with it.
    """

    status = HTTPStatus.REQUEST_ENTITY_TOO_LARGE


BULK_SUCCESS_STATUS = {
    BulkOperation.Method.post: HTTPStatus.CREATED,
    BulkOperation.Method.put: HTTPStatus.OK,
    BulkOperation.Method.patch: HTTPStatus.OK,
    BulkOperation.Method.delete: HTTPStatus.NO_CONTENT,
}
"""The status each method answers with when it succeeds."""


def record_id_of(path):
    """Return the resource identifier a bulk operation path designates.

    :param path: The ``path`` of the operation, relative to the SCIM root.
    """
    return path.rsplit("/", 1)[-1]


def apply_operation(operation, record):
    """Apply one bulk operation to the store and return the record it acted on.

    ``operation.data`` arrives validated in the context of the single request
    the operation stands for, so a POST or a PUT carries a
    :class:`~scim2_models.User` and a PATCH a :class:`~scim2_models.PatchOp`.
    Nothing is left to validate here.

    :param operation: The operation to apply.
    :param record: The record the operation path designates, or None for a POST.
    """
    if operation.method == BulkOperation.Method.post:
        created_record = from_scim_user(operation.data)
        save_record(created_record)
        return created_record

    if operation.method == BulkOperation.Method.delete:
        delete_record(record["id"])
        return record

    scim_user = to_scim_user(record)
    if operation.method == BulkOperation.Method.patch:
        # A patch edits the stored state, where a replacement takes the
        # payload and carries over what the client may not send.
        operation.data.patch(scim_user)
        updated_record = from_scim_user(scim_user)
    else:
        operation.data.replace(scim_user)
        updated_record = from_scim_user(operation.data)

    save_record(updated_record)
    return updated_record


def run_operation(operation, location_for):
    """Apply one operation of a bulk job and describe its outcome.

    The target is resolved before the operation is applied, so a failure still
    knows the location :rfc:`RFC7644 §3.7 <7644#section-3.7>` requires of every
    response but a failed creation.

    :param operation: The operation to run.
    :param location_for: Builds the canonical URL of a record.
    """
    result = BulkOperation[User](method=operation.method, bulk_id=operation.bulk_id)

    record = None
    if operation.method != BulkOperation.Method.post:
        try:
            record = get_record(record_id_of(operation.path))
        except KeyError:
            result.status = HTTPStatus.NOT_FOUND
            result.response = Error(
                status=HTTPStatus.NOT_FOUND, detail="Resource does not exist."
            )
            return result
        result.location = location_for(record)

    try:
        acted_record = apply_operation(operation, record)
    except SCIMException as exception:
        result.status = exception.status
        result.response = exception.to_error()
        return result

    result.status = BULK_SUCCESS_STATUS[operation.method]
    result.location = location_for(acted_record)
    if result.status != HTTPStatus.NO_CONTENT:
        result.version = make_etag(acted_record)
    return result


def execute_bulk(bulk_request, location_for):
    """Apply every operation of a bulk job and describe each outcome.

    :param bulk_request: The validated bulk request.
    :param location_for: Builds the canonical URL of a record, which only the
        HTTP layer of a framework knows how to spell.
    """
    limit = provider.config.bulk.max_operations
    if limit is not None and len(bulk_request.operations) > limit:
        raise PayloadTooLargeException(
            detail=f"The number of operations exceeds the maxOperations ({limit})."
        )

    operations = []
    errors = 0

    for operation in bulk_request.operations:
        result = run_operation(operation, location_for)
        operations.append(result)

        if result.status < HTTPStatus.BAD_REQUEST:
            continue

        # RFC7644 §3.7.3: a job performs as many changes as possible, unless
        # the client caps the failures it accepts with "failOnErrors".
        errors += 1
        if bulk_request.fail_on_errors and errors >= bulk_request.fail_on_errors:
            break

    return BulkResponse[User](operations=operations)


# -- bulk-end --
