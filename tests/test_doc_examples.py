import json

import pytest

flask = pytest.importorskip("flask")
django = pytest.importorskip("django")
fastapi = pytest.importorskip("fastapi")
sqlalchemy = pytest.importorskip("sqlalchemy")

from datetime import datetime  # noqa: E402
from datetime import timezone  # noqa: E402

from doc.guides._examples.sqlalchemy_example import EmailRecord  # noqa: E402
from doc.guides._examples.sqlalchemy_example import GroupRecord  # noqa: E402
from doc.guides._examples.sqlalchemy_example import UserRecord  # noqa: E402
from doc.guides._examples.sqlalchemy_example import create_session_factory  # noqa: E402
from doc.guides._examples.sqlalchemy_example import query_users  # noqa: E402
from doc.guides._examples.sqlalchemy_example import to_scim_user  # noqa: E402
from scim2_models import InvalidFilterException  # noqa: E402
from scim2_models import InvalidPathException  # noqa: E402
from scim2_models import ScimFilter  # noqa: E402
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


def sqlalchemy_records():
    """Build fresh rows, since an ORM object belongs to the session storing it."""
    return [
        UserRecord(
            id="1",
            user_name="bjensen",
            title="Manager",
            active=True,
            last_modified=datetime(2024, 6, 1, tzinfo=timezone.utc),
            emails=[EmailRecord(type="work", value="bjensen@example.com")],
            groups=[GroupRecord(value="2819c223-7f76", display="Tour Guides")],
        ),
        UserRecord(
            id="2",
            user_name="RSanchez",
            active=False,
            last_modified=datetime(2023, 1, 15, tzinfo=timezone.utc),
            emails=[EmailRecord(type="home", value="rick@example.org")],
            groups=[GroupRecord(value="2819C223-7F76", display="Tour Guides")],
        ),
        UserRecord(
            id="3",
            user_name="jsmith",
            title="Engineer",
            active=True,
            last_modified=datetime(2025, 3, 20, tzinfo=timezone.utc),
            emails=[EmailRecord(type="Work", value="J.Smith@Example.com")],
        ),
        UserRecord(
            id="4",
            user_name="dpotter",
            title="100% remote",
            active=True,
            last_modified=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        UserRecord(
            id="5",
            user_name="mgarcia",
            title="1000 Files",
            active=True,
            last_modified=datetime(2025, 2, 1, tzinfo=timezone.utc),
        ),
    ]


SQLALCHEMY_FILTERS = [
    'userName eq "bjensen"',
    'userName eq "BJENSEN"',
    'userName sw "b" and title pr',
    'emails[type eq "work" and value ew "@example.com"]',
    'emails[type eq "WORK"]',
    'emails.value co "Example"',
    'groups co "2819c223"',
    'groups co "2819C223"',
    'groups.display eq "tour guides"',
    "active eq true",
    'meta.lastModified gt "2024-01-01T00:00:00Z"',
    "not (title pr)",
    "emails pr",
    "not (emails pr)",
    'userName eq "bjensen" or title eq "Engineer"',
    'emails[type eq "home"] and active eq false',
    'title co "100%"',
    'title co "100"',
    'title ne "Manager"',
    'userName ne "bjensen"',
    'emails.type ne "work"',
    'emails[type ne "work"]',
    'groups ne "2819c223"',
]


@pytest.fixture
def sqlalchemy_session():
    session_factory = create_session_factory()
    with session_factory() as session:
        session.add_all(sqlalchemy_records())
        session.commit()
        engine = session.get_bind()
        yield session
    engine.dispose()


# -- oracle-start --
def test_sqlalchemy_queries_select_what_the_evaluator_selects(sqlalchemy_session):
    """The generated query and ``match`` answer the same question.

    Both walk the same tree through the same resolution, so a difference is a
    defect of the query rather than of the filter.
    """
    stored = sqlalchemy_session.scalars(sqlalchemy.select(UserRecord)).all()
    scim_users = [to_scim_user(record) for record in stored]

    for expression in SQLALCHEMY_FILTERS:
        scim_filter = ScimFilter[User](expression)
        total, page = query_users(sqlalchemy_session, SearchRequest(filter=expression))
        evaluated = sorted(user.id for user in scim_users if scim_filter.match(user))
        assert sorted(record.id for record in page) == evaluated, expression
        assert total == len(evaluated), expression


# -- oracle-end --


def test_sqlalchemy_sorts_and_paginates_in_the_database(sqlalchemy_session):
    """``totalResults`` counts every match, where a page holds only its slice."""
    total, page = query_users(
        sqlalchemy_session,
        SearchRequest(sort_by="userName", sort_order="descending", count=2),
    )
    assert total == 5
    assert [record.user_name for record in page] == ["mgarcia", "jsmith"]

    total, page = query_users(
        sqlalchemy_session,
        SearchRequest(sort_by="userName", start_index=3, count=2),
    )
    assert total == 5
    assert [record.user_name for record in page] == ["dpotter", "jsmith"]


def test_sqlalchemy_counts_the_filtered_results_only(sqlalchemy_session):
    total, page = query_users(
        sqlalchemy_session, SearchRequest(filter="active eq true", count=2)
    )
    assert total == 4
    assert len(page) == 2


def test_sqlalchemy_rejects_a_filter_on_an_unknown_attribute(sqlalchemy_session):
    with pytest.raises(InvalidFilterException) as exc_info:
        query_users(sqlalchemy_session, SearchRequest(filter='unknownAttr eq "x"'))
    assert exc_info.value.scim_type == "invalidFilter"


def test_sqlalchemy_rejects_sorting_on_a_multivalued_attribute(sqlalchemy_session):
    """An attribute spread over its own table has no single column to sort on."""
    with pytest.raises(InvalidPathException):
        query_users(sqlalchemy_session, SearchRequest(sort_by="emails"))
