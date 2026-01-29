from enum import Enum
from typing import TYPE_CHECKING
from typing import Annotated
from typing import ClassVar

from pydantic import Base64Bytes
from pydantic import EmailStr
from pydantic import Field

from ..annotations import CaseExact
from ..annotations import Mutability
from ..annotations import Required
from ..annotations import Returned
from ..annotations import Uniqueness
from ..attributes import ComplexAttribute
from ..path import URN
from ..reference import External
from ..reference import Reference
from .resource import AnyExtension
from .resource import Resource

if TYPE_CHECKING:
    from .group import Group


class Name(ComplexAttribute):
    formatted: str | None = None
    """The full name, including all middle names, titles, and suffixes as
    appropriate, formatted for display (e.g., 'Ms. Barbara J Jensen, III')."""

    family_name: str | None = None
    """The family name of the User, or last name in most Western languages
    (e.g., 'Jensen' given the full name 'Ms. Barbara J Jensen, III')."""

    given_name: str | None = None
    """The given name of the User, or first name in most Western languages
    (e.g., 'Barbara' given the full name 'Ms. Barbara J Jensen, III')."""

    middle_name: str | None = None
    """The middle name(s) of the User (e.g., 'Jane' given the full name 'Ms.
    Barbara J Jensen, III')."""

    honorific_prefix: str | None = None
    """The honorific prefix(es) of the User, or title in most Western languages
    (e.g., 'Ms.' given the full name 'Ms. Barbara J Jensen, III')."""

    honorific_suffix: str | None = None
    """The honorific suffix(es) of the User, or suffix in most Western
    languages (e.g., 'III' given the full name 'Ms. Barbara J Jensen, III')."""


class Email(ComplexAttribute):
    class Type(str, Enum):
        work = "work"
        home = "home"
        other = "other"

    value: EmailStr | None = None
    """Email addresses for the user."""

    display: str | None = None
    """A human-readable name, primarily used for display purposes."""

    type: Type | None = Field(None, examples=["work", "home", "other"])
    """A label indicating the attribute's function, e.g., 'work' or 'home'."""

    primary: bool | None = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred mailing address or primary email
    address."""


class PhoneNumber(ComplexAttribute):
    class Type(str, Enum):
        work = "work"
        home = "home"
        mobile = "mobile"
        fax = "fax"
        pager = "pager"
        other = "other"

    value: str | None = None
    """Phone number of the User."""

    display: str | None = None
    """A human-readable name, primarily used for display purposes."""

    type: Type | None = Field(
        None, examples=["work", "home", "mobile", "fax", "pager", "other"]
    )
    """A label indicating the attribute's function, e.g., 'work', 'home',
    'mobile'."""

    primary: bool | None = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred phone number or primary phone
    number."""


class Im(ComplexAttribute):
    class Type(str, Enum):
        aim = "aim"
        gtalk = "gtalk"
        icq = "icq"
        xmpp = "xmpp"
        msn = "msn"
        skype = "skype"
        qq = "qq"
        yahoo = "yahoo"

    value: str | None = None
    """Instant messaging address for the User."""

    display: str | None = None
    """A human-readable name, primarily used for display purposes."""

    type: Type | None = Field(
        None, examples=["aim", "gtalk", "icq", "xmpp", "msn", "skype", "qq", "yahoo"]
    )
    """A label indicating the attribute's function, e.g., 'aim', 'gtalk',
    'xmpp'."""

    primary: bool | None = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred messenger or primary messenger."""


class Photo(ComplexAttribute):
    class Type(str, Enum):
        photo = "photo"
        thumbnail = "thumbnail"

    value: Annotated[Reference[External] | None, CaseExact.true] = None
    """URL of a photo of the User."""

    display: str | None = None
    """A human-readable name, primarily used for display purposes."""

    type: Type | None = Field(None, examples=["photo", "thumbnail"])
    """A label indicating the attribute's function, i.e., 'photo' or
    'thumbnail'."""

    primary: bool | None = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred photo or thumbnail."""


