import pytest

from doc.integrations._examples.sqlalchemy_example import create_session_factory
from doc.integrations._examples.sqlalchemy_example import from_scim_user
from doc.integrations._examples.sqlalchemy_example import query_users


@pytest.fixture(autouse=True)
def sqlalchemy_example(doctest_namespace):
    """Expose the functions of the SQLAlchemy guide to the doctests of the pages."""
    doctest_namespace["create_session_factory"] = create_session_factory
    doctest_namespace["from_scim_user"] = from_scim_user
    doctest_namespace["query_users"] = query_users
