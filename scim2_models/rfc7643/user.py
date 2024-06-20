from enum import Enum
from typing import Annotated
from typing import List
from typing import Optional

from pydantic import EmailStr

from ..base import CaseExact
from ..base import ComplexAttribute
from ..base import MultiValuedComplexAttribute
from ..base import Mutability
from ..base import Reference
from ..base import Required
from ..base import Uniqueness
from .group import GroupMember
from .resource import Resource


class Name(ComplexAttribute):
    formatted: Optional[str] = None
    """The full name, including all middle names, titles, and suffixes as
    appropriate, formatted for display (e.g., 'Ms. Barbara J Jensen, III')."""

    family_name: Optional[str] = None
    """The family name of the User, or last name in most Western languages
    (e.g., 'Jensen' given the full name 'Ms. Barbara J Jensen, III')."""

    given_name: Optional[str] = None
    """The given name of the User, or first name in most Western languages
    (e.g., 'Barbara' given the full name 'Ms. Barbara J Jensen, III')."""

    middle_name: Optional[str] = None
    """The middle name(s) of the User (e.g., 'Jane' given the full name 'Ms.
    Barbara J Jensen, III')."""

    honorific_prefix: Optional[str] = None
    """The honorific prefix(es) of the User, or title in most Western languages
    (e.g., 'Ms.' given the full name 'Ms. Barbara J Jensen, III')."""

    honorific_suffix: Optional[str] = None
    """The honorific suffix(es) of the User, or suffix in most Western
    languages (e.g., 'III' given the full name 'Ms. Barbara J Jensen, III')."""


class Email(MultiValuedComplexAttribute):
    class Type(str, Enum):
        work = "work"
        home = "home"
        other = "other"

    value: Optional[EmailStr] = None
    """Email addresses for the user."""

    display: Optional[str] = None
    """A human-readable name, primarily used for display purposes."""

    type: Optional[Type] = None
    """A label indicating the attribute's function, e.g., 'work' or 'home'."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred mailing address or primary email
    address."""


class PhoneNumber(MultiValuedComplexAttribute):
    class Type(str, Enum):
        work = "work"
        home = "home"
        mobile = "mobile"
        fax = "fax"
        pager = "pager"
        other = "other"

    value: Optional[str] = None
    """Phone number of the User."""

    display: Optional[str] = None
    """A human-readable name, primarily used for display purposes."""

    type: Optional[Type] = None
    """A label indicating the attribute's function, e.g., 'work', 'home',
    'mobile'."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred phone number or primary phone
    number."""


class Im(MultiValuedComplexAttribute):
    class Type(str, Enum):
        aim = "aim"
        gtalk = "gtalk"
        icq = "icq"
        xmpp = "xmpp"
        msn = "msn"
        skype = "skype"
        qq = "qq"
        yahoo = "yahoo"

    value: Optional[str] = None
    """Instant messaging address for the User."""

    display: Optional[str] = None
    """A human-readable name, primarily used for display purposes."""

    type: Optional[Type] = None
    """A label indicating the attribute's function, e.g., 'aim', 'gtalk',
    'xmpp'."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred messenger or primary messenger."""


class Photo(MultiValuedComplexAttribute):
    class Type(str, Enum):
        photo = "photo"
        thumbnail = "thumbnail"

    value: Annotated[Optional[Reference], CaseExact.true] = None
    """URL of a photo of the User."""

    display: Optional[str] = None
    """A human-readable name, primarily used for display purposes."""

    type: Optional[Type] = None
    """A label indicating the attribute's function, i.e., 'photo' or
    'thumbnail'."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred photo or thumbnail."""