class Address(ComplexAttribute):
    class Type(str, Enum):
        work = "work"
        home = "home"
        other = "other"

    formatted: str | None = None
    """The full mailing address, formatted for display or use with a mailing
    label."""

    street_address: str | None = None
    """The full street address component, which may include house number,
    street name, P.O.

    box, and multi-line extended street address information.
    """

    locality: str | None = None
    """The city or locality component."""

    region: str | None = None
    """The state or region component."""

    postal_code: str | None = None
    """The zip code or postal code component."""

    country: str | None = None
    """The country name component."""

    type: Type | None = Field(None, examples=["work", "home", "other"])
    """A label indicating the attribute's function, e.g., 'work' or 'home'."""

    primary: bool | None = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred address."""


class Entitlement(ComplexAttribute):
    value: str | None = None
    """The value of an entitlement."""

    display: str | None = None
    """A human-readable name, primarily used for display purposes."""

    type: str | None = None
    """A label indicating the attribute's function."""

    primary: bool | None = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute."""


class GroupMembership(ComplexAttribute):
    value: Annotated[str | None, Mutability.read_only] = None
    """The identifier of the User's group."""

    ref: Annotated[
        Reference["Group"] | None,
        Mutability.read_only,
    ] = Field(None, serialization_alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""

    display: Annotated[str | None, Mutability.read_only] = None
    """A human-readable name, primarily used for display purposes."""

    type: Annotated[str | None, Mutability.read_only] = Field(
        None, examples=["direct", "indirect"]
    )
    """A label indicating the attribute's function, e.g., 'direct' or
    'indirect'."""


class Role(ComplexAttribute):
    value: str | None = None
    """The value of a role."""

    display: str | None = None
    """A human-readable name, primarily used for display purposes."""

    type: str | None = None
    """A label indicating the attribute's function."""

    primary: bool | None = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute."""


class X509Certificate(ComplexAttribute):
    value: Annotated[Base64Bytes | None, CaseExact.true] = None
    """The value of an X.509 certificate."""

    display: str | None = None
    """A human-readable name, primarily used for display purposes."""

    type: str | None = None
    """A label indicating the attribute's function."""

    primary: bool | None = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute."""


class User(Resource[AnyExtension]):
    __schema__ = URN("urn:ietf:params:scim:schemas:core:2.0:User")

    user_name: Annotated[str | None, Uniqueness.server, Required.true] = None
    """Unique identifier for the User, typically used by the user to directly
    authenticate to the service provider."""

    name: Name | None = None
    """The components of the user's real name."""

    Name: ClassVar[type[ComplexAttribute]] = Name

    display_name: str | None = None
    """The name of the User, suitable for display to end-users."""

    nick_name: str | None = None
    """The casual way to address the user in real life, e.g., 'Bob' or 'Bobby'
    instead of 'Robert'."""

    profile_url: Reference[External] | None = None
    """A fully qualified URL pointing to a page representing the User's online
    profile."""

    title: str | None = None
    """The user's title, such as "Vice President"."""

    user_type: str | None = None
    """Used to identify the relationship between the organization and the user.

    Typical values used might be 'Contractor', 'Employee', 'Intern',
    'Temp', 'External', and 'Unknown', but any value may be used.
    """

    preferred_language: str | None = None
    """Indicates the User's preferred written or spoken language.

    Generally used for selecting a localized user interface; e.g.,
    'en_US' specifies the language English and country US.
    """

    locale: str | None = None
    """Used to indicate the User's default location for purposes of localizing
    items such as currency, date time format, or numerical representations."""

    timezone: str | None = None
    """The User's time zone in the 'Olson' time zone database format, e.g.,
    'America/Los_Angeles'."""

    active: bool | None = None
    """A Boolean value indicating the User's administrative status."""

    password: Annotated[str | None, Mutability.write_only, Returned.never] = None
    """The User's cleartext password."""

    emails: list[Email] | None = None
    """Email addresses for the user."""

    Emails: ClassVar[type[ComplexAttribute]] = Email

    phone_numbers: list[PhoneNumber] | None = None
    """Phone numbers for the User."""

    PhoneNumbers: ClassVar[type[ComplexAttribute]] = PhoneNumber

    ims: list[Im] | None = None
    """Instant messaging addresses for the User."""

    Ims: ClassVar[type[ComplexAttribute]] = Im

    photos: list[Photo] | None = None
    """URLs of photos of the User."""

    Photos: ClassVar[type[ComplexAttribute]] = Photo

    addresses: list[Address] | None = None
    """A physical mailing address for this User."""

    Addresses: ClassVar[type[ComplexAttribute]] = Address

    groups: Annotated[list[GroupMembership] | None, Mutability.read_only] = None
    """A list of groups to which the user belongs, either through direct
    membership, through nested groups, or dynamically calculated."""

    Groups: ClassVar[type[ComplexAttribute]] = GroupMembership

    entitlements: list[Entitlement] | None = None
    """A list of entitlements for the User that represent a thing the User
    has."""

    Entitlements: ClassVar[type[ComplexAttribute]] = Entitlement

    roles: list[Role] | None = None
    """A list of roles for the User that collectively represent who the User
    is, e.g., 'Student', 'Faculty'."""

    Roles: ClassVar[type[ComplexAttribute]] = Role

    x509_certificates: list[X509Certificate] | None = None
    """A list of certificates issued to the User."""

    X509Certificates: ClassVar[type[ComplexAttribute]] = X509Certificate
