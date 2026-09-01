import json

import pytest

flask = pytest.importorskip("flask")
django = pytest.importorskip("django")
fastapi = pytest.importorskip("fastapi")


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
            "emails": [{"value": "bjensen@example.com", "type": "work"}],
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

    filtered_response = client.get(
        "/scim/v2/Users",
        query_string={"filter": 'emails[type eq "work" and value ew "@example.com"]'},
    )
    assert filtered_response.status_code == 200
    assert filtered_response.get_json()["totalResults"] == 1

    unmatched_response = client.get(
        "/scim/v2/Users", query_string={"filter": 'userName eq "nobody"'}
    )
    assert unmatched_response.status_code == 200
    assert unmatched_response.get_json()["totalResults"] == 0

    malformed_filter_response = client.get(
        "/scim/v2/Users", query_string={"filter": "userName eq"}
    )
    assert malformed_filter_response.status_code == 400
    assert malformed_filter_response.get_json()["scimType"] == "invalidFilter"

    unknown_attribute_response = client.get(
        "/scim/v2/Users", query_string={"filter": 'unknownAttr eq "x"'}
    )
    assert unknown_attribute_response.status_code == 400
    assert unknown_attribute_response.get_json()["scimType"] == "invalidFilter"

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
                    "emails": [{"value": "bjensen@example.com", "type": "work"}],
                }
            ),
            content_type="application/scim+json",
        )
        assert create_response.status_code == 201
        assert create_response.headers["Content-Type"] == "application/scim+json"
        user_id = json.loads(create_response.content)["id"]

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

        filtered_response = client.get(
            "/scim/v2/Users",
            {"filter": 'emails[type eq "work" and value ew "@example.com"]'},
        )
        assert filtered_response.status_code == 200
        assert json.loads(filtered_response.content)["totalResults"] == 1

        unmatched_response = client.get(
            "/scim/v2/Users", {"filter": 'userName eq "nobody"'}
        )
        assert unmatched_response.status_code == 200
        assert json.loads(unmatched_response.content)["totalResults"] == 0

        malformed_filter_response = client.get(
            "/scim/v2/Users", {"filter": "userName eq"}
        )
        assert malformed_filter_response.status_code == 400
        assert json.loads(malformed_filter_response.content)["scimType"] == (
            "invalidFilter"
        )

        unknown_attribute_response = client.get(
            "/scim/v2/Users", {"filter": 'unknownAttr eq "x"'}
        )
        assert unknown_attribute_response.status_code == 400
        assert json.loads(unknown_attribute_response.content)["scimType"] == (
            "invalidFilter"
        )

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
            "emails": [{"value": "bjensen@example.com", "type": "work"}],
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

    filtered_response = client.get(
        "/scim/v2/Users",
        params={"filter": 'emails[type eq "work" and value ew "@example.com"]'},
    )
    assert filtered_response.status_code == 200
    assert filtered_response.json()["totalResults"] == 1

    unmatched_response = client.get(
        "/scim/v2/Users", params={"filter": 'userName eq "nobody"'}
    )
    assert unmatched_response.status_code == 200
    assert unmatched_response.json()["totalResults"] == 0

    malformed_filter_response = client.get(
        "/scim/v2/Users", params={"filter": "userName eq"}
    )
    assert malformed_filter_response.status_code == 400
    assert malformed_filter_response.json()["scimType"] == "invalidFilter"

    unknown_attribute_response = client.get(
        "/scim/v2/Users", params={"filter": 'unknownAttr eq "x"'}
    )
    assert unknown_attribute_response.status_code == 400
    assert unknown_attribute_response.json()["scimType"] == "invalidFilter"

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
