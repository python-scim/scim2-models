from typing import Annotated

import pytest

from scim2_models import URN
from scim2_models import EnterpriseUser
from scim2_models import Path
from scim2_models import Returned
from scim2_models import User
from scim2_models.attributes import ComplexAttribute
from scim2_models.resources.resource import Resource

ENTERPRISE = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"


class Detail(ComplexAttribute):
    default_returned: str | None = None
    request_returned: Annotated[str | None, Returned.request] = None


class Report(Resource):
    __schema__ = URN("urn:org:example:Report")

    request_returned: Annotated[str | None, Returned.request] = None
    detail: Detail | None = None
    never_detail: Annotated[Detail | None, Returned.never] = None
    request_detail: Annotated[Detail | None, Returned.request] = None


def returns(model, path, **parameters):
    parameters = {
        name: [Path[model](value) for value in values]
        for name, values in parameters.items()
    }
    return Path[model](path) in Path[model].iter_paths(**parameters)


@pytest.mark.parametrize(
    ("parameters", "path", "expected"),
    [
        ({"attributes": []}, "userName", True),
        ({"attributes": []}, "password", False),
        ({"attributes": ["password"]}, "password", False),
        ({"attributes": ["userName"]}, "userName", True),
        ({"attributes": ["USERNAME"]}, "userName", True),
        ({"attributes": ["userName"]}, "emails", False),
        ({"attributes": ["emails.value"]}, "emails", True),
        ({"attributes": ["emails.value"]}, "emails.value", True),
        ({"attributes": ["emails.value"]}, "emails.type", False),
        ({"attributes": ["name"]}, "name.givenName", True),
        ({"excluded_attributes": ["emails.type"]}, "emails", True),
        ({"excluded_attributes": ["emails.type"]}, "emails.type", False),
        ({"excluded_attributes": ["emails"]}, "emails.value", False),
    ],
)
def test_returns_follows_the_returned_annotation(parameters, path, expected):
    """A core attribute is yielded when the response serializer keeps it."""
    assert returns(User[EnterpriseUser], path, **parameters) is expected


@pytest.mark.parametrize(
    ("parameters", "path", "expected"),
    [
        ({"excluded_attributes": [ENTERPRISE]}, f"{ENTERPRISE}:manager", False),
        ({"excluded_attributes": [ENTERPRISE]}, f"{ENTERPRISE}:manager.value", False),
        ({"excluded_attributes": [ENTERPRISE]}, "userName", True),
        (
            {"excluded_attributes": [f"{ENTERPRISE}:manager"]},
            f"{ENTERPRISE}:manager",
            False,
        ),
        ({"attributes": [f"{ENTERPRISE}:manager"]}, f"{ENTERPRISE}:manager", True),
        (
            {"attributes": [f"{ENTERPRISE}:manager"]},
            f"{ENTERPRISE}:employeeNumber",
            False,
        ),
        ({"attributes": [ENTERPRISE]}, f"{ENTERPRISE}:manager.value", True),
    ],
)
def test_returns_checks_the_extension(parameters, path, expected):
    """An extension attribute is removed with its extension."""
    assert returns(User[EnterpriseUser], path, **parameters) is expected


@pytest.mark.parametrize(
    ("parameters", "path", "expected"),
    [
        ({"attributes": []}, "requestReturned", False),
        ({"attributes": ["requestReturned"]}, "requestReturned", True),
        (
            {"attributes": ["neverDetail.defaultReturned"]},
            "neverDetail.defaultReturned",
            False,
        ),
        ({"attributes": ["detail"]}, "detail.requestReturned", False),
        ({"attributes": ["detail.requestReturned"]}, "detail.requestReturned", True),
        ({"attributes": ["requestDetail"]}, "requestDetail.defaultReturned", True),
    ],
)
def test_returns_checks_each_level(parameters, path, expected):
    """A sub-attribute is kept only when its parent is kept too."""
    assert returns(Report, path, **parameters) is expected


@pytest.mark.xfail(
    strict=True,
    reason="a request attribute is only kept when requested by its exact name",
)
def test_requesting_a_sub_attribute_keeps_its_request_parent():
    """Requesting requestDetail.defaultReturned should keep requestDetail, as for a default attribute."""
    assert returns(
        Report, "requestDetail", attributes=["requestDetail.defaultReturned"]
    )


def test_without_projection_every_attribute_is_yielded():
    """Without attributes nor excluded attributes, the Returned annotations filter nothing."""
    assert returns(User, "password")


def test_the_projection_is_not_cached():
    """Two calls with different attributes yield different paths."""
    assert returns(User, "userName", attributes=["userName"])
    assert not returns(User, "userName", attributes=["emails"])


def test_the_extension_itself_follows_the_projection():
    """The path to the whole extension is removed with it."""
    assert not returns(
        User[EnterpriseUser], ENTERPRISE, excluded_attributes=[ENTERPRISE]
    )
