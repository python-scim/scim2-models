import json

import pytest

flask = pytest.importorskip("flask")
django = pytest.importorskip("django")
fastapi = pytest.importorskip("fastapi")

from doc.guides._examples.integrations import sort_resources  # noqa: E402
from doc.guides._examples.integrations import sort_value  # noqa: E402
from scim2_models import EnterpriseUser  # noqa: E402
from scim2_models import InvalidPathException  # noqa: E402
from scim2_models import SearchRequest  # noqa: E402
from scim2_models import User  # noqa: E402


def create_flask_app():
    from flask import Flask

    from doc.guides._examples import flask_example

    app = Flask(__name__)
    app.register_blueprint(flask_example.bp)
    return app


def test_flask_example_smoke():
    from doc.guides._examples import integrations

    integrations.records.clear()
    app = create_flask_app()
    client = app.test_client()

    create_response = client.post(
        "/scim/v2/Users",
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen@example.com",
            "displayName": "Barbara Jensen",
            "active": True,
            "emails": [{"value": "bjensen@example.com"}],
        },
    )
    assert create_response.status_code == 201
    assert create_response.headers["Content-Type"] == "application/scim+json"
    user_id = create_response.get_json()["id"]

    get_response = client.get(f"/scim/v2/Users/{user_id}")
    assert get_response.status_code == 200
    assert get_response.get_json()["userName"] == "bjensen@example.com"

    patch_response = client.patch(
        f"/scim/v2/Users/{user_id}",
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "path": "displayName", "value": "Babs"}],
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.get_json()["displayName"] == "Babs"

    list_response = client.get("/scim/v2/Users?startIndex=1&count=1")
    assert list_response.status_code == 200
    assert list_response.get_json()["totalResults"] == 1

    search_response = client.post(
        "/scim/v2/Users/.search",
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
            "startIndex": 1,
            "count": 1,
            "attributes": ["userName"],
        },
    )
    assert search_response.status_code == 200
    searched = search_response.get_json()
    assert searched["totalResults"] == 1
    assert searched["Resources"][0]["userName"] == "bjensen@example.com"
    assert "displayName" not in searched["Resources"][0]

    root_response = client.post(
        "/scim/v2/.search",
        json={"schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"]},
    )
    assert root_response.status_code == 200
    gathered = root_response.get_json()
    assert gathered["totalResults"] == 3
    assert {resource["meta"]["resourceType"] for resource in gathered["Resources"]} == {
        "User",
        "Group",
    }

    # Binding the root query to a union is what resolves a sortBy both types declare.
    sorted_root_response = client.post(
        "/scim/v2/.search",
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
            "sortBy": "displayName",
        },
    )
    assert sorted_root_response.status_code == 200
    assert [
        resource["displayName"]
        for resource in sorted_root_response.get_json()["Resources"]
    ] == ["Administrators", "Auditors", "Babs"]

    malformed_response = client.post(
        "/scim/v2/Users/.search",
        data="{not json",
        content_type="application/scim+json",
    )
    assert malformed_response.status_code == 400
    assert malformed_response.get_json()["scimType"] == "invalidSyntax"

    get_attributes_response = client.get(
        f"/scim/v2/Users/{user_id}?attributes=userName"
    )
    assert get_attributes_response.status_code == 200
    assert "userName" in get_attributes_response.get_json()
    assert "displayName" not in get_attributes_response.get_json()

    list_attributes_response = client.get("/scim/v2/Users?attributes=userName")
    assert list_attributes_response.status_code == 200
    resources = list_attributes_response.get_json()["Resources"]
    assert "userName" in resources[0]
    assert "displayName" not in resources[0]

    duplicate_response = client.post(
        "/scim/v2/Users",
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen@example.com",
        },
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.get_json()["scimType"] == "uniqueness"

    put_response = client.put(
        f"/scim/v2/Users/{user_id}",
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen@example.com",
            "displayName": "Barbara J.",
        },
    )
    assert put_response.status_code == 200
    assert put_response.get_json()["displayName"] == "Barbara J."

    for extra in ("aturner@example.com", "Zoe@example.com"):
        client.post(
            "/scim/v2/Users",
            json={
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": extra,
            },
        )

    def sorted_names(query):
        response = client.get(f"/scim/v2/Users?{query}")
        assert response.status_code == 200
        return [user["userName"] for user in response.get_json()["Resources"]]

    # §3.4.2.3 sorts case-insensitively unless the attribute is case-exact
    assert sorted_names("sortBy=userName") == [
        "aturner@example.com",
        "bjensen@example.com",
        "Zoe@example.com",
    ]
    assert sorted_names("sortBy=userName&sortOrder=descending") == [
        "Zoe@example.com",
        "bjensen@example.com",
        "aturner@example.com",
    ]

    # "if there is no data for the specified sortBy value, they are ordered
    # last if ascending and first if descending"
    assert sorted_names("sortBy=displayName")[-2:] == [
        "aturner@example.com",
        "Zoe@example.com",
    ]
    assert sorted_names("sortBy=displayName&sortOrder=descending")[:2] == [
        "aturner@example.com",
        "Zoe@example.com",
    ]

    # A sub-attribute of a multi-valued attribute is read from the entry the
    # order picks, and only one user carries an email.
    assert sorted_names("sortBy=emails.value")[0] == "bjensen@example.com"


