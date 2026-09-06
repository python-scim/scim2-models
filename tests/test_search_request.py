import pytest
from pydantic import ValidationError

from scim2_models import EnterpriseUser
from scim2_models import Group
from scim2_models import InvalidFilterException
from scim2_models import InvalidPathException
from scim2_models import User
from scim2_models.messages.search_request import SearchRequest


def test_search_request():
    SearchRequest(
        attributes=["userName", "displayName"],
        filter='userName Eq "john"',
        sort_by="userName",
        sort_order=SearchRequest.SortOrder.ascending,
        start_index=1,
        count=10,
    )

    SearchRequest(
        excluded_attributes=["timezone", "phoneNumbers"],
        filter='userName Eq "john"',
        sort_by="userName",
        sort_order=SearchRequest.SortOrder.ascending,
        start_index=1,
        count=10,
    )


def test_start_index_floor():
    """Test that startIndex values less than 0 are interpreted as 0.

    https://datatracker.ietf.org/doc/html/rfc7644#section-3.4.2.4

        A value less than 1 SHALL be interpreted as 1.
    """
    sr = SearchRequest(start_index=100)
    assert sr.start_index == 100

    sr = SearchRequest(start_index=0)
    assert sr.start_index == 1


def test_count_floor():
    """Test that count values less than 1 are interpreted as 1.

    https://datatracker.ietf.org/doc/html/rfc7644#section-3.4.2.4

        A negative value SHALL be interpreted as 0.
    """
    sr = SearchRequest(count=100)
    assert sr.count == 100

    sr = SearchRequest(count=-1)
    assert sr.count == 0


def test_attributes_or_excluded_attributes():
    """Test that a validation error is raised when both 'attributes' and 'excludedAttributes' are filled at the same time.

    https://datatracker.ietf.org/doc/html/rfc7644#section-3.9

        Clients MAY request a partial resource representation on any
        operation that returns a resource within the response by specifying
        either of the mutually exclusive URL query parameters "attributes" or
        "excludedAttributes"...
    """
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
        "attributes": ["userName"],
        "excludedAttributes": [
            "displayName",
        ],
    }
    with pytest.raises(ValidationError):
        SearchRequest.model_validate(payload)


def test_index_0_properties():
    req = SearchRequest(start_index=1, count=10)
    assert req.start_index_0 == 0
    assert req.stop_index_0 == 10


def test_search_request_valid_attributes():
    """Test that valid attribute paths are accepted."""
    valid_data = {
        "attributes": ["userName", "name.familyName", "emails.value"],
        "excluded_attributes": None,
    }

    request = SearchRequest.model_validate(valid_data)
    assert request.attributes == ["userName", "name.familyName", "emails.value"]


def test_search_request_valid_excluded_attributes():
    """Test that valid excluded attribute paths are accepted."""
    valid_data = {
        "attributes": None,
        "excluded_attributes": ["password", "meta.version"],
    }

    request = SearchRequest.model_validate(valid_data)
    assert request.excluded_attributes == ["password", "meta.version"]


def test_search_request_valid_sort_by():
    """Test that valid sort_by paths are accepted."""
    valid_data = {
        "sort_by": "meta.lastModified",
    }

    request = SearchRequest.model_validate(valid_data)
    assert request.sort_by == "meta.lastModified"


def test_search_request_valid_urn_attributes():
    """Test that URN attribute paths are accepted."""
    valid_data = {
        "attributes": [
            "urn:ietf:params:scim:schemas:core:2.0:User:userName",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
        ],
    }

    request = SearchRequest.model_validate(valid_data)
    assert len(request.attributes) == 2


def test_search_request_invalid_attributes():
    """Test that invalid attribute paths are rejected."""
    invalid_cases = [
        (["123invalid"], "invalid syntax at column 1"),
        (["valid", "invalid..path"], "invalid syntax at column 8"),
        (["invalid@character"], "invalid syntax at column 8"),
    ]

    for attributes, error_match in invalid_cases:
        with pytest.raises(ValidationError, match=error_match):
            SearchRequest.model_validate({"attributes": attributes})


