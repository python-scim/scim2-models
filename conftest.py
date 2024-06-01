import pydantic
import pytest

import scim2_models


@pytest.fixture(autouse=True)
def add_doctest_namespace(doctest_namespace):
    doctest_namespace["pydantic"] = pydantic
    imports = {item: getattr(scim2_models, item) for item in scim2_models.__all__}
    doctest_namespace.update(imports)
    return doctest_namespace
