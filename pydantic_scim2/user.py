from enum import Enum
from typing import List
from typing import Optional

from pydantic import AnyUrl
from pydantic import EmailStr
from pydantic import Field

from .base import SCIM2Model
from .group import GroupMember
from .resource import Resource


class Name(SCIM2Model):
    formatted: Optional[str] = Field(
        None,
        description="The full name, including all middle names, titles, and suffixes as appropriate, formatted for display (e.g., 'Ms. Barbara J Jensen, III').",
    )
    family_name: Optional[str] = Field(
        None,
        description="The family name of the User, or last name in most Western languages (e.g., 'Jensen' given the full name 'Ms. Barbara J Jensen, III').",
    )
    given_name: Optional[str] = Field(
        None,
        description="The given name of the User, or first name in most Western languages (e.g., 'Barbara' given the full name 'Ms. Barbara J Jensen, III').",
    )
    middle_name: Optional[str] = Field(
        None,
        description="The middle name(s) of the User (e.g., 'Jane' given the full name 'Ms. Barbara J Jensen, III').",
    )
    honorific_prefix: Optional[str] = Field(
        None,
        description="The honorific prefix(es) of the User, or title in most Western languages (e.g., 'Ms.' given the full name 'Ms. Barbara J Jensen, III').",
    )
    honorific_suffix: Optional[str] = Field(
        None,
        description="The honorific suffix(es) of the User, or suffix in most Western languages (e.g., 'III' given the full name 'Ms. Barbara J Jensen, III').",
    )


class EmailKind(str, Enum):
    work = "work"
    home = "home"
    other = "other"


class Email(SCIM2Model):
    value: Optional[EmailStr] = Field(
        None,
        description="Email addresses for the user.  The value SHOULD be canonicalized by the service provider, e.g., 'bjensen@example.com' instead of 'bjensen@EXAMPLE.COM'. Canonical type values of 'work', 'home', and 'other'.",
    )
    display: Optional[str] = Field(
        None,
        description="A human-readable name, primarily used for display purposes.  READ-ONLY.",
    )
    type: Optional[EmailKind] = Field(
        None,
        description="A label indicating the attribute's function, e.g., 'work' or 'home'.",
    )
    primary: Optional[bool] = Field(
        None,
        description="A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred mailing address or primary email address.  The primary attribute value 'true' MUST appear no more than once.",
    )


class PhoneNumberKind(str, Enum):
    work = "work"
    home = "home"
    mobile = "mobile"
    fax = "fax"
    pager = "pager"
    other = "other"


class PhoneNumber(SCIM2Model):
    value: Optional[str] = Field(None, description="Phone number of the User.")
    display: Optional[str] = Field(
        None,
        description="A human-readable name, primarily used for display purposes.  READ-ONLY.",
    )
    type: Optional[PhoneNumberKind] = Field(
        None,
        description="A label indicating the attribute's function, e.g., 'work', 'home', 'mobile'.",
    )
    primary: Optional[bool] = Field(
        None,
        description="A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred phone number or primary phone number.  The primary attribute value 'true' MUST appear no more than once.",
    )


class ImKind(str, Enum):
    aim = "aim"
    gtalk = "gtalk"
    icq = "icq"
    xmpp = "xmpp"
    msn = "msn"
    skype = "skype"
    qq = "qq"
    yahoo = "yahoo"


class Im(SCIM2Model):
    value: Optional[str] = Field(
        None, description="Instant messaging address for the User."
    )
    display: Optional[str] = Field(
        None,
        description="A human-readable name, primarily used for display purposes.  READ-ONLY.",
    )
    type: Optional[ImKind] = Field(
        None,
        description="A label indicating the attribute's function, e.g., 'aim', 'gtalk', 'xmpp'.",
    )
    primary: Optional[bool] = Field(
        None,
        description="A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred messenger or primary messenger.  The primary attribute value 'true' MUST appear no more than once.",
    )


class PhotoKind(str, Enum):
    photo = "photo"
    thumbnail = "thumbnail"


class Photo(SCIM2Model):
    value: Optional[AnyUrl] = Field(None, description="URL of a photo of the User.")
    display: Optional[str] = Field(
        None,
        description="A human-readable name, primarily used for display purposes.  READ-ONLY.",
    )
    type: Optional[PhotoKind] = Field(
        None,
        description="A label indicating the attribute's function, i.e., 'photo' or 'thumbnail'.",
    )
    primary: Optional[bool] = Field(
        None,
        description="A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred photo or thumbnail.  The primary attribute value 'true' MUST appear no more than once.",
    )


class AddressKind(str, Enum):
    work = "work"
    home = "home"
    other = "other"


class Address(SCIM2Model):
    formatted: Optional[str] = Field(
        None,
        description="The full mailing address, formatted for display or use with a mailing label.  This attribute MAY contain newlines.",
    )
    street_address: Optional[str] = Field(
        None,
        description="The full street address component, which may include house number, street name, P.O. box, and multi-line extended street address information.  This attribute MAY contain newlines.",
    )
    locality: Optional[str] = Field(None, description="The city or locality component.")
    region: Optional[str] = Field(None, description="The state or region component.")
    postal_code: Optional[str] = Field(
        None, description="The zip code or postal code component."
    )
    country: Optional[str] = Field(None, description="The country name component.")
    type: Optional[AddressKind] = Field(
        None,
        description="A label indicating the attribute's function, e.g., 'work' or 'home'.",
    )
    primary: Optional[bool] = Field(
        None,
        description="A Boolean value indicating the 'primary' or preferred attribute value for this attribute, e.g., the preferred photo or thumbnail.  The primary attribute value 'true' MUST appear no more than once.",
    )