class Address(MultiValuedComplexAttribute):
    class Type(str, Enum):
        work = "work"
        home = "home"
        other = "other"

    formatted: Optional[str] = None
    """The full mailing address, formatted for display or use with a mailing
    label."""

    street_address: Optional[str] = None
    """The full street address component, which may include house number,
    street name, P.O.

    box, and multi-line extended street address information.
    """

    locality: Optional[str] = None
    """The city or locality component."""

    region: Optional[str] = None
    """The state or region component."""

    postal_code: Optional[str] = None
    """The zip code or postal code component."""

    country: Optional[str] = None
    """The country name component."""

    type: Optional[Type] = None
    """A label indicating the attribute's function, e.g., 'work' or 'home'."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred photo or thumbnail."""


class Entitlement(MultiValuedComplexAttribute):
    value: Optional[str] = None
    """The value of an entitlement."""

    display: Optional[str] = None
    """A human-readable name, primarily used for display purposes."""

    type: Optional[str] = None
    """A label indicating the attribute's function."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute."""


class Role(MultiValuedComplexAttribute):
    value: Optional[str] = None
    """The value of a role."""

    display: Optional[str] = None
    """A human-readable name, primarily used for display purposes."""

    type: Optional[str] = None
    """A label indicating the attribute's function."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute."""


class X509Certificate(MultiValuedComplexAttribute):
    value: Annotated[Optional[bytes], CaseExact.true] = None
    """The value of an X.509 certificate."""

    display: Optional[str] = None
    """A human-readable name, primarily used for display purposes."""

    type: Optional[str] = None
    """A label indicating the attribute's function."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute."""


class User(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]

    user_name: Annotated[Optional[str], Uniqueness.server, Required.true] = None
    """Unique identifier for the User, typically used by the user to directly
    authenticate to the service provider."""

    name: Optional[Name] = None
    """The components of the user's real name."""

    display_name: Optional[str] = None
    """The name of the User, suitable for display to end-users."""

    nick_name: Optional[str] = None
    """The casual way to address the user in real life, e.g., 'Bob' or 'Bobby'
    instead of 'Robert'."""

    profile_url: Optional[Reference] = None
    """A fully qualified URL pointing to a page representing the User's online
    profile."""

    title: Optional[str] = None
    """The user's title, such as "Vice President"."""

    user_type: Optional[str] = None
    """Used to identify the relationship between the organization and the user.

    Typical values used might be 'Contractor', 'Employee', 'Intern',
    'Temp', 'External', and 'Unknown', but any value may be used.
    """

    preferred_language: Optional[str] = None
    """Indicates the User's preferred written or spoken language.

    Generally used for selecting a localized user interface; e.g.,
    'en_US' specifies the language English and country US.
    """

    locale: Optional[str] = None
    """Used to indicate the User's default location for purposes of localizing
    items such as currency, date time format, or numerical representations."""

    timezone: Optional[str] = None
    """The User's time zone in the 'Olson' time zone database format, e.g.,
    'America/Los_Angeles'."""

    active: Optional[bool] = None
    """A Boolean value indicating the User's administrative status."""

    password: Annotated[Optional[str], Mutability.write_only] = None
    """The User's cleartext password."""

    emails: Optional[List[Email]] = None
    """Email addresses for the user."""

    phone_numbers: Optional[List[PhoneNumber]] = None
    """Phone numbers for the User."""

    ims: Optional[List[Im]] = None
    """Instant messaging addresses for the User."""

    photos: Optional[List[Photo]] = None
    """URLs of photos of the User."""

    addresses: Optional[List[Address]] = None
    """A physical mailing address for this User."""

    groups: Optional[List[GroupMember]] = None
    """A list of groups to which the user belongs, either through direct
    membership, through nested groups, or dynamically calculated."""

    entitlements: Optional[List[Entitlement]] = None
    """A list of entitlements for the User that represent a thing the User
    has."""

    roles: Optional[List[Role]] = None
    """A list of roles for the User that collectively represent who the User
    is, e.g., 'Student', 'Faculty'."""

    x509_certificates: Optional[List[X509Certificate]] = None
    """A list of certificates issued to the User."""