def sorting_users(emails_by_id):
    """Build users carrying the emails each id maps to."""
    return [
        User[EnterpriseUser](id=user_id, user_name=user_id, emails=emails)
        for user_id, emails in emails_by_id.items()
    ]


def sorting_order(resources, attribute, sort_order=None):
    """Return the ids a ``sortBy`` puts the resources in."""
    request = SearchRequest[User[EnterpriseUser]](
        sort_by=attribute, sort_order=sort_order
    )
    return [
        resource.id
        for resource in sort_resources(resources, request.sort_by, sort_order)
    ]


def sorting_key(resource, attribute):
    """Return the single value a ``sortBy`` orders a resource by."""
    request = SearchRequest[User[EnterpriseUser]](sort_by=attribute)
    return sort_value(resource, request.sort_by)


@pytest.mark.parametrize("attribute", ["emails", "emails.value"])
def test_sorting_reads_the_primary_entry_of_a_multivalued_attribute(attribute):
    """The entry marked ``primary`` decides the order, not the first one.

    Ordering on the first entry instead would put ``1`` ahead of ``2``, since
    ``a@example.com`` precedes ``m@example.com``.
    """
    resources = sorting_users(
        {
            "1": [
                User.Emails(value="a@example.com"),
                User.Emails(value="z@example.com", primary=True),
            ],
            "2": [User.Emails(value="m@example.com")],
        }
    )
    assert sorting_order(resources, attribute) == ["2", "1"]


def test_sorting_reads_a_sub_attribute_from_the_primary_entry():
    """A path naming a sub-attribute reads it from the entry the order picked.

    Reading the first entry instead would put ``2`` ahead of ``1``, ``other``
    preceding ``work``.
    """
    resources = sorting_users(
        {
            "1": [
                User.Emails(value="a@example.com", type="work"),
                User.Emails(value="z@example.com", type="home", primary=True),
            ],
            "2": [User.Emails(value="m@example.com", type="other")],
        }
    )
    assert sorting_order(resources, "emails.type") == ["1", "2"]


def test_sorting_falls_back_to_the_first_entry_without_a_primary():
    """An attribute marking no entry primary is ordered by its first one."""
    resources = sorting_users(
        {
            "1": [
                User.Emails(value="z@example.com"),
                User.Emails(value="a@example.com"),
            ],
            "2": [User.Emails(value="m@example.com")],
        }
    )
    assert sorting_order(resources, "emails.value") == ["2", "1"]


def test_sorting_an_unassigned_multivalued_attribute():
    """A resource carrying no entry comes last ascending and first descending."""
    resources = sorting_users({"1": None, "2": [User.Emails(value="m@example.com")]})
    assert sorting_order(resources, "emails.value") == ["2", "1"]
    assert sorting_order(resources, "emails.value", "descending") == ["1", "2"]


def test_sorting_a_scalar_multivalued_attribute_reads_the_entry_itself():
    """A scalar entry is the value, where a complex one holds it in a sub-attribute."""
    resource = sorting_users({"1": [User.Emails(value="m@example.com")]})[0]
    assert sorting_key(resource, "schemas") == User.__schema__


