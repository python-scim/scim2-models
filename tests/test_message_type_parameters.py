from typing import Any
from typing import TypeVar

import pytest

from scim2_models import BulkOperation
from scim2_models import BulkRequest
from scim2_models import BulkResponse
from scim2_models import ListResponse
from scim2_models import PatchOp
from scim2_models import Resource
from scim2_models import User

PARAMETERIZED_MESSAGES = [
    ListResponse,
    PatchOp,
    BulkRequest,
    BulkResponse,
    BulkOperation,
]


@pytest.mark.parametrize("model", PARAMETERIZED_MESSAGES)
def test_bare_model_cannot_be_instantiated(model):
    """Without a parameter the type variable falls back on its bound, which declares no attribute."""
    with pytest.raises(TypeError, match=f"{model.__name__} requires a type parameter"):
        model()


@pytest.mark.parametrize("model", PARAMETERIZED_MESSAGES)
def test_bare_model_cannot_validate_a_payload(model):
    """Reading a payload needs the parameter as much as building one does."""
    with pytest.raises(TypeError, match=f"{model.__name__} requires a type parameter"):
        model.model_validate({})


@pytest.mark.parametrize("model", PARAMETERIZED_MESSAGES)
def test_bare_model_cannot_validate_a_json_payload(model):
    """A JSON payload reaches the same check as a decoded one."""
    with pytest.raises(TypeError, match=f"{model.__name__} requires a type parameter"):
        model.model_validate_json("{}")


@pytest.mark.parametrize("model", PARAMETERIZED_MESSAGES)
def test_parameter_naming_something_else_than_a_resource_is_refused(model):
    """The error names the model that was indexed, not one it carries."""
    with pytest.raises(
        TypeError, match=f"^{model.__name__} type parameter must name resource types"
    ):
        model[str]


@pytest.mark.parametrize("model", PARAMETERIZED_MESSAGES)
def test_resource_itself_annotates_a_message_but_cannot_read_a_payload(model):
    """Resource declares no attribute, and an annotation covering any resource type needs it."""
    assert model[Resource] is not None

    with pytest.raises(TypeError, match=r"\[Resource\] declares no attribute"):
        model[Resource]()


@pytest.mark.parametrize("model", PARAMETERIZED_MESSAGES)
def test_unsubstituted_type_variable_cannot_read_a_payload(model):
    """A type variable stands for what a generic caller substitutes, and declares nothing itself."""
    resource_t = TypeVar("resource_t", bound=Resource[Any])
    assert model[resource_t] is not None

    with pytest.raises(TypeError, match=r"\[resource_t\] declares no attribute"):
        model[resource_t]()


@pytest.mark.parametrize("model", PARAMETERIZED_MESSAGES)
def test_subclass_reads_payloads_with_the_parameter_it_inherits(model):
    """A subclass holds no parameter of its own, and specializing one is not parameterizing none."""
    specialized = type("Specialized", (model[User],), {})

    assert specialized() is not None


def test_union_holding_a_bare_resource_cannot_read_a_payload():
    """One member declaring no attribute leaves the entries it would answer for unreadable."""
    assert ListResponse[User | Resource] is not None

    with pytest.raises(TypeError, match=r"\[User \| Resource\] declares no attribute"):
        ListResponse[User | Resource]()
