from scim2_models.rfc7644.search_request import SearchRequest
from scim2_models.rfc7644.search_request import SortOrder


def test_search_request():
    SearchRequest(
        attributes=["userName", "displayName"],
        excluded_attributes=["timezone", "phoneNumbers"],
        filter='userName Eq "john"',
        sort_by="userName",
        sort_order=SortOrder.ascending,
        start_index=1,
        count=10,
    )


def test_start_index_floor():
    """Test that startIndex values less than 0 are interpreted as 0.
    https://datatracker.ietf.org/doc/html/rfc7644#section-3.4.2.4

        A negative value SHALL be interpreted as 0.
    """

    sr = SearchRequest(start_index=100)
    assert sr.start_index == 100

    sr = SearchRequest(start_index=-1)
    assert sr.start_index == 0


def test_count_floor():
    """Test that count values less than 1 are interpreted as 1.
    https://datatracker.ietf.org/doc/html/rfc7644#section-3.4.2.4

        A value less than 1 SHALL be interpreted as 1.
    """

    sr = SearchRequest(count=100)
    assert sr.count == 100

    sr = SearchRequest(count=0)
    assert sr.count == 1

    sr = SearchRequest(count=-1)
    assert sr.count == 1