def test_sorting_an_attribute_of_an_extension_left_unset():
    """An extension that is not set holds no value to order by."""
    resource = sorting_users({"1": None})[0]
    urn = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department"
    assert sorting_key(resource, urn) is None

    resource[EnterpriseUser] = EnterpriseUser(department="Tour Operations")
    assert sorting_key(resource, urn) == "Tour Operations"


def test_sorting_a_request_that_named_no_resource_type():
    """The helper orders by a resolved attribute, which an unparameterised request has none of.

    A request naming the type it serves cannot reach here: an attribute the
    model does not declare is refused when the request is built.
    """
    resources = sorting_users({"1": None})
    with pytest.raises(InvalidPathException):
        sort_resources(resources, SearchRequest(sort_by="userName").sort_by)


def test_django_example_smoke():
    from django.conf import settings

    settings.configure(
        DEBUG=True,
        SECRET_KEY="test-secret-key",
        ROOT_URLCONF="doc.guides._examples.django_example",
        ALLOWED_HOSTS=["testserver"],
        MIDDLEWARE=[],
    )
    django.setup()

    from django.test import Client
    from django.test import override_settings

    from doc.guides._examples import integrations

    integrations.records.clear()

    with override_settings(ROOT_URLCONF="doc.guides._examples.django_example"):
        client = Client()

        create_response = client.post(
            "/scim/v2/Users",
            data=json.dumps(
                {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "userName": "bjensen@example.com",
                    "displayName": "Barbara Jensen",
                    "active": True,
                    "emails": [{"value": "bjensen@example.com"}],
                }
            ),
            content_type="application/scim+json",
        )
        assert create_response.status_code == 201
        assert create_response.headers["Content-Type"] == "application/scim+json"
        user_id = json.loads(create_response.content)["id"]

        # The request names the resource type it serves, so an attribute the
        # type does not declare is refused before the view has to sort on it.
        refused_sort_response = client.get("/scim/v2/Users?sortBy=nonexistent")
        assert refused_sort_response.status_code == 400
        assert json.loads(refused_sort_response.content)["scimType"] == "invalidPath"

        get_response = client.get(f"/scim/v2/Users/{user_id}")
        assert get_response.status_code == 200
        assert json.loads(get_response.content)["userName"] == "bjensen@example.com"

        patch_response = client.patch(
            f"/scim/v2/Users/{user_id}",
            data=json.dumps(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [
                        {"op": "replace", "path": "displayName", "value": "Babs"}
                    ],
                }
            ),
            content_type="application/scim+json",
        )
        assert patch_response.status_code == 200
        assert json.loads(patch_response.content)["displayName"] == "Babs"

        list_response = client.get("/scim/v2/Users?startIndex=1&count=1")
        assert list_response.status_code == 200
        assert json.loads(list_response.content)["totalResults"] == 1

        search_response = client.post(
            "/scim/v2/Users/.search",
            json.dumps(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
                    "startIndex": 1,
                    "count": 1,
                    "attributes": ["userName"],
                }
            ),
            content_type="application/scim+json",
        )
        assert search_response.status_code == 200
        searched = json.loads(search_response.content)
        assert searched["totalResults"] == 1
        assert searched["Resources"][0]["userName"] == "bjensen@example.com"
        assert "displayName" not in searched["Resources"][0]

        root_response = client.post(
            "/scim/v2/.search",
            json.dumps(
                {"schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"]}
            ),
            content_type="application/scim+json",
        )
        assert root_response.status_code == 200
        gathered = json.loads(root_response.content)
        assert gathered["totalResults"] == 3
        assert {
            resource["meta"]["resourceType"] for resource in gathered["Resources"]
        } == {"User", "Group"}

        malformed_response = client.post(
            "/scim/v2/Users/.search",
            "{not json",
            content_type="application/scim+json",
        )
        assert malformed_response.status_code == 400
        assert json.loads(malformed_response.content)["scimType"] == "invalidSyntax"

        get_attributes_response = client.get(
            f"/scim/v2/Users/{user_id}?attributes=userName"
        )
        assert get_attributes_response.status_code == 200
        assert "userName" in json.loads(get_attributes_response.content)
        assert "displayName" not in json.loads(get_attributes_response.content)

        list_attributes_response = client.get("/scim/v2/Users?attributes=userName")
        assert list_attributes_response.status_code == 200
        resources = json.loads(list_attributes_response.content)["Resources"]
        assert "userName" in resources[0]
        assert "displayName" not in resources[0]

        duplicate_response = client.post(
            "/scim/v2/Users",
            data=json.dumps(
                {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "userName": "bjensen@example.com",
                }
            ),
            content_type="application/scim+json",
        )
        assert duplicate_response.status_code == 409
        assert json.loads(duplicate_response.content)["scimType"] == "uniqueness"

        put_response = client.put(
            f"/scim/v2/Users/{user_id}",
            data=json.dumps(
                {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "userName": "bjensen@example.com",
                    "displayName": "Barbara J.",
                }
            ),
            content_type="application/scim+json",
        )
        assert put_response.status_code == 200
        assert json.loads(put_response.content)["displayName"] == "Barbara J."