def test_search_request_invalid_excluded_attributes():
    """Test that invalid excluded attribute paths are rejected."""
    invalid_data = {
        "excluded_attributes": ["valid", "123invalid"],  # Second one starts with digit
    }

    with pytest.raises(ValidationError, match="not a valid SCIM path"):
        SearchRequest.model_validate(invalid_data)


def test_search_request_invalid_sort_by():
    """Test that invalid sort_by paths are rejected."""
    invalid_cases = [
        {"sort_by": "123invalid"},  # Starts with digit
        {"sort_by": "invalid..path"},  # Double dots
        {"sort_by": "invalid@char"},  # Invalid character
        {"sort_by": "urn:invalid"},  # Invalid URN
    ]

    for case in invalid_cases:
        with pytest.raises(ValidationError, match="path|Path"):
            SearchRequest.model_validate(case)


def test_search_request_complex_paths_allowed():
    """Test that complex filter paths are allowed in attributes."""
    # Complex paths with filters should be allowed (for now)
    valid_data = {
        "attributes": [
            'emails[type eq "work"].value',
            'groups[display eq "Admin"]',
            "name.familyName",
        ],
    }

    request = SearchRequest.model_validate(valid_data)
    assert len(request.attributes) == 3


def test_comma_separated_attributes():
    """SearchRequest accepts comma-separated strings for attributes."""
    req = SearchRequest.model_validate({"attributes": "userName,displayName"})
    assert req.attributes == ["userName", "displayName"]

    req = SearchRequest.model_validate({"excludedAttributes": "password, phoneNumbers"})
    assert req.excluded_attributes == ["password", "phoneNumbers"]


def test_comma_separated_single_attribute():
    """A single attribute value without comma is accepted as-is."""
    req = SearchRequest.model_validate({"attributes": "userName"})
    assert req.attributes == ["userName"]


def test_comma_separated_empty_string():
    """An empty string produces an empty list."""
    req = SearchRequest.model_validate({"attributes": ""})
    assert req.attributes == []


def test_search_request_empty_lists():
    """Test that empty attribute lists are handled correctly."""
    valid_data = {
        "attributes": [],
        "excluded_attributes": [],
    }

    request = SearchRequest.model_validate(valid_data)
    assert request.attributes == []
    assert request.excluded_attributes == []


def test_search_request_none_values():
    """Test that None values are handled correctly."""
    valid_data = {
        "attributes": None,
        "excluded_attributes": None,
        "sort_by": None,
    }

    request = SearchRequest.model_validate(valid_data)
    assert request.attributes is None
    assert request.excluded_attributes is None
    assert request.sort_by is None


def test_search_request_mutually_exclusive_validation():
    """Test that attributes and excluded_attributes are still mutually exclusive."""
    invalid_data = {
        "attributes": ["userName"],
        "excluded_attributes": ["password"],
    }

    with pytest.raises(ValidationError, match="mutually exclusive"):
        SearchRequest.model_validate(invalid_data)


def test_search_request_integration_with_existing_validation():
    """Test that new path validation works with existing validation."""
    # Valid path syntax but mutually exclusive
    invalid_data = {
        "attributes": ["userName", "emails.value"],
        "excluded_attributes": ["password"],
    }

    with pytest.raises(ValidationError, match="mutually exclusive"):
        SearchRequest.model_validate(invalid_data)

    # Invalid path syntax should fail before mutual exclusion check
    invalid_data = {
        "attributes": ["123invalid"],
        "excluded_attributes": ["password"],
    }

    with pytest.raises(ValidationError, match="path|Path"):
        SearchRequest.model_validate(invalid_data)


def test_a_parameterised_request_resolves_its_filter_against_the_model():
    request = SearchRequest[User].model_validate({"filter": 'userName eq "bjensen"'})
    assert request.filter.match(User(user_name="bjensen"))


def test_a_parameterised_request_rejects_a_comparison_its_attribute_cannot_take():
    with pytest.raises(InvalidFilterException, match="operator 'gt' cannot be applied"):
        SearchRequest[User].model_validate({"filter": "active gt true"})


def test_a_parameterised_request_rejects_an_attribute_the_model_does_not_declare():
    """Naming the served resource type is what makes this a client error rather than an empty page."""
    with pytest.raises(InvalidFilterException, match="Field not found: nonexistent"):
        SearchRequest[User].model_validate({"filter": 'nonexistent eq "x"'})


