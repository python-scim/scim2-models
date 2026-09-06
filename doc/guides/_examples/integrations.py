"""Framework-agnostic storage and mapping layer shared by the integration examples."""

import hashlib
from datetime import datetime
from datetime import timezone
from uuid import uuid4

from scim2_models import AuthenticationScheme
from scim2_models import Bulk
from scim2_models import ChangePassword
from scim2_models import CaseExact
from scim2_models import ETag
from scim2_models import Filter
from scim2_models import InvalidPathException
from scim2_models import Group
from scim2_models import Meta
from scim2_models import Path
from scim2_models import Patch
from scim2_models import ResourceType
from scim2_models import ServiceProviderConfig
from scim2_models import SearchRequest
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
    if req.sort_by:
        resources = sort_resources(resources, req.sort_by, req.sort_order)

    start = req.start_index_0 or 0
    limit = start + MAX_RESULTS
    stop = req.stop_index_0
    stop = limit if stop is None else min(stop, limit)
    return len(resources), resources[start:stop]


def sort_resources(resources, sort_by, sort_order=None):
    """Order resources by an attribute, per :rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>`.

    :param resources: The SCIM resources to order.
    :param sort_by: The ``sortBy`` query parameter, resolved by the request it
        came from, which names the resource type the endpoint serves.
    :param sort_order: The ``sortOrder`` query parameter, ascending by default.
    :raises InvalidPathException: If the attribute is unknown.
    """
    if sort_by.field_name is None:
        raise InvalidPathException(
            path=str(sort_by), detail=f"Cannot sort on {sort_by!r}"
        )

    # "String type attributes are case insensitive by default, unless the
    # attribute type is defined as a case-exact string."
    case_exact = sort_by.model.get_field_annotation(sort_by.field_name, CaseExact)
    descending = sort_order == SearchRequest.SortOrder.descending

    def key(resource):
        value = sort_by.get(resource, strict=False)
        if isinstance(value, list):
            # "resources are sorted by the value of the primary attribute, if
            # any, or else the first value in the list, if any."
            primary = next((each for each in value if each.primary), None)
            entry = primary or (value[0] if value else None)
            value = entry.value if entry else None
        if isinstance(value, str) and not case_exact:
            value = value.casefold()
        # "if there is no data for the specified sortBy value, they are sorted
        # via the sortOrder parameter, i.e., they are ordered last if ascending
        # and first if descending", which reversing the whole key achieves.
        return (value is None, value if value is not None else "")

    return sorted(resources, key=key, reverse=descending)
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
        emails=[User.Emails(value=record["email"])] if record.get("email") else None,
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
    return {
        "id": scim_user.id,
        "user_name": scim_user.user_name,
        "display_name": scim_user.display_name,
        "active": True if scim_user.active is None else scim_user.active,
        "email": scim_user.emails[0].value if scim_user.emails else None,
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
RESOURCE_MODELS = [User]


def get_schemas():
    """Return every :class:`~scim2_models.Schema` the server exposes."""
    return [model.to_schema() for model in RESOURCE_MODELS]


def get_schema(schema_id):
    """Return the :class:`~scim2_models.Schema` matching *schema_id*, or raise KeyError."""
    for model in RESOURCE_MODELS:
        schema = model.to_schema()
        if schema.id == schema_id:
            return schema
    raise KeyError(schema_id)


def get_resource_types():
    """Return every :class:`~scim2_models.ResourceType` the server exposes."""
    return [ResourceType.from_resource(model) for model in RESOURCE_MODELS]


def get_resource_type(resource_type_id):
    """Return the :class:`~scim2_models.ResourceType` matching *resource_type_id*, or raise KeyError."""
    for model in RESOURCE_MODELS:
        rt = ResourceType.from_resource(model)
        if rt.id == resource_type_id:
            return rt
    raise KeyError(resource_type_id)


service_provider_config = ServiceProviderConfig(
    patch=Patch(supported=True),
    bulk=Bulk(supported=False, max_operations=0, max_payload_size=0),
    filter=Filter(supported=False, max_results=0),
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
)
# -- discovery-end --