def test_fastapi_example_smoke():
    from doc.guides._examples import integrations

    integrations.records.clear()

    from starlette.testclient import TestClient

    from doc.guides._examples.fastapi_example import app

    client = TestClient(app)

    create_response = client.post(
        "/scim/v2/Users",
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen@example.com",
            "displayName": "Barbara Jensen",
            "active": True,
            "emails": [{"value": "bjensen@example.com"}],
        },
    )
    assert create_response.status_code == 201
    assert create_response.headers["Content-Type"] == "application/scim+json"
    user_id = create_response.json()["id"]

    get_response = client.get(f"/scim/v2/Users/{user_id}")
    assert get_response.status_code == 200
    assert get_response.json()["userName"] == "bjensen@example.com"

    patch_response = client.patch(
        f"/scim/v2/Users/{user_id}",
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "path": "displayName", "value": "Babs"}],
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["displayName"] == "Babs"

    list_response = client.get("/scim/v2/Users?startIndex=1&count=1")
    assert list_response.status_code == 200
    assert list_response.json()["totalResults"] == 1

    search_response = client.post(
        "/scim/v2/Users/.search",
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
            "startIndex": 1,
            "count": 1,
            "attributes": ["userName"],
        },
    )
    assert search_response.status_code == 200
    searched = search_response.json()
    assert searched["totalResults"] == 1
    assert searched["Resources"][0]["userName"] == "bjensen@example.com"
    assert "displayName" not in searched["Resources"][0]

    root_response = client.post(
        "/scim/v2/.search",
        json={"schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"]},
    )
    assert root_response.status_code == 200
    gathered = root_response.json()
    assert gathered["totalResults"] == 3
    assert {resource["meta"]["resourceType"] for resource in gathered["Resources"]} == {
        "User",
        "Group",
    }

    get_attributes_response = client.get(
        f"/scim/v2/Users/{user_id}?attributes=userName"
    )
    assert get_attributes_response.status_code == 200
    assert "userName" in get_attributes_response.json()
    assert "displayName" not in get_attributes_response.json()

    list_attributes_response = client.get("/scim/v2/Users?attributes=userName")
    assert list_attributes_response.status_code == 200
    resources = list_attributes_response.json()["Resources"]
    assert "userName" in resources[0]
    assert "displayName" not in resources[0]

    duplicate_response = client.post(
        "/scim/v2/Users",
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen@example.com",
        },
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["scimType"] == "uniqueness"

    put_response = client.put(
        f"/scim/v2/Users/{user_id}",
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen@example.com",
            "displayName": "Barbara J.",
        },
    )
    assert put_response.status_code == 200
    assert put_response.json()["displayName"] == "Barbara J."


@pytest.mark.parametrize(
    ("parameters", "scim_type"),
    [
        ({"count": "abc"}, "invalidSyntax"),
        ({"attributes": 'emails[type eq "work"]'}, "invalidPath"),
    ],
)
def test_fastapi_example_answers_a_scim_error_to_a_refused_query_parameter(
    parameters, scim_type
):
    """FastAPI validates the query parameters itself, so a refused one never reaches the endpoint.

    The failure is a RequestValidationError, which the guide handles next to
    ValidationError: without it the framework answers its own body, and a
    client reading the scimType of the error finds none.
    """
    from starlette.testclient import TestClient

    from doc.guides._examples.fastapi_example import app

    client = TestClient(app)

    response = client.get("/scim/v2/Users", params=parameters)
    assert response.status_code == 400
    assert response.headers["Content-Type"] == "application/scim+json"
    assert response.json()["scimType"] == scim_type
