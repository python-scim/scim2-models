import pytest
from pydantic import ValidationError

from scim2_models.rfc7644.search_request import SearchRequest


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
