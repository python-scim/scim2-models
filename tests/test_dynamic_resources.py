import datetime
from typing import Literal
from typing import Union

from scim2_models.base import CaseExact
from scim2_models.base import ComplexAttribute
from scim2_models.base import ExternalReference
from scim2_models.base import MultiValuedComplexAttribute
from scim2_models.base import Mutability
from scim2_models.base import Reference
from scim2_models.base import Required
from scim2_models.base import Returned
from scim2_models.base import Uniqueness
from scim2_models.base import URIReference
from scim2_models.rfc7643.resource import Extension
from scim2_models.rfc7643.resource import Resource
from scim2_models.rfc7643.schema import Attribute
from scim2_models.rfc7643.schema import Schema
from scim2_models.utils import Base64Bytes


def test_make_group_model_from_schema(load_sample):
    payload = load_sample("rfc7643-8.7.1-schema-group.json")
    schema = Schema.model_validate(payload)
    Group = Resource.from_schema(schema)

    assert Group.model_fields["schemas"].default == [
        "urn:ietf:params:scim:schemas:core:2.0:Group"
    ]

    # displayName
    assert Group.get_field_root_type("display_name") is str
    assert not Group.get_field_multiplicity("display_name")
    assert (
        Group.model_fields["display_name"].description
        == "A human-readable name for the Group. REQUIRED."
    )
    assert Group.get_field_annotation("display_name", Required) == Required.false
    assert Group.get_field_annotation("display_name", CaseExact) == CaseExact.false
    assert (
        Group.get_field_annotation("display_name", Mutability) == Mutability.read_write
    )
    assert Group.get_field_annotation("display_name", Returned) == Returned.default
    assert Group.get_field_annotation("display_name", Uniqueness) == Uniqueness.none

    # members
    Members = Group.get_field_root_type("members")
    assert Members == Group.Members
    assert issubclass(Members, ComplexAttribute)
    assert Group.get_field_multiplicity("members")
    assert (
        Group.model_fields["members"].description == "A list of members of the Group."
    )
    assert Group.get_field_annotation("members", Required) == Required.false
    assert Group.get_field_annotation("members", CaseExact) == CaseExact.false
    assert Group.get_field_annotation("members", Mutability) == Mutability.read_write
    assert Group.get_field_annotation("members", Returned) == Returned.default
    assert Group.get_field_annotation("members", Uniqueness) == Uniqueness.none

    # members.value
    assert Members.get_field_root_type("value") is str
    assert not Members.get_field_multiplicity("value")
    assert (
        Members.model_fields["value"].description
        == "Identifier of the member of this Group."
    )
    assert Members.get_field_annotation("value", Required) == Required.false
    assert Members.get_field_annotation("value", CaseExact) == CaseExact.false
    assert Members.get_field_annotation("value", Mutability) == Mutability.immutable
    assert Members.get_field_annotation("value", Returned) == Returned.default
    assert Members.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # Members.ref
    assert (
        Members.get_field_root_type("ref")
        == Reference[Union[Literal["User"], Literal["Group"]]]
    )
    assert not Members.get_field_multiplicity("ref")
    assert (
        Members.model_fields["ref"].description
        == "The URI corresponding to a SCIM resource that is a member of this Group."
    )
    assert Members.model_fields["ref"].serialization_alias == "$ref"
    assert Members.get_field_annotation("ref", Required) == Required.false
    assert Members.get_field_annotation("ref", CaseExact) == CaseExact.false
    assert Members.get_field_annotation("ref", Mutability) == Mutability.immutable
    assert Members.get_field_annotation("ref", Returned) == Returned.default
    assert Members.get_field_annotation("ref", Uniqueness) == Uniqueness.none

    # Members.type
    assert Members.get_field_root_type("type") is str
    assert not Members.get_field_multiplicity("type")
    assert (
        Members.model_fields["type"].description
        == "A label indicating the type of resource, e.g., 'User' or 'Group'."
    )
    assert Members.get_field_annotation("type", Required) == Required.false
    assert Members.get_field_annotation("type", CaseExact) == CaseExact.false
    assert Members.model_fields["type"].examples == ["User", "Group"]
    assert Members.get_field_annotation("type", Mutability) == Mutability.immutable
    assert Members.get_field_annotation("type", Returned) == Returned.default
    assert Members.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # Members.display
    assert Members.get_field_root_type("display") is str
    assert not Members.get_field_multiplicity("display")
    assert (
        Members.model_fields["display"].description
        == "A human-readable name for the group member, primarily used for display purposes."
    )
    assert Members.get_field_annotation("display", Required) == Required.false
    assert Members.get_field_annotation("display", CaseExact) == CaseExact.false
    assert Members.get_field_annotation("display", Mutability) == Mutability.read_only
    assert Members.get_field_annotation("display", Returned) == Returned.default
    assert Members.get_field_annotation("display", Uniqueness) == Uniqueness.none

    payload = load_sample("rfc7643-8.4-group.json")
    obj = Group.model_validate(payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    assert obj.id == "e9e30dba-f08f-4109-8486-d5c6a331660a"
    assert obj.display_name == "Tour Guides"
    assert obj.members[0].value == "2819c223-7f76-453a-919d-413861904646"
    assert obj.members[0].ref == Reference(
        "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    )

    assert obj.members[0].display == "Babs Jensen"
    assert obj.members[1].value == "902c246b-6245-4190-8e05-00816be7344a"
    assert obj.members[1].ref == Reference(
        "https://example.com/v2/Users/902c246b-6245-4190-8e05-00816be7344a"
    )
    assert obj.members[1].display == "Mandy Pepperidge"
    assert obj.meta.resource_type == "Group"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.last_modified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"3694e05e9dff592"'
    assert (
        obj.meta.location
        == "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a"
    )

    assert obj.model_dump() == payload


def test_make_user_model_from_schema(load_sample):
    payload = load_sample("rfc7643-8.7.1-schema-user.json")
    schema = Schema.model_validate(payload)
    User = Resource.from_schema(schema)

    assert User.model_fields["schemas"].default == [
        "urn:ietf:params:scim:schemas:core:2.0:User"
    ]

    # user_name
    assert User.get_field_root_type("user_name") is str
    assert not User.get_field_multiplicity("user_name")
    assert (
        User.model_fields["user_name"].description
        == "Unique identifier for the User, typically used by the user to directly authenticate to the service provider. Each User MUST include a non-empty userName value.  This identifier MUST be unique across the service provider's entire set of Users. REQUIRED."
    )
    assert User.get_field_annotation("user_name", Required) == Required.true
    assert User.get_field_annotation("user_name", CaseExact) == CaseExact.false
    assert User.get_field_annotation("user_name", Mutability) == Mutability.read_write
    assert User.get_field_annotation("user_name", Returned) == Returned.default
    assert User.get_field_annotation("user_name", Uniqueness) == Uniqueness.server

    # name
    Name = User.get_field_root_type("name")
    assert Name == User.Name
    assert issubclass(Name, ComplexAttribute)
    assert not User.get_field_multiplicity("name")
    assert (
        User.model_fields["name"].description
        == "The components of the user's real name. Providers MAY return just the full name as a single string in the formatted sub-attribute, or they MAY return just the individual component attributes using the other sub-attributes, or they MAY return both.  If both variants are returned, they SHOULD be describing the same name, with the formatted name indicating how the component attributes should be combined."
    )
    assert User.get_field_annotation("name", Required) == Required.false
    assert User.get_field_annotation("name", CaseExact) == CaseExact.false
    assert User.get_field_annotation("name", Mutability) == Mutability.read_write
    assert User.get_field_annotation("name", Returned) == Returned.default
    assert User.get_field_annotation("name", Uniqueness) == Uniqueness.none

    # name.formatted
    assert Name.get_field_root_type("formatted") is str
    assert not Name.get_field_multiplicity("formatted")
    assert (
        Name.model_fields["formatted"].description
        == "The full name, including all middle names, titles, and suffixes as appropriate, formatted for display (e.g., 'Ms. Barbara J Jensen, III')."
    )
    assert Name.get_field_annotation("formatted", Required) == Required.false
    assert Name.get_field_annotation("formatted", CaseExact) == CaseExact.false
    assert Name.get_field_annotation("formatted", Mutability) == Mutability.read_write
    assert Name.get_field_annotation("formatted", Returned) == Returned.default
    assert Name.get_field_annotation("formatted", Uniqueness) == Uniqueness.none

    # name.family_name
    assert Name.get_field_root_type("family_name") is str
    assert not Name.get_field_multiplicity("family_name")
    assert (
        Name.model_fields["family_name"].description
        == "The family name of the User, or last name in most Western languages (e.g., 'Jensen' given the full name 'Ms. Barbara J Jensen, III')."
    )
    assert Name.get_field_annotation("family_name", Required) == Required.false
    assert Name.get_field_annotation("family_name", CaseExact) == CaseExact.false
    assert Name.get_field_annotation("family_name", Mutability) == Mutability.read_write
    assert Name.get_field_annotation("family_name", Returned) == Returned.default
    assert Name.get_field_annotation("family_name", Uniqueness) == Uniqueness.none

    # name.given_name
    assert Name.get_field_root_type("given_name") is str
    assert not Name.get_field_multiplicity("given_name")
    assert (
        Name.model_fields["given_name"].description
        == "The given name of the User, or first name in most Western languages (e.g., 'Barbara' given the full name 'Ms. Barbara J Jensen, III')."
    )
    assert Name.get_field_annotation("given_name", Required) == Required.false
    assert Name.get_field_annotation("given_name", CaseExact) == CaseExact.false
    assert Name.get_field_annotation("given_name", Mutability) == Mutability.read_write
    assert Name.get_field_annotation("given_name", Returned) == Returned.default
    assert Name.get_field_annotation("given_name", Uniqueness) == Uniqueness.none

    # name.middle_name
    assert Name.get_field_root_type("middle_name") is str
    assert not Name.get_field_multiplicity("middle_name")
    assert (
        Name.model_fields["middle_name"].description
        == "The middle name(s) of the User (e.g., 'Jane' given the full name 'Ms. Barbara J Jensen, III')."
    )
    assert Name.get_field_annotation("middle_name", Required) == Required.false
    assert Name.get_field_annotation("middle_name", CaseExact) == CaseExact.false
    assert Name.get_field_annotation("middle_name", Mutability) == Mutability.read_write
    assert Name.get_field_annotation("middle_name", Returned) == Returned.default
    assert Name.get_field_annotation("middle_name", Uniqueness) == Uniqueness.none

    # name.honorific_prefix
    assert Name.get_field_root_type("honorific_prefix") is str
    assert not Name.get_field_multiplicity("honorific_prefix")
    assert (
        Name.model_fields["honorific_prefix"].description
        == "The honorific prefix(es) of the User, or title in most Western languages (e.g., 'Ms.' given the full name 'Ms. Barbara J Jensen, III')."
    )
    assert Name.get_field_annotation("honorific_prefix", Required) == Required.false
    assert Name.get_field_annotation("honorific_prefix", CaseExact) == CaseExact.false
    assert (
        Name.get_field_annotation("honorific_prefix", Mutability)
        == Mutability.read_write
    )
    assert Name.get_field_annotation("honorific_prefix", Returned) == Returned.default
    assert Name.get_field_annotation("honorific_prefix", Uniqueness) == Uniqueness.none

    # name.honorific_suffix
    assert Name.get_field_root_type("honorific_suffix") is str
    assert not Name.get_field_multiplicity("honorific_suffix")
    assert (
        Name.model_fields["honorific_suffix"].description
        == "The honorific suffix(es) of the User, or suffix in most Western languages (e.g., 'III' given the full name 'Ms. Barbara J Jensen, III')."
    )
    assert Name.get_field_annotation("honorific_suffix", Required) == Required.false
    assert Name.get_field_annotation("honorific_suffix", CaseExact) == CaseExact.false
    assert (
        Name.get_field_annotation("honorific_suffix", Mutability)
        == Mutability.read_write
    )
    assert Name.get_field_annotation("honorific_suffix", Returned) == Returned.default
    assert Name.get_field_annotation("honorific_suffix", Uniqueness) == Uniqueness.none

    # display_name
    assert User.get_field_root_type("display_name") is str
    assert not User.get_field_multiplicity("display_name")
    assert (
        User.model_fields["display_name"].description
        == "The name of the User, suitable for display to end-users.  The name SHOULD be the full name of the User being described, if known."
    )
    assert User.get_field_annotation("display_name", Required) == Required.false
    assert User.get_field_annotation("display_name", CaseExact) == CaseExact.false
    assert (
        User.get_field_annotation("display_name", Mutability) == Mutability.read_write
    )
    assert User.get_field_annotation("display_name", Returned) == Returned.default
    assert User.get_field_annotation("display_name", Uniqueness) == Uniqueness.none

    # nick_name
    assert User.get_field_root_type("nick_name") is str
    assert not User.get_field_multiplicity("nick_name")
    assert (
        User.model_fields["nick_name"].description
        == "The casual way to address the user in real life, e.g., 'Bob' or 'Bobby' instead of 'Robert'.  This attribute SHOULD NOT be used to represent a User's username (e.g., 'bjensen' or 'mpepperidge')."
    )
    assert User.get_field_annotation("nick_name", Required) == Required.false
    assert User.get_field_annotation("nick_name", CaseExact) == CaseExact.false
    assert User.get_field_annotation("nick_name", Mutability) == Mutability.read_write
    assert User.get_field_annotation("nick_name", Returned) == Returned.default
    assert User.get_field_annotation("nick_name", Uniqueness) == Uniqueness.none

    # profile_url
    assert User.get_field_root_type("profile_url") == Reference[ExternalReference]
    assert not User.get_field_multiplicity("profile_url")
    assert (
        User.model_fields["profile_url"].description
        == "A fully qualified URL pointing to a page representing the User's online profile."
    )
    assert User.get_field_annotation("profile_url", Required) == Required.false
    assert User.get_field_annotation("profile_url", CaseExact) == CaseExact.false
    assert User.get_field_annotation("profile_url", Mutability) == Mutability.read_write
    assert User.get_field_annotation("profile_url", Returned) == Returned.default
    assert User.get_field_annotation("profile_url", Uniqueness) == Uniqueness.none

    # title
    assert User.get_field_root_type("title") is str
    assert not User.get_field_multiplicity("title")
    assert (
        User.model_fields["title"].description
        == 'The user\'s title, such as "Vice President."'
    )
    assert User.get_field_annotation("title", Required) == Required.false
    assert User.get_field_annotation("title", CaseExact) == CaseExact.false
    assert User.get_field_annotation("title", Mutability) == Mutability.read_write
    assert User.get_field_annotation("title", Returned) == Returned.default
    assert User.get_field_annotation("title", Uniqueness) == Uniqueness.none

    # user_type
    assert User.get_field_root_type("user_type") is str
    assert not User.get_field_multiplicity("user_type")
    assert (
        User.model_fields["user_type"].description
        == "Used to identify the relationship between the organization and the user.  Typical values used might be 'Contractor', 'Employee', 'Intern', 'Temp', 'External', and 'Unknown', but any value may be used."
    )
    assert User.get_field_annotation("user_type", Required) == Required.false
    assert User.get_field_annotation("user_type", CaseExact) == CaseExact.false
    assert User.get_field_annotation("user_type", Mutability) == Mutability.read_write
    assert User.get_field_annotation("user_type", Returned) == Returned.default
    assert User.get_field_annotation("user_type", Uniqueness) == Uniqueness.none

    # preferred_language
    assert User.get_field_root_type("preferred_language") is str
    assert not User.get_field_multiplicity("preferred_language")
    assert (
        User.model_fields["preferred_language"].description
        == "Indicates the User's preferred written or spoken language.  Generally used for selecting a localized user interface; e.g., 'en_US' specifies the language English and country US."
    )
    assert User.get_field_annotation("preferred_language", Required) == Required.false
    assert User.get_field_annotation("preferred_language", CaseExact) == CaseExact.false
    assert (
        User.get_field_annotation("preferred_language", Mutability)
        == Mutability.read_write
    )
    assert User.get_field_annotation("preferred_language", Returned) == Returned.default
    assert (
        User.get_field_annotation("preferred_language", Uniqueness) == Uniqueness.none
    )

    # locale
    assert User.get_field_root_type("locale") is str
    assert not User.get_field_multiplicity("locale")
    assert (
        User.model_fields["locale"].description
        == "Used to indicate the User's default location for purposes of localizing items such as currency, date time format, or numerical representations."
    )
    assert User.get_field_annotation("locale", Required) == Required.false
    assert User.get_field_annotation("locale", CaseExact) == CaseExact.false
    assert User.get_field_annotation("locale", Mutability) == Mutability.read_write
    assert User.get_field_annotation("locale", Returned) == Returned.default
    assert User.get_field_annotation("locale", Uniqueness) == Uniqueness.none

    # timezone
    assert User.get_field_root_type("timezone") is str
    assert not User.get_field_multiplicity("timezone")
    assert (
        User.model_fields["timezone"].description
        == "The User's time zone in the 'Olson' time zone database format, e.g., 'America/Los_Angeles'."
    )
    assert User.get_field_annotation("timezone", Required) == Required.false
    assert User.get_field_annotation("timezone", CaseExact) == CaseExact.false
    assert User.get_field_annotation("timezone", Mutability) == Mutability.read_write
    assert User.get_field_annotation("timezone", Returned) == Returned.default
    assert User.get_field_annotation("timezone", Uniqueness) == Uniqueness.none

    # active
    assert User.get_field_root_type("active") is bool
    assert not User.get_field_multiplicity("active")
    assert (
        User.model_fields["active"].description
        == "A Boolean value indicating the User's administrative status."
    )
    assert User.get_field_annotation("active", Required) == Required.false
    assert User.get_field_annotation("active", CaseExact) == CaseExact.false
    assert User.get_field_annotation("active", Mutability) == Mutability.read_write
    assert User.get_field_annotation("active", Returned) == Returned.default
    assert User.get_field_annotation("active", Uniqueness) == Uniqueness.none

    # password
    assert User.get_field_root_type("password") is str
    assert not User.get_field_multiplicity("password")
    assert (
        User.model_fields["password"].description
        == "The User's cleartext password.  This attribute is intended to be used as a means to specify an initial password when creating a new User or to reset an existing User'spassword."
    )
    assert User.get_field_annotation("password", Required) == Required.false
    assert User.get_field_annotation("password", CaseExact) == CaseExact.false
    assert User.get_field_annotation("password", Mutability) == Mutability.write_only
    assert User.get_field_annotation("password", Returned) == Returned.never
    assert User.get_field_annotation("password", Uniqueness) == Uniqueness.none

    # emails
    Emails = User.get_field_root_type("emails")
    assert Emails == User.Emails
    assert issubclass(Emails, MultiValuedComplexAttribute)
    assert User.get_field_multiplicity("emails")
    assert (
        User.model_fields["emails"].description
        == "Email addresses for the user.  The value SHOULD be canonicalized by the service provider, e.g., 'bjensen@example.com' instead of 'bjensen@EXAMPLE.COM'. Canonical type values of 'work', 'home', and 'other'."
    )
    assert User.get_field_annotation("emails", Required) == Required.false
    assert User.get_field_annotation("emails", CaseExact) == CaseExact.false
    assert User.get_field_annotation("emails", Mutability) == Mutability.read_write
    assert User.get_field_annotation("emails", Returned) == Returned.default
    assert User.get_field_annotation("emails", Uniqueness) == Uniqueness.none

    # email.value
    assert Emails.get_field_root_type("value") is str
    assert not Emails.get_field_multiplicity("value")
    assert (
        Emails.model_fields["value"].description
        == "Email addresses for the user.  The value SHOULD be canonicalized by the service provider, e.g., 'bjensen@example.com' instead of 'bjensen@EXAMPLE.COM'. Canonical type values of 'work', 'home', and 'other'."
    )
    assert Emails.get_field_annotation("value", Required) == Required.false
    assert Emails.get_field_annotation("value", CaseExact) == CaseExact.false
    assert Emails.get_field_annotation("value", Mutability) == Mutability.read_write
    assert Emails.get_field_annotation("value", Returned) == Returned.default
    assert Emails.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # email.display
    assert Emails.get_field_root_type("display") is str
    assert not Emails.get_field_multiplicity("display")
    assert (
        Emails.model_fields["display"].description
        == "A human-readable name, primarily used for display purposes.  READ-ONLY."
    )
    assert Emails.get_field_annotation("display", Required) == Required.false
    assert Emails.get_field_annotation("display", CaseExact) == CaseExact.false
    assert Emails.get_field_annotation("display", Mutability) == Mutability.read_write
    assert Emails.get_field_annotation("display", Returned) == Returned.default
    assert Emails.get_field_annotation("display", Uniqueness) == Uniqueness.none

    # email.type
    assert Emails.get_field_root_type("type") is str
    assert not Emails.get_field_multiplicity("type")
    assert (
        Emails.model_fields["type"].description
        == "A label indicating the attribute's function, e.g., 'work' or 'home'."
    )
    assert Emails.get_field_annotation("type", Required) == Required.false
    assert Emails.get_field_annotation("type", CaseExact) == CaseExact.false
    assert Emails.model_fields["type"].examples == ["work", "home", "other"]
    assert Emails.get_field_annotation("type", Mutability) == Mutability.read_write
    assert Emails.get_field_annotation("type", Returned) == Returned.default
    assert Emails.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # email.primary
    assert Emails.get_field_root_type("primary") is bool
    assert not Emails.get_field_multiplicity("primary")
    assert (
        Emails.model_fields["primary"].description
        == "A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred mailing address or primary email address.  The primary attribute value 'True' MUST appear no more than once."
    )
    assert Emails.get_field_annotation("primary", Required) == Required.false
    assert Emails.get_field_annotation("primary", CaseExact) == CaseExact.false
    assert Emails.get_field_annotation("primary", Mutability) == Mutability.read_write
    assert Emails.get_field_annotation("primary", Returned) == Returned.default
    assert Emails.get_field_annotation("primary", Uniqueness) == Uniqueness.none

    # phone_numbers
    PhoneNumbers = User.get_field_root_type("phone_numbers")
    assert PhoneNumbers == User.PhoneNumbers
    assert issubclass(PhoneNumbers, MultiValuedComplexAttribute)
    assert User.get_field_multiplicity("phone_numbers")
    assert (
        User.model_fields["phone_numbers"].description
        == "Phone numbers for the User.  The value SHOULD be canonicalized by the service provider according to the format specified in RFC 3966, e.g., 'tel:+1-201-555-0123'. Canonical type values of 'work', 'home', 'mobile', 'fax', 'pager', and 'other'."
    )
    assert User.get_field_annotation("phone_numbers", Required) == Required.false
    assert User.get_field_annotation("phone_numbers", CaseExact) == CaseExact.false
    assert (
        User.get_field_annotation("phone_numbers", Mutability) == Mutability.read_write
    )
    assert User.get_field_annotation("phone_numbers", Returned) == Returned.default
    assert User.get_field_annotation("phone_numbers", Uniqueness) == Uniqueness.none

    # phone_number.value
    assert PhoneNumbers.get_field_root_type("value") is str
    assert not PhoneNumbers.get_field_multiplicity("value")
    assert PhoneNumbers.model_fields["value"].description == "Phone number of the User."
    assert PhoneNumbers.get_field_annotation("value", Required) == Required.false
    assert PhoneNumbers.get_field_annotation("value", CaseExact) == CaseExact.false
    assert (
        PhoneNumbers.get_field_annotation("value", Mutability) == Mutability.read_write
    )
    assert PhoneNumbers.get_field_annotation("value", Returned) == Returned.default
    assert PhoneNumbers.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # phone_number.display
    assert PhoneNumbers.get_field_root_type("display") is str
    assert not PhoneNumbers.get_field_multiplicity("display")
    assert (
        PhoneNumbers.model_fields["display"].description
        == "A human-readable name, primarily used for display purposes.  READ-ONLY."
    )
    assert PhoneNumbers.get_field_annotation("display", Required) == Required.false
    assert PhoneNumbers.get_field_annotation("display", CaseExact) == CaseExact.false
    assert (
        PhoneNumbers.get_field_annotation("display", Mutability)
        == Mutability.read_write
    )
    assert PhoneNumbers.get_field_annotation("display", Returned) == Returned.default
    assert PhoneNumbers.get_field_annotation("display", Uniqueness) == Uniqueness.none

    # phone_number.type
    assert PhoneNumbers.get_field_root_type("type") is str
    assert not PhoneNumbers.get_field_multiplicity("type")
    assert (
        PhoneNumbers.model_fields["type"].description
        == "A label indicating the attribute's function, e.g., 'work', 'home', 'mobile'."
    )
    assert PhoneNumbers.get_field_annotation("type", Required) == Required.false
    assert PhoneNumbers.get_field_annotation("type", CaseExact) == CaseExact.false
    assert PhoneNumbers.model_fields["type"].examples == [
        "work",
        "home",
        "mobile",
        "fax",
        "pager",
        "other",
    ]
    assert (
        PhoneNumbers.get_field_annotation("type", Mutability) == Mutability.read_write
    )
    assert PhoneNumbers.get_field_annotation("type", Returned) == Returned.default
    assert PhoneNumbers.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # phone_number.primary
    assert PhoneNumbers.get_field_root_type("primary") is bool
    assert not PhoneNumbers.get_field_multiplicity("primary")
    assert (
        PhoneNumbers.model_fields["primary"].description
        == "A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred phone number or primary phone number.  The primary attribute value 'True' MUST appear no more than once."
    )
    assert PhoneNumbers.get_field_annotation("primary", Required) == Required.false
    assert PhoneNumbers.get_field_annotation("primary", CaseExact) == CaseExact.false
    assert (
        PhoneNumbers.get_field_annotation("primary", Mutability)
        == Mutability.read_write
    )
    assert PhoneNumbers.get_field_annotation("primary", Returned) == Returned.default
    assert PhoneNumbers.get_field_annotation("primary", Uniqueness) == Uniqueness.none

    # ims
    Ims = User.get_field_root_type("ims")
    assert Ims == User.Ims
    assert issubclass(Ims, MultiValuedComplexAttribute)
    assert User.get_field_multiplicity("ims")
    assert (
        User.model_fields["ims"].description
        == "Instant messaging addresses for the User."
    )
    assert User.get_field_annotation("ims", Required) == Required.false
    assert User.get_field_annotation("ims", CaseExact) == CaseExact.false
    assert User.get_field_annotation("ims", Mutability) == Mutability.read_write
    assert User.get_field_annotation("ims", Returned) == Returned.default
    assert User.get_field_annotation("ims", Uniqueness) == Uniqueness.none

    # im.value
    assert Ims.get_field_root_type("value") is str
    assert not Ims.get_field_multiplicity("value")
    assert (
        Ims.model_fields["value"].description
        == "Instant messaging address for the User."
    )
    assert Ims.get_field_annotation("value", Required) == Required.false
    assert Ims.get_field_annotation("value", CaseExact) == CaseExact.false
    assert Ims.get_field_annotation("value", Mutability) == Mutability.read_write
    assert Ims.get_field_annotation("value", Returned) == Returned.default
    assert Ims.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # im.display
    assert Ims.get_field_root_type("display") is str
    assert not Ims.get_field_multiplicity("display")
    assert (
        Ims.model_fields["display"].description
        == "A human-readable name, primarily used for display purposes.  READ-ONLY."
    )
    assert Ims.get_field_annotation("display", Required) == Required.false
    assert Ims.get_field_annotation("display", CaseExact) == CaseExact.false
    assert Ims.get_field_annotation("display", Mutability) == Mutability.read_write
    assert Ims.get_field_annotation("display", Returned) == Returned.default
    assert Ims.get_field_annotation("display", Uniqueness) == Uniqueness.none

    # im.type
    assert Ims.get_field_root_type("type") is str
    assert not Ims.get_field_multiplicity("type")
    assert (
        Ims.model_fields["type"].description
        == "A label indicating the attribute's function, e.g., 'aim', 'gtalk', 'xmpp'."
    )
    assert Ims.get_field_annotation("type", Required) == Required.false
    assert Ims.get_field_annotation("type", CaseExact) == CaseExact.false
    assert Ims.model_fields["type"].examples == [
        "aim",
        "gtalk",
        "icq",
        "xmpp",
        "msn",
        "skype",
        "qq",
        "yahoo",
    ]
    assert Ims.get_field_annotation("type", Mutability) == Mutability.read_write
    assert Ims.get_field_annotation("type", Returned) == Returned.default
    assert Ims.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # im.primary
    assert Ims.get_field_root_type("primary") is bool
    assert not Ims.get_field_multiplicity("primary")
    assert (
        Ims.model_fields["primary"].description
        == "A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred messenger or primary messenger.  The primary attribute value 'True' MUST appear no more than once."
    )
    assert Ims.get_field_annotation("primary", Required) == Required.false
    assert Ims.get_field_annotation("primary", CaseExact) == CaseExact.false
    assert Ims.get_field_annotation("primary", Mutability) == Mutability.read_write
    assert Ims.get_field_annotation("primary", Returned) == Returned.default
    assert Ims.get_field_annotation("primary", Uniqueness) == Uniqueness.none

    # photos
    Photos = User.get_field_root_type("photos")
    assert Photos == User.Photos
    assert issubclass(Photos, MultiValuedComplexAttribute)
    assert User.get_field_multiplicity("photos")
    assert User.model_fields["photos"].description == "URLs of photos of the User."
    assert User.get_field_annotation("photos", Required) == Required.false
    assert User.get_field_annotation("photos", CaseExact) == CaseExact.false
    assert User.get_field_annotation("photos", Mutability) == Mutability.read_write
    assert User.get_field_annotation("photos", Returned) == Returned.default
    assert User.get_field_annotation("photos", Uniqueness) == Uniqueness.none

    # photo.value
    assert Photos.get_field_root_type("value") == Reference[ExternalReference]
    assert not Photos.get_field_multiplicity("value")
    assert Photos.model_fields["value"].description == "URL of a photo of the User."
    assert Photos.get_field_annotation("value", Required) == Required.false
    assert Photos.get_field_annotation("value", CaseExact) == CaseExact.true
    assert Photos.get_field_annotation("value", Mutability) == Mutability.read_write
    assert Photos.get_field_annotation("value", Returned) == Returned.default
    assert Photos.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # photo.display
    assert Photos.get_field_root_type("display") is str
    assert not Photos.get_field_multiplicity("display")
    assert (
        Photos.model_fields["display"].description
        == "A human-readable name, primarily used for display purposes.  READ-ONLY."
    )
    assert Photos.get_field_annotation("display", Required) == Required.false
    assert Photos.get_field_annotation("display", CaseExact) == CaseExact.false
    assert Photos.get_field_annotation("display", Mutability) == Mutability.read_write
    assert Photos.get_field_annotation("display", Returned) == Returned.default
    assert Photos.get_field_annotation("display", Uniqueness) == Uniqueness.none

    # photo.type
    assert Photos.get_field_root_type("type") is str
    assert not Photos.get_field_multiplicity("type")
    assert (
        Photos.model_fields["type"].description
        == "A label indicating the attribute's function, i.e., 'photo' or 'thumbnail'."
    )
    assert Photos.get_field_annotation("type", Required) == Required.false
    assert Photos.get_field_annotation("type", CaseExact) == CaseExact.false
    assert Photos.model_fields["type"].examples == ["photo", "thumbnail"]
    assert Photos.get_field_annotation("type", Mutability) == Mutability.read_write
    assert Photos.get_field_annotation("type", Returned) == Returned.default
    assert Photos.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # photo.primary
    assert Photos.get_field_root_type("primary") is bool
    assert not Photos.get_field_multiplicity("primary")
    assert (
        Photos.model_fields["primary"].description
        == "A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred photo or thumbnail.  The primary attribute value 'True' MUST appear no more than once."
    )
    assert Photos.get_field_annotation("primary", Required) == Required.false
    assert Photos.get_field_annotation("primary", CaseExact) == CaseExact.false
    assert Photos.get_field_annotation("primary", Mutability) == Mutability.read_write
    assert Photos.get_field_annotation("primary", Returned) == Returned.default
    assert Photos.get_field_annotation("primary", Uniqueness) == Uniqueness.none

    # addresses
    Addresses = User.get_field_root_type("addresses")
    assert Addresses == User.Addresses
    assert issubclass(Addresses, MultiValuedComplexAttribute)
    assert User.get_field_multiplicity("addresses")
    assert (
        User.model_fields["addresses"].description
        == "A physical mailing address for this User. Canonical type values of 'work', 'home', and 'other'.  This attribute is a complex type with the following sub-attributes."
    )
    assert User.get_field_annotation("addresses", Required) == Required.false
    assert User.get_field_annotation("addresses", CaseExact) == CaseExact.false
    assert User.get_field_annotation("addresses", Mutability) == Mutability.read_write
    assert User.get_field_annotation("addresses", Returned) == Returned.default
    assert User.get_field_annotation("addresses", Uniqueness) == Uniqueness.none

    # address.formatted
    assert Addresses.get_field_root_type("formatted") is str
    assert not Addresses.get_field_multiplicity("formatted")
    assert (
        Addresses.model_fields["formatted"].description
        == "The full mailing address, formatted for display or use with a mailing label.  This attribute MAY contain newlines."
    )
    assert Addresses.get_field_annotation("formatted", Required) == Required.false
    assert Addresses.get_field_annotation("formatted", CaseExact) == CaseExact.false
    assert (
        Addresses.get_field_annotation("formatted", Mutability) == Mutability.read_write
    )
    assert Addresses.get_field_annotation("formatted", Returned) == Returned.default
    assert Addresses.get_field_annotation("formatted", Uniqueness) == Uniqueness.none

    # address.street_address
    assert Addresses.get_field_root_type("street_address") is str
    assert not Addresses.get_field_multiplicity("street_address")
    assert (
        Addresses.model_fields["street_address"].description
        == "The full street address component, which may include house number, street name, P.O. box, and multi-line extended street address information.  This attribute MAY contain newlines."
    )
    assert Addresses.get_field_annotation("street_address", Required) == Required.false
    assert (
        Addresses.get_field_annotation("street_address", CaseExact) == CaseExact.false
    )
    assert (
        Addresses.get_field_annotation("street_address", Mutability)
        == Mutability.read_write
    )
    assert (
        Addresses.get_field_annotation("street_address", Returned) == Returned.default
    )
    assert (
        Addresses.get_field_annotation("street_address", Uniqueness) == Uniqueness.none
    )

    # address.locality
    assert Addresses.get_field_root_type("locality") is str
    assert not Addresses.get_field_multiplicity("locality")
    assert (
        Addresses.model_fields["locality"].description
        == "The city or locality component."
    )
    assert Addresses.get_field_annotation("locality", Required) == Required.false
    assert Addresses.get_field_annotation("locality", CaseExact) == CaseExact.false
    assert (
        Addresses.get_field_annotation("locality", Mutability) == Mutability.read_write
    )
    assert Addresses.get_field_annotation("locality", Returned) == Returned.default
    assert Addresses.get_field_annotation("locality", Uniqueness) == Uniqueness.none

    # address.region
    assert Addresses.get_field_root_type("region") is str
    assert not Addresses.get_field_multiplicity("region")
    assert (
        Addresses.model_fields["region"].description == "The state or region component."
    )
    assert Addresses.get_field_annotation("region", Required) == Required.false
    assert Addresses.get_field_annotation("region", CaseExact) == CaseExact.false
    assert Addresses.get_field_annotation("region", Mutability) == Mutability.read_write
    assert Addresses.get_field_annotation("region", Returned) == Returned.default
    assert Addresses.get_field_annotation("region", Uniqueness) == Uniqueness.none

    # address.postal_code
    assert Addresses.get_field_root_type("postal_code") is str
    assert not Addresses.get_field_multiplicity("postal_code")
    assert (
        Addresses.model_fields["postal_code"].description
        == "The zip code or postal code component."
    )
    assert Addresses.get_field_annotation("postal_code", Required) == Required.false
    assert Addresses.get_field_annotation("postal_code", CaseExact) == CaseExact.false
    assert (
        Addresses.get_field_annotation("postal_code", Mutability)
        == Mutability.read_write
    )
    assert Addresses.get_field_annotation("postal_code", Returned) == Returned.default
    assert Addresses.get_field_annotation("postal_code", Uniqueness) == Uniqueness.none

    # address.country
    assert Addresses.get_field_root_type("country") is str
    assert not Addresses.get_field_multiplicity("country")
    assert (
        Addresses.model_fields["country"].description == "The country name component."
    )
    assert Addresses.get_field_annotation("country", Required) == Required.false
    assert Addresses.get_field_annotation("country", CaseExact) == CaseExact.false
    assert (
        Addresses.get_field_annotation("country", Mutability) == Mutability.read_write
    )
    assert Addresses.get_field_annotation("country", Returned) == Returned.default
    assert Addresses.get_field_annotation("country", Uniqueness) == Uniqueness.none

    # address.type
    assert Addresses.get_field_root_type("type") is str
    assert not Addresses.get_field_multiplicity("type")
    assert (
        Addresses.model_fields["type"].description
        == "A label indicating the attribute's function, e.g., 'work' or 'home'."
    )
    assert Addresses.get_field_annotation("type", Required) == Required.false
    assert Addresses.get_field_annotation("type", CaseExact) == CaseExact.false
    assert Addresses.model_fields["type"].examples == ["work", "home", "other"]
    assert Addresses.get_field_annotation("type", Mutability) == Mutability.read_write
    assert Addresses.get_field_annotation("type", Returned) == Returned.default
    assert Addresses.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # address.primary
    assert Addresses.get_field_root_type("primary") is bool
    assert not Addresses.get_field_multiplicity("primary")
    assert (
        Addresses.model_fields["primary"].description
        == "A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred mailing address or primary email address.  The primary attribute value 'True' MUST appear no more than once."
    )
    assert Addresses.get_field_annotation("primary", Required) == Required.false
    assert Addresses.get_field_annotation("primary", CaseExact) == CaseExact.false
    assert (
        Addresses.get_field_annotation("primary", Mutability) == Mutability.read_write
    )
    assert Addresses.get_field_annotation("primary", Returned) == Returned.default
    assert Addresses.get_field_annotation("primary", Uniqueness) == Uniqueness.none

    # groups
    Groups = User.get_field_root_type("groups")
    assert Groups == User.Groups
    assert issubclass(Groups, MultiValuedComplexAttribute)
    assert User.get_field_multiplicity("groups")
    assert (
        User.model_fields["groups"].description
        == "A list of groups to which the user belongs, either through direct membership, through nested groups, or dynamically calculated."
    )
    assert User.get_field_annotation("groups", Required) == Required.false
    assert User.get_field_annotation("groups", CaseExact) == CaseExact.false
    assert User.get_field_annotation("groups", Mutability) == Mutability.read_only
    assert User.get_field_annotation("groups", Returned) == Returned.default
    assert User.get_field_annotation("groups", Uniqueness) == Uniqueness.none

    # group.value
    assert Groups.get_field_root_type("value") is str
    assert not Groups.get_field_multiplicity("value")
    assert (
        Groups.model_fields["value"].description
        == "The identifier of the User's group."
    )
    assert Groups.get_field_annotation("value", Required) == Required.false
    assert Groups.get_field_annotation("value", CaseExact) == CaseExact.false
    assert Groups.get_field_annotation("value", Mutability) == Mutability.read_only
    assert Groups.get_field_annotation("value", Returned) == Returned.default
    assert Groups.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # group.ref
    assert (
        Groups.get_field_root_type("ref")
        == Reference[Union[Literal["User"], Literal["Group"]]]
    )
    assert not Groups.get_field_multiplicity("ref")
    assert (
        Groups.model_fields["ref"].description
        == "The URI of the corresponding 'Group' resource to which the user belongs."
    )
    assert Groups.get_field_annotation("ref", Required) == Required.false
    assert Groups.get_field_annotation("ref", CaseExact) == CaseExact.false
    assert Groups.get_field_annotation("ref", Mutability) == Mutability.read_only
    assert Groups.get_field_annotation("ref", Returned) == Returned.default
    assert Groups.get_field_annotation("ref", Uniqueness) == Uniqueness.none

    # group.display
    assert Groups.get_field_root_type("display") is str
    assert not Groups.get_field_multiplicity("display")
    assert (
        Groups.model_fields["display"].description
        == "A human-readable name, primarily used for display purposes.  READ-ONLY."
    )
    assert Groups.get_field_annotation("display", Required) == Required.false
    assert Groups.get_field_annotation("display", CaseExact) == CaseExact.false
    assert Groups.get_field_annotation("display", Mutability) == Mutability.read_only
    assert Groups.get_field_annotation("display", Returned) == Returned.default
    assert Groups.get_field_annotation("display", Uniqueness) == Uniqueness.none

    # group.type
    assert Groups.get_field_root_type("type") is str
    assert not Groups.get_field_multiplicity("type")
    assert (
        Groups.model_fields["type"].description
        == "A label indicating the attribute's function, e.g., 'direct' or 'indirect'."
    )
    assert Groups.get_field_annotation("type", Required) == Required.false
    assert Groups.get_field_annotation("type", CaseExact) == CaseExact.false
    assert Groups.model_fields["type"].examples == [
        "direct",
        "indirect",
    ]
    assert Groups.get_field_annotation("type", Mutability) == Mutability.read_only
    assert Groups.get_field_annotation("type", Returned) == Returned.default
    assert Groups.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # entitlements
    Entitlements = User.get_field_root_type("entitlements")
    assert Entitlements == User.Entitlements
    assert issubclass(Entitlements, MultiValuedComplexAttribute)
    assert User.get_field_multiplicity("entitlements")
    assert (
        User.model_fields["entitlements"].description
        == "A list of entitlements for the User that represent a thing the User has."
    )
    assert User.get_field_annotation("entitlements", Required) == Required.false
    assert User.get_field_annotation("entitlements", CaseExact) == CaseExact.false
    assert (
        User.get_field_annotation("entitlements", Mutability) == Mutability.read_write
    )
    assert User.get_field_annotation("entitlements", Returned) == Returned.default
    assert User.get_field_annotation("entitlements", Uniqueness) == Uniqueness.none

    # entitlement.value
    assert Entitlements.get_field_root_type("value") is str
    assert not Entitlements.get_field_multiplicity("value")
    assert (
        Entitlements.model_fields["value"].description == "The value of an entitlement."
    )
    assert Entitlements.get_field_annotation("value", Required) == Required.false
    assert Entitlements.get_field_annotation("value", CaseExact) == CaseExact.false
    assert (
        Entitlements.get_field_annotation("value", Mutability) == Mutability.read_write
    )
    assert Entitlements.get_field_annotation("value", Returned) == Returned.default
    assert Entitlements.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # entitlement.display
    assert Entitlements.get_field_root_type("display") is str
    assert not Entitlements.get_field_multiplicity("display")
    assert (
        Entitlements.model_fields["display"].description
        == "A human-readable name, primarily used for display purposes.  READ-ONLY."
    )
    assert Entitlements.get_field_annotation("display", Required) == Required.false
    assert Entitlements.get_field_annotation("display", CaseExact) == CaseExact.false
    assert (
        Entitlements.get_field_annotation("display", Mutability)
        == Mutability.read_write
    )
    assert Entitlements.get_field_annotation("display", Returned) == Returned.default
    assert Entitlements.get_field_annotation("display", Uniqueness) == Uniqueness.none

    # entitlement.type
    assert Entitlements.get_field_root_type("type") is str
    assert not Entitlements.get_field_multiplicity("type")
    assert (
        Entitlements.model_fields["type"].description
        == "A label indicating the attribute's function."
    )
    assert Entitlements.get_field_annotation("type", Required) == Required.false
    assert Entitlements.get_field_annotation("type", CaseExact) == CaseExact.false
    assert (
        Entitlements.get_field_annotation("type", Mutability) == Mutability.read_write
    )
    assert Entitlements.get_field_annotation("type", Returned) == Returned.default
    assert Entitlements.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # entitlement.primary
    assert Entitlements.get_field_root_type("primary") is bool
    assert not Entitlements.get_field_multiplicity("primary")
    assert (
        Entitlements.model_fields["primary"].description
        == "A Boolean value indicating the 'primary' or preferred attribute value for this attribute.  The primary attribute value 'True' MUST appear no more than once."
    )
    assert Entitlements.get_field_annotation("primary", Required) == Required.false
    assert Entitlements.get_field_annotation("primary", CaseExact) == CaseExact.false
    assert (
        Entitlements.get_field_annotation("primary", Mutability)
        == Mutability.read_write
    )
    assert Entitlements.get_field_annotation("primary", Returned) == Returned.default
    assert Entitlements.get_field_annotation("primary", Uniqueness) == Uniqueness.none

    # roles
    Roles = User.get_field_root_type("roles")
    assert Roles == User.Roles
    assert issubclass(Roles, MultiValuedComplexAttribute)
    assert User.get_field_multiplicity("roles")
    assert (
        User.model_fields["roles"].description
        == "A list of roles for the User that collectively represent who the User is, e.g., 'Student', 'Faculty'."
    )
    assert User.get_field_annotation("roles", Required) == Required.false
    assert User.get_field_annotation("roles", CaseExact) == CaseExact.false
    assert User.get_field_annotation("roles", Mutability) == Mutability.read_write
    assert User.get_field_annotation("roles", Returned) == Returned.default
    assert User.get_field_annotation("roles", Uniqueness) == Uniqueness.none

    # role.value
    assert Roles.get_field_root_type("value") is str
    assert not Roles.get_field_multiplicity("value")
    assert Roles.model_fields["value"].description == "The value of a role."
    assert Roles.get_field_annotation("value", Required) == Required.false
    assert Roles.get_field_annotation("value", CaseExact) == CaseExact.false
    assert Roles.get_field_annotation("value", Mutability) == Mutability.read_write
    assert Roles.get_field_annotation("value", Returned) == Returned.default
    assert Roles.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # role.display
    assert Roles.get_field_root_type("display") is str
    assert not Roles.get_field_multiplicity("display")
    assert (
        Roles.model_fields["display"].description
        == "A human-readable name, primarily used for display purposes.  READ-ONLY."
    )
    assert Roles.get_field_annotation("display", Required) == Required.false
    assert Roles.get_field_annotation("display", CaseExact) == CaseExact.false
    assert Roles.get_field_annotation("display", Mutability) == Mutability.read_write
    assert Roles.get_field_annotation("display", Returned) == Returned.default
    assert Roles.get_field_annotation("display", Uniqueness) == Uniqueness.none

    # role.type
    assert Roles.get_field_root_type("type") is str
    assert not Roles.get_field_multiplicity("type")
    assert (
        Roles.model_fields["type"].description
        == "A label indicating the attribute's function."
    )
    assert Roles.get_field_annotation("type", Required) == Required.false
    assert Roles.get_field_annotation("type", CaseExact) == CaseExact.false
    assert Roles.get_field_annotation("type", Mutability) == Mutability.read_write
    assert Roles.get_field_annotation("type", Returned) == Returned.default
    assert Roles.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # role.primary
    assert Roles.get_field_root_type("primary") is bool
    assert not Roles.get_field_multiplicity("primary")
    assert (
        Roles.model_fields["primary"].description
        == "A Boolean value indicating the 'primary' or preferred attribute value for this attribute.  The primary attribute value 'True' MUST appear no more than once."
    )
    assert Roles.get_field_annotation("primary", Required) == Required.false
    assert Roles.get_field_annotation("primary", CaseExact) == CaseExact.false
    assert Roles.get_field_annotation("primary", Mutability) == Mutability.read_write
    assert Roles.get_field_annotation("primary", Returned) == Returned.default
    assert Roles.get_field_annotation("primary", Uniqueness) == Uniqueness.none

    # x_509_certificates
    X509Certificates = User.get_field_root_type("x_509_certificates")
    assert X509Certificates == User.X509Certificates
    assert issubclass(X509Certificates, MultiValuedComplexAttribute)
    assert User.get_field_multiplicity("x_509_certificates")
    assert (
        User.model_fields["x_509_certificates"].description
        == "A list of certificates issued to the User."
    )
    assert User.get_field_annotation("x_509_certificates", Required) == Required.false
    assert User.get_field_annotation("x_509_certificates", CaseExact) == CaseExact.false
    assert (
        User.get_field_annotation("x_509_certificates", Mutability)
        == Mutability.read_write
    )
    assert User.get_field_annotation("x_509_certificates", Returned) == Returned.default
    assert (
        User.get_field_annotation("x_509_certificates", Uniqueness) == Uniqueness.none
    )

    # x_509_certificate.value
    assert X509Certificates.get_field_root_type("value") is Base64Bytes
    assert not X509Certificates.get_field_multiplicity("value")
    assert (
        X509Certificates.model_fields["value"].description
        == "The value of an X.509 certificate."
    )
    assert X509Certificates.get_field_annotation("value", Required) == Required.false
    assert X509Certificates.get_field_annotation("value", CaseExact) == CaseExact.true
    assert (
        X509Certificates.get_field_annotation("value", Mutability)
        == Mutability.read_write
    )
    assert X509Certificates.get_field_annotation("value", Returned) == Returned.default
    assert X509Certificates.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # x_509_certificate.display
    assert X509Certificates.get_field_root_type("display") is str
    assert not X509Certificates.get_field_multiplicity("display")
    assert (
        X509Certificates.model_fields["display"].description
        == "A human-readable name, primarily used for display purposes.  READ-ONLY."
    )
    assert X509Certificates.get_field_annotation("display", Required) == Required.false
    assert (
        X509Certificates.get_field_annotation("display", CaseExact) == CaseExact.false
    )
    assert (
        X509Certificates.get_field_annotation("display", Mutability)
        == Mutability.read_write
    )
    assert (
        X509Certificates.get_field_annotation("display", Returned) == Returned.default
    )
    assert (
        X509Certificates.get_field_annotation("display", Uniqueness) == Uniqueness.none
    )

    # x_509_certificate.type
    assert X509Certificates.get_field_root_type("type") is str
    assert not X509Certificates.get_field_multiplicity("type")
    assert (
        X509Certificates.model_fields["type"].description
        == "A label indicating the attribute's function."
    )
    assert X509Certificates.get_field_annotation("type", Required) == Required.false
    assert X509Certificates.get_field_annotation("type", CaseExact) == CaseExact.false
    assert (
        X509Certificates.get_field_annotation("type", Mutability)
        == Mutability.read_write
    )
    assert X509Certificates.get_field_annotation("type", Returned) == Returned.default
    assert X509Certificates.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # x_509_certificate.primary
    assert X509Certificates.get_field_root_type("primary") is bool
    assert not X509Certificates.get_field_multiplicity("primary")
    assert (
        X509Certificates.model_fields["primary"].description
        == "A Boolean value indicating the 'primary' or preferred attribute value for this attribute.  The primary attribute value 'True' MUST appear no more than once."
    )
    assert X509Certificates.get_field_annotation("primary", Required) == Required.false
    assert (
        X509Certificates.get_field_annotation("primary", CaseExact) == CaseExact.false
    )
    assert (
        X509Certificates.get_field_annotation("primary", Mutability)
        == Mutability.read_write
    )
    assert (
        X509Certificates.get_field_annotation("primary", Returned) == Returned.default
    )
    assert (
        X509Certificates.get_field_annotation("primary", Uniqueness) == Uniqueness.none
    )

    payload = load_sample("rfc7643-8.2-user-full.json")
    obj = User.model_validate(payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:User"]
    assert obj.id == "2819c223-7f76-453a-919d-413861904646"
    assert obj.external_id == "701984"
    assert obj.user_name == "bjensen@example.com"
    assert obj.name
    assert obj.name.formatted == "Ms. Barbara J Jensen, III"
    assert obj.name.family_name == "Jensen"
    assert obj.name.given_name == "Barbara"
    assert obj.name.middle_name == "Jane"
    assert obj.name.honorific_prefix == "Ms."
    assert obj.name.honorific_suffix == "III"
    assert obj.display_name == "Babs Jensen"
    assert obj.nick_name == "Babs"
    assert obj.profile_url == Reference("https://login.example.com/bjensen")
    assert obj.emails[0].value == "bjensen@example.com"
    assert obj.emails[0].type == "work"
    assert obj.emails[0].primary is True
    assert obj.emails[1].value == "babs@jensen.org"
    assert obj.emails[1].type == "home"
    assert obj.addresses[0].type == "work"
    assert obj.addresses[0].street_address == "100 Universal City Plaza"
    assert obj.addresses[0].locality == "Hollywood"
    assert obj.addresses[0].region == "CA"
    assert obj.addresses[0].postal_code == "91608"
    assert obj.addresses[0].country == "USA"
    assert (
        obj.addresses[0].formatted
        == "100 Universal City Plaza\nHollywood, CA 91608 USA"
    )
    assert obj.addresses[0].primary is True
    assert obj.addresses[1].type == "home"
    assert obj.addresses[1].street_address == "456 Hollywood Blvd"
    assert obj.addresses[1].locality == "Hollywood"
    assert obj.addresses[1].region == "CA"
    assert obj.addresses[1].postal_code == "91608"
    assert obj.addresses[1].country == "USA"
    assert obj.addresses[1].formatted == "456 Hollywood Blvd\nHollywood, CA 91608 USA"
    assert obj.phone_numbers[0].value == "555-555-5555"
    assert obj.phone_numbers[0].type == "work"
    assert obj.phone_numbers[1].value == "555-555-4444"
    assert obj.phone_numbers[1].type == "mobile"
    assert obj.ims[0].value == "someaimhandle"
    assert obj.ims[0].type == "aim"
    assert obj.photos[0].value == Reference(
        "https://photos.example.com/profilephoto/72930000000Ccne/F"
    )
    assert obj.photos[0].type == "photo"
    assert obj.photos[1].value == Reference(
        "https://photos.example.com/profilephoto/72930000000Ccne/T"
    )
    assert obj.photos[1].type == "thumbnail"
    assert obj.user_type == "Employee"
    assert obj.title == "Tour Guide"
    assert obj.preferred_language == "en-US"
    assert obj.locale == "en-US"
    assert obj.timezone == "America/Los_Angeles"
    assert obj.active is True
    assert obj.password == "t1meMa$heen"
    assert obj.groups[0].value == "e9e30dba-f08f-4109-8486-d5c6a331660a"
    assert obj.groups[0].ref == Reference(
        "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a"
    )
    assert obj.groups[0].display == "Tour Guides"
    assert obj.groups[1].value == "fc348aa8-3835-40eb-a20b-c726e15c55b5"
    assert obj.groups[1].ref == Reference(
        "https://example.com/v2/Groups/fc348aa8-3835-40eb-a20b-c726e15c55b5"
    )
    assert obj.groups[1].display == "Employees"
    assert obj.groups[2].value == "71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7"
    assert obj.groups[2].ref == Reference(
        "https://example.com/v2/Groups/71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7"
    )
    assert obj.groups[2].display == "US Employees"
    assert obj.x_509_certificates[0].value == (
        b"0\x82\x03C0\x82\x02\xac\xa0\x03\x02\x01\x02\x02\x02\x10\x000\r\x06\t*\x86H\x86\xf7\r\x01\x01\x05\x05\x000N1\x0b0\t\x06\x03U\x04\x06\x13\x02US1\x130\x11\x06\x03U\x04\x08\x0c\nCalifornia1\x140\x12\x06\x03U\x04\n\x0c\x0bexample.com1\x140\x12\x06\x03U\x04\x03\x0c\x0bexample.com0\x1e\x17\r111022062431Z\x17\r121004062431Z0\x7f1\x0b0\t\x06\x03U\x04\x06\x13\x02US1\x130\x11\x06\x03U\x04\x08\x0c\nCalifornia1\x140\x12\x06\x03U\x04\n\x0c\x0bexample.com1!0\x1f\x06\x03U\x04\x03\x0c\x18Ms. Barbara J Jensen III1\"0 \x06\t*\x86H\x86\xf7\r\x01\t\x01\x16\x13bjensen@example.com0\x82\x01\"0\r\x06\t*\x86H\x86\xf7\r\x01\x01\x01\x05\x00\x03\x82\x01\x0f\x000\x82\x01\n\x02\x82\x01\x01\x00\xec\xaa\xfe\r\xc7l\xfc\x949\x1b\x07\xa3$W\x01 \xfe\xbc\xd9}\xf1\xa68\xac\xe7\xa0\n\xd3f\xdc\xd4R\xe0\xcd\xd2\xc8\xf1\xab\xa8G\xe7\x02\xf7\xf5k\x87\x9bz\xe8y\x10 \xe7@\xe2\xe9\xc7\x87@\x1ag\x8cK\xe4\xf8Umr\x0f0\x1eo\x00\xf2\xa9\xcf>b=(\xbc\xc4\xef\x12/\xb2;H8\\\x05Ra\xa9Z\xab\xdcx%\x94A\xbaP)Cts\xbb\x9eB\xee\xc1z\xbc\x1d\xc2\x12*F\xd3\xe5aSU\xf1Y\xce'O\x97\xc1\xd9\xec8W\x91\x92\x11\xb4\x9c\x01\xc1\xea\xb8n\xf9\xb7\x84\xcdN\xb3\xb5\x10\x1fNYK\xa7\x15\x0e\x0c\x1e(\xdc\x1d,\xba\xd3\xe7X\xa4I\x01\xb7\r\x8a\xe5\xf9\xfb{\xf3U\x10D\x8a\xb1\x83\n\x82}q.\x0e(\xa7>\x1d$\x92\xf2\"\xe68\xafV\xedY\xf5\x08\xb0\x95\x81\x1dE\xb2\xc9\xe32P\x06`\xebHd\xccb~%E\xcd\x87\x80s\xb8\x0e\xa0\x7fns\x15\xa2\xb1\xc1\xd0 \xba\x01]P\xa0R\xb8\x18\xf7\xb5/\x02\x03\x01\x00\x01\xa3{0y0\t\x06\x03U\x1d\x13\x04\x020\x000,\x06\t`\x86H\x01\x86\xf8B\x01\r\x04\x1f\x16\x1dOpenSSL Generated Certificate0\x1d\x06\x03U\x1d\x0e\x04\x16\x04\x14\xf2\x90\xf4SK\xecd\x8b\x1a\x03^\xa5/\xc1'\xf1\xbct\x17\xf80\x1f\x06\x03U\x1d#\x04\x180\x16\x80\x14tg\x8a\x8a\xd7\x1a\x17\xb8'\xce\xc3p\x0f\x1e\xf4\xf2J\x9aV\xdd0\r\x06\t*\x86H\x86\xf7\r\x01\x01\x05\x05\x00\x03\x81\x81\x00\x03\xcdR\xb0Y\xceu\x82m6\x0eSr\xaf\xbf\x07!\x03\xac\x18'\xba\xcct\x8eZ\x14\x84\x1c\x8f0Ed\xa0\xc6w'\xb8\xf5f\x02<\xac\x06\xce\x90\xd9\xe0_\xcf\xa9)\xf4\xe2\x0f=Q\x0b\x8f\x9d\xc7\xca\x14\xe9\x96\xbe\xe0\xd2WR9K\xe4+\xd5\xe8\x11\x18o_\x90\x00Bp\x8a\xd4\xd5\xbf\x10\x7f\x03\xae\xe0\xe3o\xef\xce\x00-\xa1\x15\x1e\x0e\x8b\xf5\xf8ab\x05\x9f\x864_\xdc\x01\x82\x9c2\xd1\x9c\xae\xcd\xa2\xf7\xb6d$\xca"
    )
    assert obj.meta.resource_type == "User"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.last_modified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"a330bc54f0671c9"'
    assert (
        obj.meta.location
        == "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    )


def test_make_enterprise_user_model_from_schema(load_sample):
    payload = load_sample("rfc7643-8.7.1-schema-enterprise_user.json")
    schema = Schema.model_validate(payload)
    EnterpriseUser = Extension.from_schema(schema)

    assert EnterpriseUser.model_fields["schemas"].default == [
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    ]

    # employee_number
    assert EnterpriseUser.get_field_root_type("employee_number") is str
    assert not EnterpriseUser.get_field_multiplicity("employee_number")
    assert (
        EnterpriseUser.model_fields["employee_number"].description
        == "Numeric or alphanumeric identifier assigned to a person, typically based on order of hire or association with an organization."
    )
    assert (
        EnterpriseUser.get_field_annotation("employee_number", Required)
        == Required.false
    )
    assert (
        EnterpriseUser.get_field_annotation("employee_number", CaseExact)
        == CaseExact.false
    )
    assert (
        EnterpriseUser.get_field_annotation("employee_number", Mutability)
        == Mutability.read_write
    )
    assert (
        EnterpriseUser.get_field_annotation("employee_number", Returned)
        == Returned.default
    )
    assert (
        EnterpriseUser.get_field_annotation("employee_number", Uniqueness)
        == Uniqueness.none
    )

    # cost_center
    assert EnterpriseUser.get_field_root_type("cost_center") is str
    assert not EnterpriseUser.get_field_multiplicity("cost_center")
    assert (
        EnterpriseUser.model_fields["cost_center"].description
        == "Identifies the name of a cost center."
    )
    assert (
        EnterpriseUser.get_field_annotation("cost_center", Required) == Required.false
    )
    assert (
        EnterpriseUser.get_field_annotation("cost_center", CaseExact) == CaseExact.false
    )
    assert (
        EnterpriseUser.get_field_annotation("cost_center", Mutability)
        == Mutability.read_write
    )
    assert (
        EnterpriseUser.get_field_annotation("cost_center", Returned) == Returned.default
    )
    assert (
        EnterpriseUser.get_field_annotation("cost_center", Uniqueness)
        == Uniqueness.none
    )

    # organization
    assert EnterpriseUser.get_field_root_type("organization") is str
    assert not EnterpriseUser.get_field_multiplicity("organization")
    assert (
        EnterpriseUser.model_fields["organization"].description
        == "Identifies the name of an organization."
    )
    assert (
        EnterpriseUser.get_field_annotation("organization", Required) == Required.false
    )
    assert (
        EnterpriseUser.get_field_annotation("organization", CaseExact)
        == CaseExact.false
    )
    assert (
        EnterpriseUser.get_field_annotation("organization", Mutability)
        == Mutability.read_write
    )
    assert (
        EnterpriseUser.get_field_annotation("organization", Returned)
        == Returned.default
    )
    assert (
        EnterpriseUser.get_field_annotation("organization", Uniqueness)
        == Uniqueness.none
    )

    # division
    assert EnterpriseUser.get_field_root_type("division") is str
    assert not EnterpriseUser.get_field_multiplicity("division")
    assert (
        EnterpriseUser.model_fields["division"].description
        == "Identifies the name of a division."
    )
    assert EnterpriseUser.get_field_annotation("division", Required) == Required.false
    assert EnterpriseUser.get_field_annotation("division", CaseExact) == CaseExact.false
    assert (
        EnterpriseUser.get_field_annotation("division", Mutability)
        == Mutability.read_write
    )
    assert EnterpriseUser.get_field_annotation("division", Returned) == Returned.default
    assert (
        EnterpriseUser.get_field_annotation("division", Uniqueness) == Uniqueness.none
    )

    # department
    assert EnterpriseUser.get_field_root_type("department") is str
    assert not EnterpriseUser.get_field_multiplicity("department")
    assert (
        EnterpriseUser.model_fields["department"].description
        == "Identifies the name of a department."
    )
    assert EnterpriseUser.get_field_annotation("department", Required) == Required.false
    assert (
        EnterpriseUser.get_field_annotation("department", CaseExact) == CaseExact.false
    )
    assert (
        EnterpriseUser.get_field_annotation("department", Mutability)
        == Mutability.read_write
    )
    assert (
        EnterpriseUser.get_field_annotation("department", Returned) == Returned.default
    )
    assert (
        EnterpriseUser.get_field_annotation("department", Uniqueness) == Uniqueness.none
    )

    # manager
    Manager = EnterpriseUser.get_field_root_type("manager")
    assert Manager == EnterpriseUser.Manager
    assert issubclass(Manager, ComplexAttribute)
    assert not EnterpriseUser.get_field_multiplicity("manager")
    assert (
        EnterpriseUser.model_fields["manager"].description
        == "The User's manager.  A complex type that optionally allows service providers to represent organizational hierarchy by referencing the 'id' attribute of another User."
    )
    assert EnterpriseUser.get_field_annotation("manager", Required) == Required.false
    assert EnterpriseUser.get_field_annotation("manager", CaseExact) == CaseExact.false
    assert (
        EnterpriseUser.get_field_annotation("manager", Mutability)
        == Mutability.read_write
    )
    assert EnterpriseUser.get_field_annotation("manager", Returned) == Returned.default
    assert EnterpriseUser.get_field_annotation("manager", Uniqueness) == Uniqueness.none

    # Manager.value
    assert Manager.get_field_root_type("value") is str
    assert not Manager.get_field_multiplicity("value")
    assert (
        Manager.model_fields["value"].description
        == "The id of the SCIM resource representing the User's manager.  REQUIRED."
    )
    assert Manager.get_field_annotation("value", Required) == Required.true
    assert Manager.get_field_annotation("value", CaseExact) == CaseExact.false
    assert Manager.get_field_annotation("value", Mutability) == Mutability.read_write
    assert Manager.get_field_annotation("value", Returned) == Returned.default
    assert Manager.get_field_annotation("value", Uniqueness) == Uniqueness.none

    # Manager.ref
    assert Manager.get_field_root_type("ref") == Reference[Literal["User"]]
    assert not Manager.get_field_multiplicity("ref")
    assert (
        Manager.model_fields["ref"].description
        == "The URI of the SCIM resource representing the User's manager.  REQUIRED."
    )
    assert Manager.get_field_annotation("ref", Required) == Required.true
    assert Manager.get_field_annotation("ref", CaseExact) == CaseExact.false
    assert Manager.get_field_annotation("ref", Mutability) == Mutability.read_write
    assert Manager.get_field_annotation("ref", Returned) == Returned.default
    assert Manager.get_field_annotation("ref", Uniqueness) == Uniqueness.none

    # Manager.display_name
    assert Manager.get_field_root_type("display_name") is str
    assert not Manager.get_field_multiplicity("display_name")
    assert (
        Manager.model_fields["display_name"].description
        == "The displayName of the User's manager. OPTIONAL and READ-ONLY."
    )
    assert Manager.get_field_annotation("display_name", Required) == Required.false
    assert Manager.get_field_annotation("display_name", CaseExact) == CaseExact.false
    assert (
        Manager.get_field_annotation("display_name", Mutability) == Mutability.read_only
    )
    assert Manager.get_field_annotation("display_name", Returned) == Returned.default
    assert Manager.get_field_annotation("display_name", Uniqueness) == Uniqueness.none


def test_make_resource_type_model_from_schema(load_sample):
    payload = load_sample("rfc7643-8.7.2-schema-resource_type.json")
    schema = Schema.model_validate(payload)
    ResourceType = Resource.from_schema(schema)

    assert ResourceType.model_fields["schemas"].default == [
        "urn:ietf:params:scim:schemas:core:2.0:ResourceType"
    ]

    # id
    assert ResourceType.get_field_root_type("id") is str
    assert not ResourceType.get_field_multiplicity("id")
    assert (
        ResourceType.model_fields["id"].description
        == "The resource type's server unique id. May be the same as the 'name' attribute."
    )
    assert ResourceType.get_field_annotation("id", Required) == Required.false
    assert ResourceType.get_field_annotation("id", CaseExact) == CaseExact.false
    assert ResourceType.get_field_annotation("id", Mutability) == Mutability.read_only
    assert ResourceType.get_field_annotation("id", Returned) == Returned.default
    assert ResourceType.get_field_annotation("id", Uniqueness) == Uniqueness.none

    # name
    assert ResourceType.get_field_root_type("name") is str
    assert not ResourceType.get_field_multiplicity("name")
    assert (
        ResourceType.model_fields["name"].description
        == "The resource type name.  When applicable, service providers MUST specify the name, e.g., 'User'."
    )
    assert ResourceType.get_field_annotation("name", Required) == Required.true
    assert ResourceType.get_field_annotation("name", CaseExact) == CaseExact.false
    assert ResourceType.get_field_annotation("name", Mutability) == Mutability.read_only
    assert ResourceType.get_field_annotation("name", Returned) == Returned.default
    assert ResourceType.get_field_annotation("name", Uniqueness) == Uniqueness.none

    # description
    assert ResourceType.get_field_root_type("description") is str
    assert not ResourceType.get_field_multiplicity("description")
    assert (
        ResourceType.model_fields["description"].description
        == "The resource type's human-readable description.  When applicable, service providers MUST specify the description."
    )
    assert ResourceType.get_field_annotation("description", Required) == Required.false
    assert (
        ResourceType.get_field_annotation("description", CaseExact) == CaseExact.false
    )
    assert (
        ResourceType.get_field_annotation("description", Mutability)
        == Mutability.read_only
    )
    assert (
        ResourceType.get_field_annotation("description", Returned) == Returned.default
    )
    assert (
        ResourceType.get_field_annotation("description", Uniqueness) == Uniqueness.none
    )

    # endpoint
    assert ResourceType.get_field_root_type("endpoint") == Reference[URIReference]
    assert not ResourceType.get_field_multiplicity("endpoint")
    assert (
        ResourceType.model_fields["endpoint"].description
        == "The resource type's HTTP-addressable endpoint relative to the Base URL, e.g., '/Users'."
    )
    assert ResourceType.get_field_annotation("endpoint", Required) == Required.true
    assert ResourceType.get_field_annotation("endpoint", CaseExact) == CaseExact.false
    assert (
        ResourceType.get_field_annotation("endpoint", Mutability)
        == Mutability.read_only
    )
    assert ResourceType.get_field_annotation("endpoint", Returned) == Returned.default
    assert ResourceType.get_field_annotation("endpoint", Uniqueness) == Uniqueness.none

    # schema
    assert ResourceType.get_field_root_type("schema_") == Reference[URIReference]
    assert not ResourceType.get_field_multiplicity("schema_")
    assert (
        ResourceType.model_fields["schema_"].description
        == "The resource type's primary/base schema URI."
    )
    assert ResourceType.get_field_annotation("schema_", Required) == Required.true
    assert ResourceType.get_field_annotation("schema_", CaseExact) == CaseExact.true
    assert (
        ResourceType.get_field_annotation("schema_", Mutability) == Mutability.read_only
    )
    assert ResourceType.get_field_annotation("schema_", Returned) == Returned.default
    assert ResourceType.get_field_annotation("schema_", Uniqueness) == Uniqueness.none

    # schema_extensions
    SchemaExtensions = ResourceType.get_field_root_type("schema_extensions")
    assert SchemaExtensions == ResourceType.SchemaExtensions
    assert issubclass(SchemaExtensions, ComplexAttribute)
    assert ResourceType.get_field_multiplicity("schema_extensions")
    assert (
        ResourceType.model_fields["schema_extensions"].description
        == "A list of URIs of the resource type's schema extensions."
    )
    assert (
        ResourceType.get_field_annotation("schema_extensions", Required)
        == Required.true
    )
    assert (
        ResourceType.get_field_annotation("schema_extensions", CaseExact)
        == CaseExact.false
    )
    assert (
        ResourceType.get_field_annotation("schema_extensions", Mutability)
        == Mutability.read_only
    )
    assert (
        ResourceType.get_field_annotation("schema_extensions", Returned)
        == Returned.default
    )
    assert (
        ResourceType.get_field_annotation("schema_extensions", Uniqueness)
        == Uniqueness.none
    )

    # SchemaExtensions.schema
    assert SchemaExtensions.get_field_root_type("schema_") == Reference[URIReference]
    assert not SchemaExtensions.get_field_multiplicity("schema_")
    assert (
        SchemaExtensions.model_fields["schema_"].description
        == "The URI of a schema extension."
    )
    assert SchemaExtensions.get_field_annotation("schema_", Required) == Required.true
    assert SchemaExtensions.get_field_annotation("schema_", CaseExact) == CaseExact.true
    assert (
        SchemaExtensions.get_field_annotation("schema_", Mutability)
        == Mutability.read_only
    )
    assert (
        SchemaExtensions.get_field_annotation("schema_", Returned) == Returned.default
    )
    assert (
        SchemaExtensions.get_field_annotation("schema_", Uniqueness) == Uniqueness.none
    )

    # SchemaExtensions.required
    assert SchemaExtensions.get_field_root_type("required") is bool
    assert not SchemaExtensions.get_field_multiplicity("required")
    assert (
        SchemaExtensions.model_fields["required"].description
        == "A Boolean value that specifies whether or not the schema extension is required for the resource type.  If True, a resource of this type MUST include this schema extension and also include any attributes declared as required in this schema extension. If False, a resource of this type MAY omit this schema extension."
    )
    assert SchemaExtensions.get_field_annotation("required", Required) == Required.true
    assert (
        SchemaExtensions.get_field_annotation("required", CaseExact) == CaseExact.false
    )
    assert (
        SchemaExtensions.get_field_annotation("required", Mutability)
        == Mutability.read_only
    )
    assert (
        SchemaExtensions.get_field_annotation("required", Returned) == Returned.default
    )
    assert (
        SchemaExtensions.get_field_annotation("required", Uniqueness) == Uniqueness.none
    )

    payload = load_sample("rfc7643-8.6-resource_type-user.json")
    obj = ResourceType.model_validate(payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    assert obj.id == "User"
    assert obj.name == "User"
    assert obj.endpoint == "/Users"
    assert obj.description == "User Account"
    assert obj.schema_ == Reference("urn:ietf:params:scim:schemas:core:2.0:User")
    assert obj.schema_extensions[0].schema_ == Reference(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert obj.schema_extensions[0].required is True
    assert obj.meta.location == "https://example.com/v2/ResourceTypes/User"
    assert obj.meta.resource_type == "ResourceType"

    assert obj.model_dump(exclude_unset=True) == payload

    payload = load_sample("rfc7643-8.6-resource_type-group.json")
    obj = ResourceType.model_validate(payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    assert obj.id == "Group"
    assert obj.name == "Group"
    assert obj.endpoint == "/Groups"
    assert obj.description == "Group"
    assert obj.schema_ == Reference("urn:ietf:params:scim:schemas:core:2.0:Group")
    assert obj.meta.location == "https://example.com/v2/ResourceTypes/Group"
    assert obj.meta.resource_type == "ResourceType"

    assert obj.model_dump(exclude_unset=True) == payload


def test_make_service_provider_config_model_from_schema(load_sample):
    payload = load_sample("rfc7643-8.7.2-schema-service_provider_configuration.json")
    schema = Schema.model_validate(payload)
    ServiceProviderConfig = Resource.from_schema(schema)

    assert ServiceProviderConfig.model_fields["schemas"].default == [
        "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
    ]

    # documentation_uri
    assert (
        ServiceProviderConfig.get_field_root_type("documentation_uri")
        == Reference[ExternalReference]
    )
    assert not ServiceProviderConfig.get_field_multiplicity("documentation_uri")
    assert (
        ServiceProviderConfig.model_fields["documentation_uri"].description
        == "An HTTP-addressable URL pointing to the service provider's human-consumable help documentation."
    )
    assert (
        ServiceProviderConfig.get_field_annotation("documentation_uri", Required)
        == Required.false
    )
    assert (
        ServiceProviderConfig.get_field_annotation("documentation_uri", CaseExact)
        == CaseExact.false
    )
    assert (
        ServiceProviderConfig.get_field_annotation("documentation_uri", Mutability)
        == Mutability.read_only
    )
    assert (
        ServiceProviderConfig.get_field_annotation("documentation_uri", Returned)
        == Returned.default
    )
    assert (
        ServiceProviderConfig.get_field_annotation("documentation_uri", Uniqueness)
        == Uniqueness.none
    )

    # patch
    Patch = ServiceProviderConfig.get_field_root_type("patch")
    assert Patch == ServiceProviderConfig.Patch
    assert issubclass(Patch, ComplexAttribute)
    assert not ServiceProviderConfig.get_field_multiplicity("patch")
    assert (
        ServiceProviderConfig.model_fields["patch"].description
        == "A complex type that specifies PATCH configuration options."
    )
    assert (
        ServiceProviderConfig.get_field_annotation("patch", Required) == Required.true
    )
    assert (
        ServiceProviderConfig.get_field_annotation("patch", CaseExact)
        == CaseExact.false
    )
    assert (
        ServiceProviderConfig.get_field_annotation("patch", Mutability)
        == Mutability.read_only
    )
    assert (
        ServiceProviderConfig.get_field_annotation("patch", Returned)
        == Returned.default
    )
    assert (
        ServiceProviderConfig.get_field_annotation("patch", Uniqueness)
        == Uniqueness.none
    )

    # patch.supported
    assert Patch.get_field_root_type("supported") is bool
    assert not Patch.get_field_multiplicity("supported")
    assert (
        Patch.model_fields["supported"].description
        == "A Boolean value specifying whether or not the operation is supported."
    )
    assert Patch.get_field_annotation("supported", Required) == Required.true
    assert Patch.get_field_annotation("supported", CaseExact) == CaseExact.false
    assert Patch.get_field_annotation("supported", Mutability) == Mutability.read_only
    assert Patch.get_field_annotation("supported", Returned) == Returned.default
    assert Patch.get_field_annotation("supported", Uniqueness) == Uniqueness.none

    # bulk
    Bulk = ServiceProviderConfig.get_field_root_type("bulk")
    assert Bulk == ServiceProviderConfig.Bulk
    assert issubclass(Bulk, ComplexAttribute)
    assert not ServiceProviderConfig.get_field_multiplicity("bulk")
    assert (
        ServiceProviderConfig.model_fields["bulk"].description
        == "A complex type that specifies bulk configuration options."
    )
    assert ServiceProviderConfig.get_field_annotation("bulk", Required) == Required.true
    assert (
        ServiceProviderConfig.get_field_annotation("bulk", CaseExact) == CaseExact.false
    )
    assert (
        ServiceProviderConfig.get_field_annotation("bulk", Mutability)
        == Mutability.read_only
    )
    assert (
        ServiceProviderConfig.get_field_annotation("bulk", Returned) == Returned.default
    )
    assert (
        ServiceProviderConfig.get_field_annotation("bulk", Uniqueness)
        == Uniqueness.none
    )

    # bulk.supported
    assert Bulk.get_field_root_type("supported") is bool
    assert not Bulk.get_field_multiplicity("supported")
    assert (
        Bulk.model_fields["supported"].description
        == "A Boolean value specifying whether or not the operation is supported."
    )
    assert Bulk.get_field_annotation("supported", Required) == Required.true
    assert Bulk.get_field_annotation("supported", CaseExact) == CaseExact.false
    assert Bulk.get_field_annotation("supported", Mutability) == Mutability.read_only
    assert Bulk.get_field_annotation("supported", Returned) == Returned.default
    assert Bulk.get_field_annotation("supported", Uniqueness) == Uniqueness.none

    # bulk.max_operations
    assert Bulk.get_field_root_type("max_operations") is int
    assert not Bulk.get_field_multiplicity("max_operations")
    assert (
        Bulk.model_fields["max_operations"].description
        == "An integer value specifying the maximum number of operations."
    )
    assert Bulk.get_field_annotation("max_operations", Required) == Required.true
    assert Bulk.get_field_annotation("max_operations", CaseExact) == CaseExact.false
    assert (
        Bulk.get_field_annotation("max_operations", Mutability) == Mutability.read_only
    )
    assert Bulk.get_field_annotation("max_operations", Returned) == Returned.default
    assert Bulk.get_field_annotation("max_operations", Uniqueness) == Uniqueness.none

    # bulk.max_payload_size
    assert Bulk.get_field_root_type("max_payload_size") is int
    assert not Bulk.get_field_multiplicity("max_payload_size")
    assert (
        Bulk.model_fields["max_payload_size"].description
        == "An integer value specifying the maximum payload size in bytes."
    )
    assert Bulk.get_field_annotation("max_payload_size", Required) == Required.true
    assert Bulk.get_field_annotation("max_payload_size", CaseExact) == CaseExact.false
    assert (
        Bulk.get_field_annotation("max_payload_size", Mutability)
        == Mutability.read_only
    )
    assert Bulk.get_field_annotation("max_payload_size", Returned) == Returned.default
    assert Bulk.get_field_annotation("max_payload_size", Uniqueness) == Uniqueness.none

    # filter
    Filter = ServiceProviderConfig.get_field_root_type("filter")
    assert Filter == ServiceProviderConfig.Filter
    assert issubclass(Filter, ComplexAttribute)
    assert not ServiceProviderConfig.get_field_multiplicity("filter")
    assert (
        ServiceProviderConfig.model_fields["filter"].description
        == "A complex type that specifies FILTER options."
    )
    assert (
        ServiceProviderConfig.get_field_annotation("filter", Required) == Required.true
    )
    assert (
        ServiceProviderConfig.get_field_annotation("filter", CaseExact)
        == CaseExact.false
    )
    assert (
        ServiceProviderConfig.get_field_annotation("filter", Mutability)
        == Mutability.read_only
    )
    assert (
        ServiceProviderConfig.get_field_annotation("filter", Returned)
        == Returned.default
    )
    assert (
        ServiceProviderConfig.get_field_annotation("filter", Uniqueness)
        == Uniqueness.none
    )

    # filter.supported
    assert Filter.get_field_root_type("supported") is bool
    assert not Filter.get_field_multiplicity("supported")
    assert (
        Filter.model_fields["supported"].description
        == "A Boolean value specifying whether or not the operation is supported."
    )
    assert Filter.get_field_annotation("supported", Required) == Required.true
    assert Filter.get_field_annotation("supported", CaseExact) == CaseExact.false
    assert Filter.get_field_annotation("supported", Mutability) == Mutability.read_only
    assert Filter.get_field_annotation("supported", Returned) == Returned.default
    assert Filter.get_field_annotation("supported", Uniqueness) == Uniqueness.none

    # filter.max_results
    assert Filter.get_field_root_type("max_results") is int
    assert not Filter.get_field_multiplicity("max_results")
    assert (
        Filter.model_fields["max_results"].description
        == "An integer value specifying the maximum number of resources returned in a response."
    )
    assert Filter.get_field_annotation("max_results", Required) == Required.true
    assert Filter.get_field_annotation("max_results", CaseExact) == CaseExact.false
    assert (
        Filter.get_field_annotation("max_results", Mutability) == Mutability.read_only
    )
    assert Filter.get_field_annotation("max_results", Returned) == Returned.default
    assert Filter.get_field_annotation("max_results", Uniqueness) == Uniqueness.none

    # change_password
    ChangePassword = ServiceProviderConfig.get_field_root_type("change_password")
    assert ChangePassword == ServiceProviderConfig.ChangePassword
    assert issubclass(ChangePassword, ComplexAttribute)
    assert not ServiceProviderConfig.get_field_multiplicity("change_password")
    assert (
        ServiceProviderConfig.model_fields["change_password"].description
        == "A complex type that specifies configuration options related to changing a password."
    )
    assert (
        ServiceProviderConfig.get_field_annotation("change_password", Required)
        == Required.true
    )
    assert (
        ServiceProviderConfig.get_field_annotation("change_password", CaseExact)
        == CaseExact.false
    )
    assert (
        ServiceProviderConfig.get_field_annotation("change_password", Mutability)
        == Mutability.read_only
    )
    assert (
        ServiceProviderConfig.get_field_annotation("change_password", Returned)
        == Returned.default
    )
    assert (
        ServiceProviderConfig.get_field_annotation("change_password", Uniqueness)
        == Uniqueness.none
    )

    # change_password.supported
    assert ChangePassword.get_field_root_type("supported") is bool
    assert not ChangePassword.get_field_multiplicity("supported")
    assert (
        ChangePassword.model_fields["supported"].description
        == "A Boolean value specifying whether or not the operation is supported."
    )
    assert ChangePassword.get_field_annotation("supported", Required) == Required.true
    assert (
        ChangePassword.get_field_annotation("supported", CaseExact) == CaseExact.false
    )
    assert (
        ChangePassword.get_field_annotation("supported", Mutability)
        == Mutability.read_only
    )
    assert (
        ChangePassword.get_field_annotation("supported", Returned) == Returned.default
    )
    assert (
        ChangePassword.get_field_annotation("supported", Uniqueness) == Uniqueness.none
    )

    # sort
    Sort = ServiceProviderConfig.get_field_root_type("sort")
    assert Sort == ServiceProviderConfig.Sort
    assert issubclass(Sort, ComplexAttribute)
    assert not ServiceProviderConfig.get_field_multiplicity("sort")
    assert (
        ServiceProviderConfig.model_fields["sort"].description
        == "A complex type that specifies sort result options."
    )
    assert ServiceProviderConfig.get_field_annotation("sort", Required) == Required.true
    assert (
        ServiceProviderConfig.get_field_annotation("sort", CaseExact) == CaseExact.false
    )
    assert (
        ServiceProviderConfig.get_field_annotation("sort", Mutability)
        == Mutability.read_only
    )
    assert (
        ServiceProviderConfig.get_field_annotation("sort", Returned) == Returned.default
    )
    assert (
        ServiceProviderConfig.get_field_annotation("sort", Uniqueness)
        == Uniqueness.none
    )

    # sort.supported
    assert Sort.get_field_root_type("supported") is bool
    assert not Sort.get_field_multiplicity("supported")
    assert (
        Sort.model_fields["supported"].description
        == "A Boolean value specifying whether or not the operation is supported."
    )
    assert Sort.get_field_annotation("supported", Required) == Required.true
    assert Sort.get_field_annotation("supported", CaseExact) == CaseExact.false
    assert Sort.get_field_annotation("supported", Mutability) == Mutability.read_only
    assert Sort.get_field_annotation("supported", Returned) == Returned.default
    assert Sort.get_field_annotation("supported", Uniqueness) == Uniqueness.none

    # etag
    Etag = ServiceProviderConfig.get_field_root_type("etag")
    assert Etag == ServiceProviderConfig.Etag
    assert issubclass(Etag, ComplexAttribute)
    assert not ServiceProviderConfig.get_field_multiplicity("etag")
    assert (
        ServiceProviderConfig.model_fields["etag"].description
        == "A complex type that specifies ETag result options."
    )
    assert ServiceProviderConfig.get_field_annotation("etag", Required) == Required.true
    assert (
        ServiceProviderConfig.get_field_annotation("etag", CaseExact) == CaseExact.false
    )
    assert (
        ServiceProviderConfig.get_field_annotation("etag", Mutability)
        == Mutability.read_only
    )
    assert (
        ServiceProviderConfig.get_field_annotation("etag", Returned) == Returned.default
    )
    assert (
        ServiceProviderConfig.get_field_annotation("etag", Uniqueness)
        == Uniqueness.none
    )

    # etag.supported
    assert Etag.get_field_root_type("supported") is bool
    assert not Etag.get_field_multiplicity("supported")
    assert (
        Etag.model_fields["supported"].description
        == "A Boolean value specifying whether or not the operation is supported."
    )
    assert Etag.get_field_annotation("supported", Required) == Required.true
    assert Etag.get_field_annotation("supported", CaseExact) == CaseExact.false
    assert Etag.get_field_annotation("supported", Mutability) == Mutability.read_only
    assert Etag.get_field_annotation("supported", Returned) == Returned.default
    assert Etag.get_field_annotation("supported", Uniqueness) == Uniqueness.none

    # authentication_schemes
    AuthenticationSchemes = ServiceProviderConfig.get_field_root_type(
        "authentication_schemes"
    )
    assert AuthenticationSchemes == ServiceProviderConfig.AuthenticationSchemes
    assert issubclass(AuthenticationSchemes, ComplexAttribute)
    assert ServiceProviderConfig.get_field_multiplicity("authentication_schemes")
    assert (
        ServiceProviderConfig.model_fields["authentication_schemes"].description
        == "A complex type that specifies supported authentication scheme properties."
    )
    assert (
        ServiceProviderConfig.get_field_annotation("authentication_schemes", Required)
        == Required.true
    )
    assert (
        ServiceProviderConfig.get_field_annotation("authentication_schemes", CaseExact)
        == CaseExact.false
    )
    assert (
        ServiceProviderConfig.get_field_annotation("authentication_schemes", Mutability)
        == Mutability.read_only
    )
    assert (
        ServiceProviderConfig.get_field_annotation("authentication_schemes", Returned)
        == Returned.default
    )
    assert (
        ServiceProviderConfig.get_field_annotation("authentication_schemes", Uniqueness)
        == Uniqueness.none
    )

    # authentication_schemes.name
    assert AuthenticationSchemes.get_field_root_type("name") is str
    assert not AuthenticationSchemes.get_field_multiplicity("name")
    assert (
        AuthenticationSchemes.model_fields["name"].description
        == "The common authentication scheme name, e.g., HTTP Basic."
    )
    assert AuthenticationSchemes.get_field_annotation("name", Required) == Required.true
    assert (
        AuthenticationSchemes.get_field_annotation("name", CaseExact) == CaseExact.false
    )
    assert (
        AuthenticationSchemes.get_field_annotation("name", Mutability)
        == Mutability.read_only
    )
    assert (
        AuthenticationSchemes.get_field_annotation("name", Returned) == Returned.default
    )
    assert (
        AuthenticationSchemes.get_field_annotation("name", Uniqueness)
        == Uniqueness.none
    )

    # authentication_schemes.description
    assert AuthenticationSchemes.get_field_root_type("description") is str
    assert not AuthenticationSchemes.get_field_multiplicity("description")
    assert (
        AuthenticationSchemes.model_fields["description"].description
        == "A description of the authentication scheme."
    )
    assert (
        AuthenticationSchemes.get_field_annotation("description", Required)
        == Required.true
    )
    assert (
        AuthenticationSchemes.get_field_annotation("description", CaseExact)
        == CaseExact.false
    )
    assert (
        AuthenticationSchemes.get_field_annotation("description", Mutability)
        == Mutability.read_only
    )
    assert (
        AuthenticationSchemes.get_field_annotation("description", Returned)
        == Returned.default
    )
    assert (
        AuthenticationSchemes.get_field_annotation("description", Uniqueness)
        == Uniqueness.none
    )

    # authentication_schemes.spec_uri
    assert (
        AuthenticationSchemes.get_field_root_type("spec_uri")
        == Reference[ExternalReference]
    )
    assert not AuthenticationSchemes.get_field_multiplicity("spec_uri")
    assert (
        AuthenticationSchemes.model_fields["spec_uri"].description
        == "An HTTP-addressable URL pointing to the authentication scheme's specification."
    )
    assert (
        AuthenticationSchemes.get_field_annotation("spec_uri", Required)
        == Required.false
    )
    assert (
        AuthenticationSchemes.get_field_annotation("spec_uri", CaseExact)
        == CaseExact.false
    )
    assert (
        AuthenticationSchemes.get_field_annotation("spec_uri", Mutability)
        == Mutability.read_only
    )
    assert (
        AuthenticationSchemes.get_field_annotation("spec_uri", Returned)
        == Returned.default
    )
    assert (
        AuthenticationSchemes.get_field_annotation("spec_uri", Uniqueness)
        == Uniqueness.none
    )

    # authentication_schemes.documentation_uri
    assert (
        AuthenticationSchemes.get_field_root_type("documentation_uri")
        == Reference[ExternalReference]
    )
    assert not AuthenticationSchemes.get_field_multiplicity("documentation_uri")
    assert (
        AuthenticationSchemes.model_fields["documentation_uri"].description
        == "An HTTP-addressable URL pointing to the authentication scheme's usage documentation."
    )
    assert (
        AuthenticationSchemes.get_field_annotation("documentation_uri", Required)
        == Required.false
    )
    assert (
        AuthenticationSchemes.get_field_annotation("documentation_uri", CaseExact)
        == CaseExact.false
    )
    assert (
        AuthenticationSchemes.get_field_annotation("documentation_uri", Mutability)
        == Mutability.read_only
    )
    assert (
        AuthenticationSchemes.get_field_annotation("documentation_uri", Returned)
        == Returned.default
    )
    assert (
        AuthenticationSchemes.get_field_annotation("documentation_uri", Uniqueness)
        == Uniqueness.none
    )

    payload = load_sample("rfc7643-8.5-service_provider_configuration.json")
    obj = ServiceProviderConfig.model_validate(payload)

    assert obj.schemas == [
        "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
    ]
    assert obj.documentation_uri == Reference("http://example.com/help/scim.html")
    assert obj.patch.supported is True
    assert obj.bulk.supported is True
    assert obj.bulk.max_operations == 1000
    assert obj.bulk.max_payload_size == 1048576
    assert obj.filter.supported is True
    assert obj.filter.max_results == 200
    assert obj.change_password.supported is True
    assert obj.sort.supported is True
    assert obj.etag.supported is True
    assert obj.authentication_schemes[0].name == "OAuth Bearer Token"
    assert (
        obj.authentication_schemes[0].description
        == "Authentication scheme using the OAuth Bearer Token Standard"
    )
    assert obj.authentication_schemes[0].spec_uri == Reference(
        "http://www.rfc-editor.org/info/rfc6750"
    )
    assert obj.authentication_schemes[0].documentation_uri == Reference(
        "http://example.com/help/oauth.html"
    )
    assert obj.authentication_schemes[0].type == "oauthbearertoken"
    assert obj.authentication_schemes[0].primary is True

    assert obj.authentication_schemes[1].name == "HTTP Basic"
    assert (
        obj.authentication_schemes[1].description
        == "Authentication scheme using the HTTP Basic Standard"
    )
    assert obj.authentication_schemes[1].spec_uri == Reference(
        "http://www.rfc-editor.org/info/rfc2617"
    )
    assert obj.authentication_schemes[1].documentation_uri == Reference(
        "http://example.com/help/httpBasic.html"
    )
    assert obj.authentication_schemes[1].type == "httpbasic"
    assert obj.meta.location == "https://example.com/v2/ServiceProviderConfig"
    assert obj.meta.resource_type == "ServiceProviderConfig"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.last_modified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"3694e05e9dff594"'

    assert obj.model_dump() == payload


def test_make_schema_model_from_schema(load_sample):
    payload = load_sample("rfc7643-8.7.2-schema-schema.json")
    schema = Schema.model_validate(payload)
    Schema_ = Resource.from_schema(schema)

    assert Schema_.model_fields["schemas"].default == [
        "urn:ietf:params:scim:schemas:core:2.0:Schema"
    ]

    # id
    assert Schema_.get_field_root_type("id") is str
    assert not Schema_.get_field_multiplicity("id")
    assert (
        Schema_.model_fields["id"].description
        == "The unique URI of the schema. When applicable, service providers MUST specify the URI."
    )
    assert Schema_.get_field_annotation("id", Required) == Required.true
    assert Schema_.get_field_annotation("id", CaseExact) == CaseExact.false
    assert Schema_.get_field_annotation("id", Mutability) == Mutability.read_only
    assert Schema_.get_field_annotation("id", Returned) == Returned.default
    assert Schema_.get_field_annotation("id", Uniqueness) == Uniqueness.none

    # name
    assert Schema_.get_field_root_type("name") is str
    assert not Schema_.get_field_multiplicity("name")
    assert (
        Schema_.model_fields["name"].description
        == "The schema's human-readable name.  When applicable, service providers MUST specify the name, e.g., 'User'."
    )
    assert Schema_.get_field_annotation("name", Required) == Required.true
    assert Schema_.get_field_annotation("name", CaseExact) == CaseExact.false
    assert Schema_.get_field_annotation("name", Mutability) == Mutability.read_only
    assert Schema_.get_field_annotation("name", Returned) == Returned.default
    assert Schema_.get_field_annotation("name", Uniqueness) == Uniqueness.none

    # description
    assert Schema_.get_field_root_type("description") is str
    assert not Schema_.get_field_multiplicity("description")
    assert (
        Schema_.model_fields["description"].description
        == "The schema's human-readable description.  When applicable, service providers MUST specify the description."
    )
    assert Schema_.get_field_annotation("description", Required) == Required.false
    assert Schema_.get_field_annotation("description", CaseExact) == CaseExact.false
    assert (
        Schema_.get_field_annotation("description", Mutability) == Mutability.read_only
    )
    assert Schema_.get_field_annotation("description", Returned) == Returned.default
    assert Schema_.get_field_annotation("description", Uniqueness) == Uniqueness.none

    # attributes
    Attributes = Schema_.get_field_root_type("attributes")
    assert Attributes == Schema_.Attributes
    assert issubclass(Attributes, MultiValuedComplexAttribute)
    assert Schema_.get_field_multiplicity("attributes")
    assert (
        Schema_.model_fields["attributes"].description
        == "A complex attribute that includes the attributes of a schema."
    )
    assert Schema_.get_field_annotation("attributes", Required) == Required.true
    assert Schema_.get_field_annotation("attributes", CaseExact) == CaseExact.false
    assert (
        Schema_.get_field_annotation("attributes", Mutability) == Mutability.read_only
    )
    assert Schema_.get_field_annotation("attributes", Returned) == Returned.default
    assert Schema_.get_field_annotation("attributes", Uniqueness) == Uniqueness.none

    # attributes.name
    assert Attributes.get_field_root_type("name") is str
    assert not Attributes.get_field_multiplicity("name")
    assert Attributes.model_fields["name"].description == "The attribute's name."
    assert Attributes.get_field_annotation("name", Required) == Required.true
    assert Attributes.get_field_annotation("name", CaseExact) == CaseExact.true
    assert Attributes.get_field_annotation("name", Mutability) == Mutability.read_only
    assert Attributes.get_field_annotation("name", Returned) == Returned.default
    assert Attributes.get_field_annotation("name", Uniqueness) == Uniqueness.none

    # attributes.type
    assert Attributes.get_field_root_type("type") is str
    assert not Attributes.get_field_multiplicity("type")
    assert (
        Attributes.model_fields["type"].description
        == "The attribute's data type. Valid values include 'string', 'complex', 'boolean', 'decimal', 'integer', 'dateTime', 'reference'."
    )
    assert Attributes.get_field_annotation("type", Required) == Required.true
    assert Attributes.get_field_annotation("type", CaseExact) == CaseExact.false
    assert Attributes.model_fields["type"].examples == [
        "string",
        "complex",
        "boolean",
        "decimal",
        "integer",
        "dateTime",
        "reference",
        "binary",
    ]
    assert Attributes.get_field_annotation("type", Mutability) == Mutability.read_only
    assert Attributes.get_field_annotation("type", Returned) == Returned.default
    assert Attributes.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # attributes.multi_valued
    assert Attributes.get_field_root_type("multi_valued") is bool
    assert not Attributes.get_field_multiplicity("multi_valued")
    assert (
        Attributes.model_fields["multi_valued"].description
        == "A Boolean value indicating an  attribute's plurality."
    )
    assert Attributes.get_field_annotation("multi_valued", Required) == Required.true
    assert Attributes.get_field_annotation("multi_valued", CaseExact) == CaseExact.false
    assert (
        Attributes.get_field_annotation("multi_valued", Mutability)
        == Mutability.read_only
    )
    assert Attributes.get_field_annotation("multi_valued", Returned) == Returned.default
    assert (
        Attributes.get_field_annotation("multi_valued", Uniqueness) == Uniqueness.none
    )

    # attributes.description
    assert Attributes.get_field_root_type("description") is str
    assert not Attributes.get_field_multiplicity("description")
    assert (
        Attributes.model_fields["description"].description
        == "A human-readable description of the attribute."
    )
    assert Attributes.get_field_annotation("description", Required) == Required.false
    assert Attributes.get_field_annotation("description", CaseExact) == CaseExact.true
    assert (
        Attributes.get_field_annotation("description", Mutability)
        == Mutability.read_only
    )
    assert Attributes.get_field_annotation("description", Returned) == Returned.default
    assert Attributes.get_field_annotation("description", Uniqueness) == Uniqueness.none

    # attributes.required
    assert Attributes.get_field_root_type("required") is bool
    assert not Attributes.get_field_multiplicity("required")
    assert (
        Attributes.model_fields["required"].description
        == "A boolean value indicating whether or not the attribute is required."
    )
    assert Attributes.get_field_annotation("required", Required) == Required.false
    assert Attributes.get_field_annotation("required", CaseExact) == CaseExact.false
    assert (
        Attributes.get_field_annotation("required", Mutability) == Mutability.read_only
    )
    assert Attributes.get_field_annotation("required", Returned) == Returned.default
    assert Attributes.get_field_annotation("required", Uniqueness) == Uniqueness.none

    # attributes.canonical_values
    assert Attributes.get_field_root_type("canonical_values") is str
    assert Attributes.get_field_multiplicity("canonical_values")
    assert (
        Attributes.model_fields["canonical_values"].description
        == "A collection of canonical values.  When  applicable, service providers MUST specify the canonical types, e.g., 'work', 'home'."
    )
    assert (
        Attributes.get_field_annotation("canonical_values", Required) == Required.false
    )
    assert (
        Attributes.get_field_annotation("canonical_values", CaseExact) == CaseExact.true
    )
    assert (
        Attributes.get_field_annotation("canonical_values", Mutability)
        == Mutability.read_only
    )
    assert (
        Attributes.get_field_annotation("canonical_values", Returned)
        == Returned.default
    )
    assert (
        Attributes.get_field_annotation("canonical_values", Uniqueness)
        == Uniqueness.none
    )

    # attributes.case_exact
    assert Attributes.get_field_root_type("case_exact") is bool
    assert not Attributes.get_field_multiplicity("case_exact")
    assert (
        Attributes.model_fields["case_exact"].description
        == "A Boolean value indicating whether or not a string attribute is case sensitive."
    )
    assert Attributes.get_field_annotation("case_exact", Required) == Required.false
    assert Attributes.get_field_annotation("case_exact", CaseExact) == CaseExact.false
    assert (
        Attributes.get_field_annotation("case_exact", Mutability)
        == Mutability.read_only
    )
    assert Attributes.get_field_annotation("case_exact", Returned) == Returned.default
    assert Attributes.get_field_annotation("case_exact", Uniqueness) == Uniqueness.none

    # attributes.mutability
    assert Attributes.get_field_root_type("mutability") is str
    assert not Attributes.get_field_multiplicity("mutability")
    assert (
        Attributes.model_fields["mutability"].description
        == "Indicates whether or not an attribute is modifiable."
    )
    assert Attributes.get_field_annotation("mutability", Required) == Required.false
    assert Attributes.get_field_annotation("mutability", CaseExact) == CaseExact.true
    assert Attributes.model_fields["mutability"].examples == [
        "readOnly",
        "readWrite",
        "immutable",
        "writeOnly",
    ]
    assert (
        Attributes.get_field_annotation("mutability", Mutability)
        == Mutability.read_only
    )
    assert Attributes.get_field_annotation("mutability", Returned) == Returned.default
    assert Attributes.get_field_annotation("mutability", Uniqueness) == Uniqueness.none

    # attributes.returned
    assert Attributes.get_field_root_type("returned") is str
    assert not Attributes.get_field_multiplicity("returned")
    assert (
        Attributes.model_fields["returned"].description
        == "Indicates when an attribute is returned in a response (e.g., to a query)."
    )
    assert Attributes.get_field_annotation("returned", Required) == Required.false
    assert Attributes.get_field_annotation("returned", CaseExact) == CaseExact.true
    assert Attributes.model_fields["returned"].examples == [
        "always",
        "never",
        "default",
        "request",
    ]
    assert (
        Attributes.get_field_annotation("returned", Mutability) == Mutability.read_only
    )
    assert Attributes.get_field_annotation("returned", Returned) == Returned.default
    assert Attributes.get_field_annotation("returned", Uniqueness) == Uniqueness.none

    # attributes.uniqueness
    assert Attributes.get_field_root_type("uniqueness") is str
    assert not Attributes.get_field_multiplicity("uniqueness")
    assert (
        Attributes.model_fields["uniqueness"].description
        == "Indicates how unique a value must be."
    )
    assert Attributes.get_field_annotation("uniqueness", Required) == Required.false
    assert Attributes.get_field_annotation("uniqueness", CaseExact) == CaseExact.true
    assert Attributes.model_fields["uniqueness"].examples == [
        "none",
        "server",
        "global",
    ]
    assert (
        Attributes.get_field_annotation("uniqueness", Mutability)
        == Mutability.read_only
    )
    assert Attributes.get_field_annotation("uniqueness", Returned) == Returned.default
    assert Attributes.get_field_annotation("uniqueness", Uniqueness) == Uniqueness.none

    # attributes.reference_types
    assert Attributes.get_field_root_type("reference_types") is str
    assert Attributes.get_field_multiplicity("reference_types")
    assert (
        Attributes.model_fields["reference_types"].description
        == "Used only with an attribute of type 'reference'.  Specifies a SCIM resourceType that a reference attribute MAY refer to, e.g., 'User'."
    )
    assert (
        Attributes.get_field_annotation("reference_types", Required) == Required.false
    )
    assert (
        Attributes.get_field_annotation("reference_types", CaseExact) == CaseExact.true
    )
    assert (
        Attributes.get_field_annotation("reference_types", Mutability)
        == Mutability.read_only
    )
    assert (
        Attributes.get_field_annotation("reference_types", Returned) == Returned.default
    )
    assert (
        Attributes.get_field_annotation("reference_types", Uniqueness)
        == Uniqueness.none
    )

    # sub_attributes
    SubAttributes = Attributes.get_field_root_type("sub_attributes")
    assert SubAttributes == Attributes.SubAttributes
    assert issubclass(SubAttributes, MultiValuedComplexAttribute)
    assert Attributes.get_field_multiplicity("sub_attributes")
    assert (
        Attributes.model_fields["sub_attributes"].description
        == "Used to define the sub-attributes of a complex attribute."
    )
    assert Attributes.get_field_annotation("sub_attributes", Required) == Required.false
    assert (
        Attributes.get_field_annotation("sub_attributes", CaseExact) == CaseExact.false
    )
    assert (
        Attributes.get_field_annotation("sub_attributes", Mutability)
        == Mutability.read_only
    )
    assert (
        Attributes.get_field_annotation("sub_attributes", Returned) == Returned.default
    )
    assert (
        Attributes.get_field_annotation("sub_attributes", Uniqueness) == Uniqueness.none
    )

    # sub_attributes.name
    assert SubAttributes.get_field_root_type("name") is str
    assert not SubAttributes.get_field_multiplicity("name")
    assert SubAttributes.model_fields["name"].description == "The attribute's name."
    assert SubAttributes.get_field_annotation("name", Required) == Required.true
    assert SubAttributes.get_field_annotation("name", CaseExact) == CaseExact.true
    assert (
        SubAttributes.get_field_annotation("name", Mutability) == Mutability.read_only
    )
    assert SubAttributes.get_field_annotation("name", Returned) == Returned.default
    assert SubAttributes.get_field_annotation("name", Uniqueness) == Uniqueness.none

    # sub_attributes.type
    assert SubAttributes.get_field_root_type("type") is str
    assert not SubAttributes.get_field_multiplicity("type")
    assert (
        SubAttributes.model_fields["type"].description
        == "The attribute's data type. Valid values include 'string', 'complex', 'boolean', 'decimal', 'integer', 'dateTime', 'reference'."
    )
    assert SubAttributes.get_field_annotation("type", Required) == Required.true
    assert SubAttributes.get_field_annotation("type", CaseExact) == CaseExact.false
    assert SubAttributes.model_fields["type"].examples == [
        "string",
        "complex",
        "boolean",
        "decimal",
        "integer",
        "dateTime",
        "reference",
        "binary",
    ]
    assert (
        SubAttributes.get_field_annotation("type", Mutability) == Mutability.read_only
    )
    assert SubAttributes.get_field_annotation("type", Returned) == Returned.default
    assert SubAttributes.get_field_annotation("type", Uniqueness) == Uniqueness.none

    # sub_attributes.multi_valued
    assert SubAttributes.get_field_root_type("multi_valued") is bool
    assert not SubAttributes.get_field_multiplicity("multi_valued")
    assert (
        SubAttributes.model_fields["multi_valued"].description
        == "A Boolean value indicating an attribute's plurality."
    )
    assert SubAttributes.get_field_annotation("multi_valued", Required) == Required.true
    assert (
        SubAttributes.get_field_annotation("multi_valued", CaseExact) == CaseExact.false
    )
    assert (
        SubAttributes.get_field_annotation("multi_valued", Mutability)
        == Mutability.read_only
    )
    assert (
        SubAttributes.get_field_annotation("multi_valued", Returned) == Returned.default
    )
    assert (
        SubAttributes.get_field_annotation("multi_valued", Uniqueness)
        == Uniqueness.none
    )

    # sub_attributes.description
    assert SubAttributes.get_field_root_type("description") is str
    assert not SubAttributes.get_field_multiplicity("description")
    assert (
        SubAttributes.model_fields["description"].description
        == "A human-readable description of the attribute."
    )
    assert SubAttributes.get_field_annotation("description", Required) == Required.false
    assert (
        SubAttributes.get_field_annotation("description", CaseExact) == CaseExact.true
    )
    assert (
        SubAttributes.get_field_annotation("description", Mutability)
        == Mutability.read_only
    )
    assert (
        SubAttributes.get_field_annotation("description", Returned) == Returned.default
    )
    assert (
        SubAttributes.get_field_annotation("description", Uniqueness) == Uniqueness.none
    )

    # sub_attributes.required
    assert SubAttributes.get_field_root_type("required") is bool
    assert not SubAttributes.get_field_multiplicity("required")
    assert (
        SubAttributes.model_fields["required"].description
        == "A boolean value indicating whether or not the attribute is required."
    )
    assert SubAttributes.get_field_annotation("required", Required) == Required.false
    assert SubAttributes.get_field_annotation("required", CaseExact) == CaseExact.false
    assert (
        SubAttributes.get_field_annotation("required", Mutability)
        == Mutability.read_only
    )
    assert SubAttributes.get_field_annotation("required", Returned) == Returned.default
    assert SubAttributes.get_field_annotation("required", Uniqueness) == Uniqueness.none

    # sub_attributes.canonical_values
    assert SubAttributes.get_field_root_type("canonical_values") is str
    assert SubAttributes.get_field_multiplicity("canonical_values")
    assert (
        SubAttributes.model_fields["canonical_values"].description
        == "A collection of canonical values.  When applicable, service providers MUST specify the canonical types, e.g., 'work', 'home'."
    )
    assert (
        SubAttributes.get_field_annotation("canonical_values", Required)
        == Required.false
    )
    assert (
        SubAttributes.get_field_annotation("canonical_values", CaseExact)
        == CaseExact.true
    )
    assert (
        SubAttributes.get_field_annotation("canonical_values", Mutability)
        == Mutability.read_only
    )
    assert (
        SubAttributes.get_field_annotation("canonical_values", Returned)
        == Returned.default
    )
    assert (
        SubAttributes.get_field_annotation("canonical_values", Uniqueness)
        == Uniqueness.none
    )

    # sub_attributes.case_exact
    assert SubAttributes.get_field_root_type("case_exact") is bool
    assert not SubAttributes.get_field_multiplicity("case_exact")
    assert (
        SubAttributes.model_fields["case_exact"].description
        == "A Boolean value indicating whether or not a string attribute is case sensitive."
    )
    assert SubAttributes.get_field_annotation("case_exact", Required) == Required.false
    assert (
        SubAttributes.get_field_annotation("case_exact", CaseExact) == CaseExact.false
    )
    assert (
        SubAttributes.get_field_annotation("case_exact", Mutability)
        == Mutability.read_only
    )
    assert (
        SubAttributes.get_field_annotation("case_exact", Returned) == Returned.default
    )
    assert (
        SubAttributes.get_field_annotation("case_exact", Uniqueness) == Uniqueness.none
    )

    # sub_attributes.mutability
    assert SubAttributes.get_field_root_type("mutability") is str
    assert not SubAttributes.get_field_multiplicity("mutability")
    assert (
        SubAttributes.model_fields["mutability"].description
        == "Indicates whether or not an attribute is modifiable."
    )
    assert SubAttributes.get_field_annotation("mutability", Required) == Required.false
    assert SubAttributes.get_field_annotation("mutability", CaseExact) == CaseExact.true
    assert SubAttributes.model_fields["mutability"].examples == [
        "readOnly",
        "readWrite",
        "immutable",
        "writeOnly",
    ]
    assert (
        SubAttributes.get_field_annotation("mutability", Mutability)
        == Mutability.read_only
    )
    assert (
        SubAttributes.get_field_annotation("mutability", Returned) == Returned.default
    )
    assert (
        SubAttributes.get_field_annotation("mutability", Uniqueness) == Uniqueness.none
    )

    # sub_attributes.returned
    assert SubAttributes.get_field_root_type("returned") is str
    assert not SubAttributes.get_field_multiplicity("returned")
    assert (
        SubAttributes.model_fields["returned"].description
        == "Indicates when an attribute is returned in a response (e.g., to a query)."
    )
    assert SubAttributes.get_field_annotation("returned", Required) == Required.false
    assert SubAttributes.get_field_annotation("returned", CaseExact) == CaseExact.true
    assert SubAttributes.model_fields["returned"].examples == [
        "always",
        "never",
        "default",
        "request",
    ]
    assert (
        SubAttributes.get_field_annotation("returned", Mutability)
        == Mutability.read_only
    )
    assert SubAttributes.get_field_annotation("returned", Returned) == Returned.default
    assert SubAttributes.get_field_annotation("returned", Uniqueness) == Uniqueness.none

    # sub_attributes.uniqueness
    assert SubAttributes.get_field_root_type("uniqueness") is str
    assert not SubAttributes.get_field_multiplicity("uniqueness")
    assert (
        SubAttributes.model_fields["uniqueness"].description
        == "Indicates how unique a value must be."
    )
    assert SubAttributes.get_field_annotation("uniqueness", Required) == Required.false
    assert SubAttributes.get_field_annotation("uniqueness", CaseExact) == CaseExact.true
    assert SubAttributes.model_fields["uniqueness"].examples == [
        "none",
        "server",
        "global",
    ]
    assert (
        SubAttributes.get_field_annotation("uniqueness", Mutability)
        == Mutability.read_only
    )
    assert (
        SubAttributes.get_field_annotation("uniqueness", Returned) == Returned.default
    )
    assert (
        SubAttributes.get_field_annotation("uniqueness", Uniqueness) == Uniqueness.none
    )

    # sub_attributes.reference_types
    assert SubAttributes.get_field_root_type("reference_types") is str
    assert SubAttributes.get_field_multiplicity("reference_types")
    assert (
        SubAttributes.model_fields["reference_types"].description
        == "Used only with an attribute of type 'reference'.  Specifies a SCIM resourceType that a reference attribute MAY refer to, e.g., 'User'."
    )
    assert (
        SubAttributes.get_field_annotation("reference_types", Required)
        == Required.false
    )
    assert (
        SubAttributes.get_field_annotation("reference_types", CaseExact)
        == CaseExact.true
    )
    assert (
        SubAttributes.get_field_annotation("reference_types", Mutability)
        == Mutability.read_only
    )
    assert (
        SubAttributes.get_field_annotation("reference_types", Returned)
        == Returned.default
    )
    assert (
        SubAttributes.get_field_annotation("reference_types", Uniqueness)
        == Uniqueness.none
    )

    payload = load_sample("rfc7643-8.7.1-schema-group.json")
    obj = Schema_.model_validate(payload)

    assert obj.id == "urn:ietf:params:scim:schemas:core:2.0:Group"
    assert obj.name == "Group"
    assert obj.description == "Group"
    assert obj.attributes[0].name == "displayName"
    assert obj.attributes[0].type == "string"
    assert not obj.attributes[0].multi_valued
    assert obj.attributes[0].description == (
        "A human-readable name for the Group. REQUIRED."
    )
    assert not obj.attributes[0].required
    assert not obj.attributes[0].case_exact
    assert obj.attributes[0].mutability == Mutability.read_write
    assert obj.attributes[0].returned == Returned.default
    assert obj.attributes[0].uniqueness == Uniqueness.none
    assert obj.attributes[1].name == "members"
    assert obj.attributes[1].type == "complex"
    assert obj.attributes[1].multi_valued
    assert obj.attributes[1].description == "A list of members of the Group."
    assert not obj.attributes[1].required
    assert obj.attributes[1].sub_attributes[0].name == "value"
    assert obj.attributes[1].sub_attributes[0].type == "string"
    assert not obj.attributes[1].sub_attributes[0].multi_valued
    assert (
        obj.attributes[1].sub_attributes[0].description
        == "Identifier of the member of this Group."
    )
    assert not obj.attributes[1].sub_attributes[0].required
    assert not obj.attributes[1].sub_attributes[0].case_exact
    assert obj.attributes[1].sub_attributes[0].mutability == Mutability.immutable
    assert obj.attributes[1].sub_attributes[0].returned == Returned.default
    assert obj.attributes[1].sub_attributes[0].uniqueness == Uniqueness.none
    assert obj.attributes[1].sub_attributes[1].name == "$ref"
    assert obj.attributes[1].sub_attributes[1].type == "reference"
    assert obj.attributes[1].sub_attributes[1].reference_types == ["User", "Group"]
    assert not obj.attributes[1].sub_attributes[1].multi_valued
    assert obj.attributes[1].sub_attributes[1].description == (
        "The URI corresponding to a SCIM resource that is a member of this Group."
    )
    assert not obj.attributes[1].sub_attributes[1].required
    assert not obj.attributes[1].sub_attributes[1].case_exact
    assert obj.attributes[1].sub_attributes[1].mutability == Mutability.immutable
    assert obj.attributes[1].sub_attributes[1].returned == Returned.default
    assert obj.attributes[1].sub_attributes[1].uniqueness == Uniqueness.none
    assert obj.attributes[1].sub_attributes[2].name == "type"
    assert obj.attributes[1].sub_attributes[2].type == "string"
    assert not obj.attributes[1].sub_attributes[2].multi_valued
    assert obj.attributes[1].sub_attributes[2].description == (
        "A label indicating the type of resource, e.g., 'User' or 'Group'."
    )
    assert not obj.attributes[1].sub_attributes[2].required
    assert not obj.attributes[1].sub_attributes[2].case_exact
    assert obj.attributes[1].sub_attributes[2].canonical_values == ["User", "Group"]
    assert obj.attributes[1].sub_attributes[2].mutability == Mutability.immutable
    assert obj.attributes[1].sub_attributes[2].returned == Returned.default
    assert obj.attributes[1].sub_attributes[2].uniqueness == Uniqueness.none
    assert obj.attributes[1].mutability == Mutability.read_write
    assert obj.attributes[1].returned == Returned.default
    assert obj.meta.resource_type == "Schema"
    assert (
        obj.meta.location == "/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:Group"
    )

    assert obj.model_dump(exclude_unset=True) == payload


def test_empty_attribute():
    """Attributes must at least have a name to be pythonizable."""
    assert Attribute().to_python() is None
