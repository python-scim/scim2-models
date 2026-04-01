"""Framework-agnostic storage and mapping layer shared by the integration examples."""

from uuid import uuid4

from scim2_models import Meta
from scim2_models import User

# -- storage-start --
records = {}


def get_record(record_id):
    """Return the record for *record_id*, raising KeyError if absent."""
    if record_id not in records:
        raise KeyError(record_id)
    return records[record_id]


def list_records():
    """Return all stored records as a list."""
    return list(records.values())


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