class Entitlement(SCIM2Model):
    value: Optional[str] = Field(None, description="The value of an entitlement.")
    display: Optional[str] = Field(
        None,
        description="A human-readable name, primarily used for display purposes.  READ-ONLY.",
    )
    type: Optional[str] = Field(
        None, description="A label indicating the attribute's function."
    )
    primary: Optional[bool] = Field(
        None,
        description="A Boolean value indicating the 'primary' or preferred attribute value for this attribute.  The primary attribute value 'true' MUST appear no more than once.",
    )


class Role(SCIM2Model):
    value: Optional[str] = Field(None, description="The value of a role.")
    display: Optional[str] = Field(
        None,
        description="A human-readable name, primarily used for display purposes.  READ-ONLY.",
    )
    type: Optional[str] = Field(
        None, description="A label indicating the attribute's function."
    )
    primary: Optional[bool] = Field(
        None,
        description="A Boolean value indicating the 'primary' or preferred attribute value for this attribute.  The primary attribute value 'true' MUST appear no more than once.",
    )


class X509Certificate(SCIM2Model):
    value: Optional[str] = Field(None, description="The value of an X.509 certificate.")
    display: Optional[str] = Field(
        None,
        description="A human-readable name, primarily used for display purposes.  READ-ONLY.",
    )
    type: Optional[str] = Field(
        None, description="A label indicating the attribute's function."
    )
    primary: Optional[bool] = Field(
        None,
        description="A Boolean value indicating the 'primary' or preferred attribute value for this attribute.  The primary attribute value 'true' MUST appear no more than once.",
    )


class User(Resource):
    user_name: str = Field(
        ...,
        description="Unique identifier for the User, typically used by the user to directly authenticate to the service provider.  Each User MUST include a non-empty userName value.  This identifier MUST be unique across the service provider's entire set of Users.  REQUIRED.",
    )
    name: Optional[Name] = Field(
        None,
        description="The components of the user's real name.  Providers MAY return just the full name as a single string in the formatted sub-attribute, or they MAY return just the individual component attributes using the other sub-attributes, or they MAY return both.  If both variants are returned, they SHOULD be describing the same name, with the formatted name indicating how the component attributes should be combined.",
    )
    display_name: Optional[str] = Field(
        None,
        description="The name of the User, suitable for display to end-users.  The name SHOULD be the full name of the User being described, if known.",
    )
    nick_name: Optional[str] = Field(
        None,
        description="The casual way to address the user in real life, e.g., 'Bob' or 'Bobby' instead of 'Robert'.  This attribute SHOULD NOT be used to represent a User's username (e.g., 'bjensen' or 'mpepperidge').",
    )
    profile_url: Optional[AnyUrl] = Field(
        None,
        description="A fully qualified URL pointing to a page representing the User's online profile.",
    )
    title: Optional[str] = Field(
        None, description='The user\'s title, such as "Vice President."'
    )
    user_type: Optional[str] = Field(
        None,
        description="Used to identify the relationship between the organization and the user.  Typical values used might be 'Contractor', 'Employee', 'Intern', 'Temp', 'External', and 'Unknown', but any value may be used.",
    )
    preferred_language: Optional[str] = Field(
        None,
        description="Indicates the User's preferred written or spoken language.  Generally used for selecting a localized user interface; e.g., 'en_US' specifies the language English and country US.",
    )
    locale: Optional[str] = Field(
        None,
        description="Used to indicate the User's default location for purposes of localizing items such as currency, date time format, or numerical representations.",
    )
    timezone: Optional[str] = Field(
        None,
        description="The User's time zone in the 'Olson' time zone database format, e.g., 'America/Los_Angeles'.",
    )
    active: Optional[bool] = Field(
        None, description="A Boolean value indicating the User's administrative status."
    )
    password: Optional[str] = Field(
        None,
        description="The User's cleartext password.  This attribute is intended to be used as a means to specify an initial password when creating a new User or to reset an existing User's password.",
    )
    emails: Optional[List[Email]] = Field(
        None,
        description="Email addresses for the user.  The value SHOULD be canonicalized by the service provider, e.g., 'bjensen@example.com' instead of 'bjensen@EXAMPLE.COM'. Canonical type values of 'work', 'home', and 'other'.",
    )
    phone_numbers: Optional[List[PhoneNumber]] = Field(
        None,
        description="Phone numbers for the User.  The value SHOULD be canonicalized by the service provider according to the format specified in RFC 3966, e.g., 'tel:+1-201-555-0123'. Canonical type values of 'work', 'home', 'mobile', 'fax', 'pager', and 'other'.",
    )
    ims: Optional[List[Im]] = Field(
        None, description="Instant messaging addresses for the User."
    )
    photos: Optional[List[Photo]] = Field(
        None, description="URLs of photos of the User."
    )
    addresses: Optional[List[Address]] = Field(
        None,
        description="A physical mailing address for this User. Canonical type values of 'work', 'home', and 'other'.  This attribute is a complex type with the following sub-attributes.",
    )
    groups: Optional[List[GroupMember]] = Field(
        None,
        description="A list of groups to which the user belongs, either through direct membership, through nested groups, or dynamically calculated.",
    )
    entitlements: Optional[List[Entitlement]] = Field(
        None,
        description="A list of entitlements for the User that represent a thing the User has.",
    )
    roles: Optional[List[Role]] = Field(
        None,
        description="A list of roles for the User that collectively represent who the User is, e.g., 'Student', 'Faculty'.",
    )
    x509Certificates: Optional[List[X509Certificate]] = Field(
        None, description="A list of certificates issued to the User."
    )
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
