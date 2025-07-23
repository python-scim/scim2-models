import pytest
from pydantic import ValidationError

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
        {
            "attributes": ["123invalid"],  # Starts with digit
            "error_match": "path.*invalid",
        },
        {
            "attributes": ["valid", "invalid..path"],  # Double dots
            "error_match": "path.*invalid",
        },
        {
            "attributes": ["invalid@character"],  # Invalid character
            "error_match": "path.*invalid",
        },
    ]

    for case in invalid_cases:
        with pytest.raises(ValidationError, match=case["error_match"]):
            SearchRequest.model_validate(case)


def test_search_request_invalid_excluded_attributes():
    """Test that invalid excluded attribute paths are rejected."""
    invalid_data = {
        "excluded_attributes": ["valid", "123invalid"],  # Second one starts with digit
    }

    with pytest.raises(ValidationError, match="path.*invalid"):
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
        with pytest.raises(ValidationError, match="path.*invalid"):
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

    with pytest.raises(ValidationError, match="path.*invalid"):
        SearchRequest.model_validate(invalid_data)
