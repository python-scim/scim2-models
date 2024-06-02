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