def test_a_parameterised_request_declares_the_extensions_it_serves():
    payload = {
        "filter": 'urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber eq "1"'
    }
    with pytest.raises(InvalidFilterException, match="Field not found: employeeNumber"):
        SearchRequest[User].model_validate(payload)

    assert SearchRequest[User[EnterpriseUser]].model_validate(payload).filter


def test_a_parameterised_request_resolves_its_sort_by():
    request = SearchRequest[User].model_validate({"sortBy": "userName"})
    assert request.sort_by.field_name == "user_name"

    assert SearchRequest[User].model_validate({"sortBy": "meta.lastModified"}).sort_by
    assert SearchRequest[User].model_validate({"sortBy": "emails.value"}).sort_by


def test_a_parameterised_request_rejects_a_sort_by_the_model_does_not_declare():
    """An order cannot be quietly dropped the way an unknown attributes entry is."""
    with pytest.raises(InvalidPathException, match="Cannot sort on 'nonexistent'"):
        SearchRequest[User].model_validate({"sortBy": "nonexistent"})


def test_a_parameterised_request_rejects_a_sort_by_designating_a_resource():
    """A schema URN names a resource type, which holds no value to order by."""
    with pytest.raises(InvalidPathException):
        SearchRequest[User].model_validate(
            {"sortBy": "urn:ietf:params:scim:schemas:core:2.0:User"}
        )


def test_a_sort_by_on_a_union_answers_to_the_type_declaring_it():
    """§3.4.2.1 has a root query cover types that do not share every attribute."""
    request = SearchRequest[User | Group].model_validate({"sortBy": "userName"})
    assert request.sort_by.field_name == "user_name"

    with pytest.raises(InvalidPathException):
        SearchRequest[User | Group].model_validate({"sortBy": "nonexistent"})


def test_an_unparameterised_request_only_checks_the_filter_syntax():
    """§3.4.2.1 has an endpoint covering several resource types evaluate an undeclared attribute to false."""
    request = SearchRequest.model_validate({"filter": 'nonexistent eq "x"'})
    assert request.filter == 'nonexistent eq "x"'
    assert request.filter.model is None
    assert (
        SearchRequest.model_validate({"sortBy": "userName"}).sort_by.field_name is None
    )


def test_a_request_covering_several_resource_types_takes_a_union():
    """§3.4.2.1 has the server root cover every type it serves."""
    request = SearchRequest[User | Group].model_validate(
        {"filter": 'userName eq "bjensen" or members pr'}
    )
    assert request.filter.models == (User, Group)
    assert request.filter.match(User(user_name="bjensen"))
    assert request.filter.match(Group(display_name="admins", members=[{"value": "u1"}]))


def test_a_union_request_rejects_an_attribute_no_resource_type_declares():
    with pytest.raises(InvalidFilterException, match="Field not found: nonexistent"):
        SearchRequest[User | Group].model_validate({"filter": 'nonexistent eq "x"'})


def test_a_union_request_resolves_its_sort_by():
    """A root query sorts on an attribute only some of the types it serves declare."""
    request = SearchRequest[User | Group].model_validate({"sortBy": "userName"})
    assert request.sort_by.field_name == "user_name"
    assert request.sort_by.model is User


def test_a_parameterised_request_resolves_its_attributes():
    """A server reads the attribute a client asked for, rather than its spelling."""
    request = SearchRequest[User].model_validate(
        {"attributes": ["userName", "emails.value"]}
    )
    assert [path.field_name for path in request.attributes] == ["user_name", "value"]
    assert [path.model.__name__ for path in request.attributes] == ["User", "Email"]


def test_a_union_request_resolves_its_attributes():
    request = SearchRequest[User | Group].model_validate(
        {"attributes": ["userName", "members"]}
    )
    assert [path.model for path in request.attributes] == [User, Group]


def test_an_unparameterised_request_leaves_its_attributes_unresolved():
    """§3.9 makes no promise about an attribute a resource type does not declare."""
    request = SearchRequest.model_validate({"attributes": "userName"})
    assert request.attributes == ["userName"]
    assert request.attributes[0].field_name is None
