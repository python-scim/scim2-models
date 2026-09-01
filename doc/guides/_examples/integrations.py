"""Framework-agnostic storage and mapping layer shared by the integration examples."""

import hashlib
from datetime import datetime
from datetime import timezone
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


def paginate(resources, start=None, stop=None):
    """Return the total count and the requested page of resources.

    A page never exceeds ``MAX_RESULTS`` entries, which is the bound the
    :class:`~scim2_models.ServiceProviderConfig` advertises.

    :param start: 0-based start index.
    :param stop: 0-based stop index (exclusive).
    :return: A ``(total, page)`` tuple.
    """
    start = start or 0
    limit = start + MAX_RESULTS
    stop = limit if stop is None else min(stop, limit)
    return len(resources), resources[start:stop]


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
# -- mapping-end --


# -- discovery-start --
RESOURCE_MODELS = [User]


def get_schemas():
    """Return the :class:`~scim2_models.Schema` of every exposed model."""
    return [model.to_schema() for model in RESOURCE_MODELS]


def get_schema(schema_id):
    """Return the :class:`~scim2_models.Schema` matching *schema_id*, or raise KeyError."""
    for model in RESOURCE_MODELS:
        schema = model.to_schema()
        if schema.id == schema_id:
            return schema
    raise KeyError(schema_id)


def get_resource_types():
    """Return the :class:`~scim2_models.ResourceType` of every exposed model."""
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
    filter=Filter(supported=True, max_results=MAX_RESULTS),
    change_password=ChangePassword(supported=False),
    sort=Sort(supported=False),
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
