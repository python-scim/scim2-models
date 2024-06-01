import pydantic
import pytest

import pydantic_scim2


@pytest.fixture(autouse=True)
def add_doctest_namespace(doctest_namespace):
    doctest_namespace["pydantic"] = pydantic
    imports = {item: getattr(pydantic_scim2, item) for item in pydantic_scim2.__all__}
    doctest_namespace.update(imports)
    return doctest_namespace
