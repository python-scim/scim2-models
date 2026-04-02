"""Framework-agnostic storage and mapping layer shared by the integration examples."""

from uuid import uuid4

from scim2_models import AuthenticationScheme
from scim2_models import Bulk
from scim2_models import ChangePassword
from scim2_models import ETag
from scim2_models import Filter
from scim2_models import Meta
from scim2_models import Patch
from scim2_models import ResourceType
from scim2_models import ServiceProviderConfig
from scim2_models import Sort
from scim2_models import User

# -- storage-start --
records = {}


def get_record(record_id):
    """Return the record for *record_id*, raising KeyError if absent."""
    if record_id not in records:
        raise KeyError(record_id)
    return records[record_id]


def list_records(start=None, stop=None):
    """Return a page of stored records and the total count.

    :param start: 0-based start index.
    :param stop: 0-based stop index (exclusive).
    :return: A ``(total, page)`` tuple.
    """
    all_records = list(records.values())
    return len(all_records), all_records[start:stop]


def save_record(record):
    """Persist *record*, raising ValueError if its userName is already taken."""
    for existing in records.values():
        if existing["id"] != record["id"] and existing["user_name"] == record["user_name"]:
            raise ValueError(f"userName {record['user_name']!r} is already taken")
    records[record["id"]] = record


def delete_record(record_id):
    """Remove the record identified by *record_id*."""
    del records[record_id]
# -- storage-end --


# -- mapping-start --
def to_scim_user(record):
    """Convert an application record into a SCIM User resource."""
    return User(
        id=record["id"],
        user_name=record["user_name"],
        display_name=record.get("display_name"),
        active=record.get("active", True),
        emails=[User.Emails(value=record["email"])] if record.get("email") else None,
        meta=Meta(resource_type="User"),
    )


def from_scim_user(scim_user):
    """Convert a validated SCIM payload into the application shape."""
    return {
        "id": scim_user.id or str(uuid4()),
        "user_name": scim_user.user_name,
        "display_name": scim_user.display_name,
        "active": True if scim_user.active is None else scim_user.active,
        "email": scim_user.emails[0].value if scim_user.emails else None,
    }
# -- mapping-end --


# -- discovery-start --
RESOURCE_MODELS = [User]


def get_schemas(start=None, stop=None):
    """Return a page of :class:`~scim2_models.Schema` and the total count.

    :param start: 0-based start index.
    :param stop: 0-based stop index (exclusive).
    :return: A ``(total, page)`` tuple.
    """
    all_schemas = [model.to_schema() for model in RESOURCE_MODELS]
    return len(all_schemas), all_schemas[start:stop]


def get_schema(schema_id):
    """Return the :class:`~scim2_models.Schema` matching *schema_id*, or raise KeyError."""
    for model in RESOURCE_MODELS:
        schema = model.to_schema()
        if schema.id == schema_id:
            return schema
    raise KeyError(schema_id)


def get_resource_types(start=None, stop=None):
    """Return a page of :class:`~scim2_models.ResourceType` and the total count.

    :param start: 0-based start index.
    :param stop: 0-based stop index (exclusive).
    :return: A ``(total, page)`` tuple.
    """
    all_resource_types = [ResourceType.from_resource(model) for model in RESOURCE_MODELS]
    return len(all_resource_types), all_resource_types[start:stop]


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
    sort=Sort(supported=False),
    etag=ETag(supported=False),
    authentication_schemes=[
        AuthenticationScheme(
            type=AuthenticationScheme.Type.httpbasic,
            name="HTTP Basic",
            description="Authentication via HTTP Basic",
        ),
    ],
)
# -- discovery-end --
