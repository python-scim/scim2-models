import datetime
import re
from typing import Annotated
from typing import Any

import pytest
from lark.exceptions import LarkError
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ValidationError

from scim2_models import EnterpriseUser
from scim2_models import Extension
from scim2_models import Group
from scim2_models import InvalidFilterException
from scim2_models import Name
from scim2_models import Path
from scim2_models import PathNotFoundException
from scim2_models import Required
from scim2_models import ResolvedAttribute
from scim2_models import Schema
from scim2_models import ScimFilter
from scim2_models import User
from scim2_models.filters import AttrPath
from scim2_models.filters import CompareOperator
from scim2_models.filters import Comparison
from scim2_models.filters import FilterVisitor
from scim2_models.filters import LogicalExpr
from scim2_models.filters import LogicalOperator
from scim2_models.filters import Not
from scim2_models.filters import Present
from scim2_models.filters import ValuePath
from scim2_models.filters import coerce_value
from scim2_models.filters import compare
from scim2_models.filters import is_present
from scim2_models.filters import parse_filter
from scim2_models.filters import resolve_attr_path
from scim2_models.filters import resolve_comparison_path
from scim2_models.grammar import _error_detail
from scim2_models.resources.user import Email

COMPOSED = "Jos\N{LATIN SMALL LETTER E WITH ACUTE}"
DECOMPOSED = "Jose\N{COMBINING ACUTE ACCENT}"
DECOMPOSED_SUFFIX = "se\N{COMBINING ACUTE ACCENT}"

UserWithExtension = User[EnterpriseUser]


@pytest.fixture
def user():
    user = UserWithExtension(
        user_name="BJensen",
        display_name="Barbara Jensen",
        title="Manager",
        active=True,
        emails=[
            {"type": "work", "value": "bjensen@example.com", "primary": True},
            {"type": "home", "value": "babs@home.net", "primary": False},
        ],
    )
    user[EnterpriseUser] = EnterpriseUser(
        employee_number="701984", manager={"value": "26118915"}
    )
    return user


# --- Resolution ---


def test_resolution_exposes_what_a_transpiler_needs():
    """A resolved attribute says which field, which type and which casing."""
    resolved = resolve_attr_path(User, AttrPath("emails", "type"))
    assert resolved.model is User
    assert resolved.field_name == "emails"
    assert resolved.sub_field_name == "type"
    assert resolved.is_multivalued is True
    assert resolved.urn == "urn:ietf:params:scim:schemas:core:2.0:User:emails.type"


def test_resolution_of_a_simple_attribute():
    resolved = resolve_attr_path(User, AttrPath("userName"))
    assert resolved.field_name == "user_name"
    assert resolved.field_type is str
    assert resolved.is_multivalued is False
    assert resolved.sub_field_name is None
    assert resolved.target_field_name == "user_name"
    assert resolved.target_model is User


def test_resolution_targets_the_sub_attribute_when_there_is_one():
    resolved = resolve_attr_path(User, AttrPath("name", "familyName"))
    assert resolved.target_field_name == "family_name"
    assert resolved.target_type is str
    assert resolved.target_model is not User


def test_resolution_matches_attribute_names_case_insensitively():
    """§3.4.2.2 makes attribute names case-insensitive."""
    assert resolve_attr_path(User, AttrPath("USERNAME")).field_name == "user_name"


def test_resolution_of_an_attribute_qualified_by_the_resource_schema():
    resolved = resolve_attr_path(
        User, AttrPath("userName", uri="urn:ietf:params:scim:schemas:core:2.0:User")
    )
    assert resolved.field_name == "user_name"


def test_resolution_of_an_extension_attribute():
    resolved = resolve_attr_path(
        UserWithExtension,
        AttrPath(
            "employeeNumber",
            uri="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ),
    )
    assert resolved.model is EnterpriseUser
    assert resolved.field_name == "employee_number"


def test_resolution_reads_case_exactness_from_the_annotations():
    """A reference attribute is case-exact, per §2.3.7 and errata 6001."""
    assert resolve_attr_path(User, AttrPath("profileUrl")).case_exact is True
    assert resolve_attr_path(User, AttrPath("userName")).case_exact is False


def test_resolution_reads_case_exactness_of_a_sub_attribute():
    assert resolve_attr_path(Group, AttrPath("members", "value")).case_exact is True
    assert resolve_attr_path(Group, AttrPath("members", "display")).case_exact is False


def test_resolution_of_an_unknown_attribute_raises():
    with pytest.raises(PathNotFoundException):
        resolve_attr_path(User, AttrPath("nonexistent"))


def test_resolution_of_an_unknown_attribute_is_silent_when_tolerant():
    """Servers should be tolerant of schema extensions, per §3.5.2."""
    assert resolve_attr_path(User, AttrPath("nonexistent"), strict=False) is None


def test_resolution_of_an_unknown_sub_attribute_raises():
    with pytest.raises(PathNotFoundException):
        resolve_attr_path(User, AttrPath("name", "nonexistent"))


def test_resolution_of_an_unknown_sub_attribute_is_silent_when_tolerant():
    assert resolve_attr_path(User, AttrPath("name", "nope"), strict=False) is None


def test_resolution_of_a_sub_attribute_on_a_simple_attribute_raises():
    """``userName`` holds a string, which has no sub-attribute."""
    with pytest.raises(PathNotFoundException):
        resolve_attr_path(User, AttrPath("userName", "sub"))


def test_resolution_of_a_sub_attribute_on_a_simple_attribute_is_silent_when_tolerant():
    assert resolve_attr_path(User, AttrPath("userName", "sub"), strict=False) is None


def test_resolution_of_an_unknown_schema_raises():
    with pytest.raises(PathNotFoundException):
        resolve_attr_path(User, AttrPath("attr", uri="urn:unknown:schema"))


def test_resolution_of_an_unknown_schema_is_silent_when_tolerant():
    assert (
        resolve_attr_path(User, AttrPath("attr", uri="urn:x:y"), strict=False) is None
    )


def test_resolution_of_a_qualified_path_against_a_complex_attribute():
    """A complex attribute has no schema of its own to qualify against."""
    assert resolve_attr_path(Email, AttrPath("type", uri="urn:x:y")) is None


# --- The value convention ---


def test_a_comparison_without_a_sub_attribute_resolves_to_the_entry_values():
    """§3.4.2.2 writes ``emails co`` and ``emails.value co`` in one expression.

    A comparison against a multi-valued complex attribute applies to the
    ``value`` sub-attribute its entries carry.
    """
    resolved = resolve_comparison_path(User, AttrPath("emails"))
    assert resolved.field_name == "emails"
    assert resolved.sub_field_name == "value"
    assert resolved.urn == "urn:ietf:params:scim:schemas:core:2.0:User:emails.value"


def test_the_value_convention_carries_the_case_exactness_of_the_sub_attribute():
    """``members.value`` is case-exact where ``members`` is not."""
    assert resolve_comparison_path(Group, AttrPath("members")).case_exact is True


@pytest.mark.parametrize(
    ("model", "attr_path"),
    [
        pytest.param(User, AttrPath("emails", "type"), id="explicit sub-attribute"),
        pytest.param(User, AttrPath("name"), id="single-valued complex attribute"),
        pytest.param(User, AttrPath("schemas"), id="list of scalars"),
        pytest.param(Schema, AttrPath("attributes"), id="entries without a value"),
    ],
)
def test_the_value_convention_leaves_other_attributes_alone(model, attr_path):
    assert resolve_comparison_path(model, attr_path) == resolve_attr_path(
        model, attr_path
    )


def test_the_value_convention_tolerates_an_unknown_attribute():
    assert resolve_comparison_path(User, AttrPath("nope"), strict=False) is None


def test_comparing_a_multi_valued_complex_attribute_matches_its_entry_values():
    """The example of Figure 2 of §3.4.2.2 has to match."""
    user = User(user_name="x", emails=[{"type": "work", "value": "bj@example.com"}])
    assert ScimFilter[User]('emails co "example.com"').match(user)
    assert ScimFilter[User]('emails eq "bj@example.com"').match(user)
    assert not ScimFilter[User]('emails co "example.org"').match(user)


def test_presence_of_a_multi_valued_complex_attribute_tests_the_node():
    """``pr`` matches "a non-empty node for complex attributes", not its values.

    An entry without a ``value`` is still a node, so the convention that
    applies to comparisons must not apply here.
    """
    user = User(user_name="x", emails=[{"type": "work"}])
    assert ScimFilter[User]("emails pr").match(user)
    assert not ScimFilter[User]("emails.value pr").match(user)


def test_validating_a_comparison_against_entry_values_checks_the_sub_attribute():
    """A binary ``value`` refuses the substring operators, however addressed."""
    with pytest.raises(InvalidFilterException, match="binary"):
        ScimFilter[User]('x509Certificates co "a"')._validate_semantics()


# --- Coercion ---


def test_a_date_time_operand_is_coerced():
    """A filter carries JSON, a model holds Python types."""
    user = User(user_name="x")
    user.meta = {"last_modified": datetime.datetime(2011, 5, 13, 4, 42, 34)}
    assert ScimFilter[User]('meta.lastModified gt "2010-01-01T00:00:00"').match(user)
    assert not ScimFilter[User]('meta.lastModified gt "2012-01-01T00:00:00"').match(
        user
    )


def test_an_integer_operand_is_coerced_from_a_string():
    """Comparing against the wrong JSON type still works when convertible."""
    resolved = resolve_attr_path(User, AttrPath("userName"))

    assert coerce_value(resolved, "already a string") == "already a string"


def test_an_operand_that_does_not_fit_its_attribute_is_rejected():
    with pytest.raises(InvalidFilterException, match="is not valid for attribute"):
        ScimFilter[User]("userName eq 3")._validate_semantics()


@pytest.mark.parametrize(
    "expression",
    ['emails.value eq "notanemail"', 'emails[value eq "notanemail"]'],
)
def test_a_rejected_operand_names_the_whole_attribute(expression):
    """A sub-attribute is named by its full URN however it was addressed.

    Inside a value selection it is resolved against a complex model, which has
    no schema of its own, so the enclosing attribute has to complete it.
    """
    with pytest.raises(InvalidFilterException) as exc_info:
        ScimFilter[User](expression)._validate_semantics()
    assert (
        "urn:ietf:params:scim:schemas:core:2.0:User:emails.value"
        in exc_info.value.detail
    )


def test_a_rejected_operator_names_the_whole_attribute():
    with pytest.raises(InvalidFilterException) as exc_info:
        ScimFilter[User]('emails[primary co "x"]')._validate_semantics()
    assert (
        "urn:ietf:params:scim:schemas:core:2.0:User:emails.primary"
        in exc_info.value.detail
    )


def test_a_value_selection_evaluated_against_a_model_names_the_whole_attribute():
    """The evaluator reports the same URN as the validator."""
    user = User(user_name="x", emails=[{"value": "bjensen@example.com"}])
    with pytest.raises(InvalidFilterException) as exc_info:
        ScimFilter[User]('emails[primary co "x"]').match(user)
    assert (
        "urn:ietf:params:scim:schemas:core:2.0:User:emails.primary"
        in exc_info.value.detail
    )


def test_a_substring_operand_is_not_coerced():
    """``co``, ``sw`` and ``ew`` match a fragment, not a whole value.

    ``emails[value co "example"]`` is legitimate even though ``"example"`` is
    not a valid email address on its own.
    """
    user = User(user_name="x", emails=[{"value": "bjensen@example.com"}])
    assert ScimFilter[User]('emails[value co "example"]').match(user)
    assert ScimFilter[User]('emails[value sw "bjensen"]').match(user)
    assert ScimFilter[User]('emails[value ew ".com"]').match(user)


def test_a_null_operand_is_left_alone():

    resolved = resolve_attr_path(User, AttrPath("userName"))
    assert coerce_value(resolved, None) is None


# --- Operator validity ---


@pytest.mark.parametrize("operator", ["gt", "ge", "lt", "le"])
def test_ordering_a_boolean_attribute_is_rejected(operator):
    """§3.4.2.2 requires boolean attributes to fail the ordering operators."""
    with pytest.raises(InvalidFilterException, match="boolean"):
        ScimFilter[User](f"active {operator} true")._validate_semantics()


@pytest.mark.parametrize("operator", ["co", "sw", "ew"])
def test_substring_matching_a_boolean_attribute_is_rejected(operator):
    with pytest.raises(InvalidFilterException, match="boolean"):
        ScimFilter[User](f'active {operator} "x"')._validate_semantics()


@pytest.mark.parametrize("operator", ["eq", "ne"])
def test_comparing_a_boolean_attribute_for_equality_is_allowed(operator):
    ScimFilter[User](f"active {operator} true")._validate_semantics()


def test_ordering_a_binary_attribute_is_rejected():
    with pytest.raises(InvalidFilterException, match="binary"):
        ScimFilter[User]('x509Certificates.value gt "abc"')._validate_semantics()


# --- Evaluation ---


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('userName eq "bjensen"', True),
        ('userName eq "BJENSEN"', True),
        ('userName eq "other"', False),
        ('userName ne "other"', True),
        ('userName co "jen"', True),
        ('userName sw "bj"', True),
        ('userName ew "sen"', True),
        ('userName gt "a"', True),
        ('userName lt "a"', False),
        ('userName ge "bjensen"', True),
        ('userName le "bjensen"', True),
        ("title pr", True),
        ("nickName pr", False),
        ("active eq true", True),
        ("active eq false", False),
    ],
)
def test_comparison_against_a_single_valued_attribute(user, expression, expected):
    assert ScimFilter[UserWithExtension](expression).match(user) is expected


def test_comparison_is_case_insensitive_by_default():
    """A string attribute is case-insensitive unless annotated case-exact."""
    user = User(user_name="BJensen")
    assert ScimFilter[User]('userName eq "bjensen"').match(user)


def test_comparison_is_case_sensitive_on_a_case_exact_attribute():
    """``members.value`` references an id, which is case-exact per errata 8472."""
    group = Group(display_name="G", members=[{"value": "AbC"}])
    assert ScimFilter[Group]('members[value eq "AbC"]').match(group)
    assert not ScimFilter[Group]('members[value eq "abc"]').match(group)


def test_case_insensitive_comparison_folds_a_letter_expanding_to_two():
    """Case folding expands the sharp s to a double s, where lowercasing does not."""
    user = User(display_name="Stra\N{LATIN SMALL LETTER SHARP S}e")
    assert ScimFilter[User]('displayName eq "STRASSE"').match(user)


def test_case_insensitive_comparison_folds_the_greek_final_sigma():
    """A final and a medial sigma are the same letter and fold to the same value."""
    user = User(display_name="\u039f\u0394\u039f\u03a3")
    assert ScimFilter[User]('displayName eq "\u03bf\u03b4\u03bf\u03c3"').match(user)
    assert ScimFilter[User]('displayName eq "\u03bf\u03b4\u03bf\u03c2"').match(user)


def test_comparison_matches_a_canonically_equivalent_operand():
    """A precomposed and a decomposed accent denote the same text."""
    user = User(display_name=COMPOSED)
    assert ScimFilter[User](f'displayName eq "{DECOMPOSED}"').match(user)


def test_a_case_exact_comparison_matches_a_canonically_equivalent_operand():
    """Case exactness constrains the casing, not the normalization form."""
    assert compare(COMPOSED, DECOMPOSED, CompareOperator.eq, case_exact=True)
    assert not compare(
        COMPOSED.upper(), DECOMPOSED, CompareOperator.eq, case_exact=True
    )


@pytest.mark.parametrize(
    "operand",
    [
        f'co "{DECOMPOSED_SUFFIX} Jen"',
        f'sw "{DECOMPOSED.lower()}"',
        'ew "JENSEN"',
    ],
)
def test_substring_operators_prepare_both_operands(operand):
    user = User(display_name=f"{COMPOSED} Jensen")
    assert ScimFilter[User](f"displayName {operand}").match(user)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('emails.type eq "work"', True),
        ('emails.type eq "home"', True),
        ('emails.type eq "other"', False),
        ('emails.value co "example"', True),
    ],
)
def test_comparison_against_a_multi_valued_attribute_matches_any_value(
    user, expression, expected
):
    """§3.4.2.2: the filter matches if any of the values matches."""
    assert ScimFilter[UserWithExtension](expression).match(user) is expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('emails.type ne "work"', False),
        ('emails.type ne "home"', False),
        ('emails.type ne "other"', True),
    ],
)
def test_negated_comparison_against_a_multi_valued_attribute_is_universal(
    user, expression, expected
):
    """The RFC leaves ``ne`` on a multi-valued attribute undefined.

    The universal reading is used: no value equals the operand, so that it
    agrees with negating the equality.
    """
    assert ScimFilter[UserWithExtension](expression).match(user) is expected


def test_presence_of_a_multi_valued_sub_attribute(user):
    assert ScimFilter[UserWithExtension]("emails.value pr").match(user)


def test_presence_of_an_unset_attribute_does_not_match():
    assert not ScimFilter[User]("title pr").match(User(user_name="x"))


def test_presence_of_an_empty_list_does_not_match():
    assert not ScimFilter[User]("emails pr").match(User(user_name="x", emails=[]))


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('emails[type eq "work"]', True),
        ('emails[type eq "other"]', False),
        ('emails[type eq "work" and primary eq true]', True),
        ('emails[type eq "home" and primary eq true]', False),
        ('emails[type eq "work" or type eq "home"]', True),
        ('emails[not (type eq "work")]', True),
        ('emails[value ew "@home.net"]', True),
    ],
)
def test_value_selection(user, expression, expected):
    assert ScimFilter[UserWithExtension](expression).match(user) is expected


def test_value_selection_on_an_unset_attribute_does_not_match():
    assert not ScimFilter[User]('emails[type eq "work"]').match(User(user_name="x"))


def test_value_selection_on_a_single_valued_attribute_is_invalid():
    """§3.5.2 defines a selection over a complex multi-valued attribute only."""
    user = User(user_name="x", name={"family_name": "Jensen"})
    with pytest.raises(InvalidFilterException, match="not multi-valued"):
        ScimFilter[User]('name[familyName eq "Jensen"]').match(user)

    with pytest.raises(InvalidFilterException, match="not multi-valued"):
        ScimFilter[User]('name[familyName eq "Jensen"]')._validate_semantics()


def test_value_selection_on_a_single_valued_attribute_names_it():
    with pytest.raises(InvalidFilterException, match="userName"):
        ScimFilter[User]('userName[value eq "x"]')._validate_semantics()


def test_value_selection_on_a_scalar_list_uses_the_value_convention():
    """A multi-valued attribute that is not complex has no sub-attribute.

    Implementations conventionally address its entries through ``value``.
    """
    user = User(user_name="x", schemas=["urn:ietf:params:scim:schemas:core:2.0:User"])
    assert ScimFilter[User](
        'schemas[value eq "urn:ietf:params:scim:schemas:core:2.0:User"]'
    ).match(user)
    assert not ScimFilter[User]('schemas[value eq "urn:other"]').match(user)


def test_value_selection_on_a_scalar_list_ignores_other_attribute_names():
    user = User(
        user_name="x", schemas=["urn:ietf:params:scim:schemas:core:2.0:User", "urn:x"]
    )
    assert not ScimFilter[User]('schemas[type eq "urn:x"]').match(user)


def test_presence_within_a_value_selection_on_a_scalar_list():
    user = User(
        user_name="x", schemas=["urn:ietf:params:scim:schemas:core:2.0:User", "urn:x"]
    )
    assert ScimFilter[User]("schemas[value pr]").match(user)


def test_boolean_operators_within_a_value_selection_on_a_scalar_list():
    user = User(
        user_name="x", schemas=["urn:ietf:params:scim:schemas:core:2.0:User", "urn:x"]
    )
    assert ScimFilter[User]('schemas[value eq "urn:x" or value eq "urn:y"]').match(user)
    assert ScimFilter[User]('schemas[not (value eq "urn:y")]').match(user)
    assert not ScimFilter[User]('schemas[value eq "urn:x" and value eq "urn:y"]').match(
        user
    )


def test_a_value_selection_on_an_empty_scalar_list_does_not_match():
    assert not ScimFilter[User]("schemas[value pr]").match(
        User(user_name="x", schemas=[])
    )


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('userName eq "bjensen" and active eq true', True),
        ('userName eq "bjensen" and active eq false', False),
        ('userName eq "other" or title pr', True),
        ('userName eq "other" or nickName pr', False),
        ('not (userName eq "bjensen")', False),
        ('not (userName eq "other")', True),
        ("userName pr and title pr and active eq true", True),
    ],
)
def test_logical_composition(user, expression, expected):
    assert ScimFilter[UserWithExtension](expression).match(user) is expected


def test_comparison_against_an_extension_attribute(user):
    assert ScimFilter[UserWithExtension](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber "
        'eq "701984"'
    ).match(user)


def test_comparison_against_an_extension_sub_attribute(user):
    assert ScimFilter[UserWithExtension](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value "
        'eq "26118915"'
    ).match(user)


def test_comparison_against_an_unset_extension_does_not_match():
    user = UserWithExtension(user_name="x")
    assert not ScimFilter[UserWithExtension](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber pr"
    ).match(user)


def test_comparison_against_an_unset_complex_attribute_does_not_match():
    assert not ScimFilter[User]('name.familyName eq "Jensen"').match(
        User(user_name="x")
    )


def test_evaluation_of_an_unknown_attribute_does_not_match_by_default():
    """Tolerance is the default, so an unknown attribute simply does not match."""
    assert not ScimFilter[User]('nonexistent eq "x"').match(User(user_name="x"))


def test_evaluation_of_an_unknown_attribute_raises_when_strict():
    with pytest.raises(InvalidFilterException):
        ScimFilter[User]('nonexistent eq "x"').match(User(user_name="x"), strict=True)


def test_presence_of_an_unknown_attribute_does_not_match():
    assert not ScimFilter[User]("nonexistent pr").match(User(user_name="x"))


def test_value_selection_on_an_unknown_attribute_does_not_match():
    assert not ScimFilter[User]('nonexistent[type eq "x"]').match(User(user_name="x"))


# --- The filter type itself ---


def test_a_filter_behaves_like_the_string_it_came_from():
    expression = 'userName eq "bjensen"'
    assert ScimFilter(expression) == expression
    assert str(ScimFilter(expression)) == expression


def test_a_filter_is_a_string():
    """Anything reading a filter reads a string, a regular expression included.

    Slicing one yields a plain string rather than a filter, since a fragment of
    an expression is not an expression.
    """
    scim_filter = ScimFilter('userName eq "bjensen"')
    assert isinstance(scim_filter, str)
    assert hash(scim_filter) == hash('userName eq "bjensen"')
    assert re.match("userName", scim_filter)
    assert scim_filter[:8] == "userName"
    assert not isinstance(scim_filter[:8], ScimFilter)


def test_an_invalid_filter_is_rejected_on_creation():
    with pytest.raises(InvalidFilterException):
        ScimFilter("nonsense @")


def test_a_filter_can_be_built_from_another_filter():
    original = ScimFilter('userName eq "x"')
    assert ScimFilter(original) == original


def test_a_filter_exposes_its_parsed_form():
    assert ScimFilter('userName eq "x"').ast == Comparison(
        AttrPath("userName"), CompareOperator.eq, "x"
    )


def test_a_filter_exposes_the_model_it_is_bound_to():
    assert ScimFilter[User]('userName eq "x"').model is User
    assert ScimFilter('userName eq "x"').model is None


def test_an_unbound_filter_cannot_match():
    with pytest.raises(TypeError, match="bound filter type"):
        ScimFilter('userName eq "x"').match(User(user_name="x"))


def test_an_unbound_filter_resolves_to_nothing():
    assert ScimFilter('userName eq "x"').resolve(AttrPath("userName")) is None


def test_an_unbound_filter_resolves_no_comparison():
    assert ScimFilter('members co "x"').resolve_comparison(AttrPath("members")) is None


def test_an_unbound_filter_validates_to_nothing():
    """Without a model there is nothing to check beyond the syntax."""
    ScimFilter('nonexistent eq "x"')._validate_semantics()


def test_a_filter_resolves_its_own_attribute_paths():
    resolved = ScimFilter[User]('emails.type eq "work"').resolve(
        AttrPath("emails", "type")
    )
    assert resolved.field_name == "emails"


def test_a_filter_resolves_a_comparison_to_the_entry_values():
    """A comparison follows the ``value`` convention where a bare path does not.

    A transpiler that resolved the path as written would compare ``members``
    case-insensitively, where :meth:`match` compares ``members.value``
    case-exactly.
    """
    scim_filter = ScimFilter[Group]('members co "2819c223"')
    assert scim_filter.resolve(AttrPath("members")).sub_field_name is None

    resolved = scim_filter.resolve_comparison(AttrPath("members"))
    assert resolved.sub_field_name == "value"
    assert resolved.case_exact is True


def test_validating_a_whole_filter_walks_every_branch():
    with pytest.raises(InvalidFilterException):
        ScimFilter[User](
            "userName pr and not (active gt true) or title pr"
        )._validate_semantics()


def test_validating_a_value_selection_walks_its_inner_filter():
    with pytest.raises(InvalidFilterException):
        ScimFilter[User]('emails[nonexistent eq "x"]')._validate_semantics()


def test_validating_a_value_selection_on_a_scalar_list_stops_there():
    """A scalar list has no model to resolve the inner filter against."""
    ScimFilter[User]('schemas[value eq "urn:x"]')._validate_semantics()


def test_validating_tolerantly_ignores_unknown_attributes():
    ScimFilter[User]('nonexistent eq "x"')._validate_semantics(strict=False)


def test_a_filter_can_be_built_from_a_tree():
    tree = Comparison(AttrPath("userName"), CompareOperator.eq, "x")
    assert ScimFilter[User](tree).ast is tree
    assert ScimFilter[User](tree) == 'userName eq "x"'


def test_a_bound_filter_class_is_reused():
    assert ScimFilter[User] is ScimFilter[User]
    assert ScimFilter[User] is not ScimFilter[Group]


def test_subscripting_with_a_non_model_falls_back_to_generics():

    assert ScimFilter[Any] is not None


# --- Composition ---


def test_expressions_compose_with_the_boolean_operators():
    work = Comparison(AttrPath("type"), CompareOperator.eq, "work")
    primary = Present(AttrPath("primary"))
    assert str(work & primary) == 'type eq "work" and primary pr'
    assert str(work | primary) == 'type eq "work" or primary pr'
    assert str(~work) == 'not (type eq "work")'


def test_composing_the_same_operator_flattens_the_terms():
    a = Present(AttrPath("a"))
    combined = a & a & a
    assert combined.op == LogicalOperator.and_
    assert len(combined.terms) == 3


def test_composing_different_operators_keeps_them_nested():
    a, b, c = (Present(AttrPath(name)) for name in "abc")
    assert str((a | b) & c) == "(a pr or b pr) and c pr"
    assert str(a | (b & c)) == "a pr or b pr and c pr"


def test_a_composed_filter_can_be_evaluated():
    tree = Comparison(AttrPath("userName"), CompareOperator.eq, "x") & Present(
        AttrPath("title")
    )
    assert ScimFilter[User](tree).match(User(user_name="x", title="M"))


# --- Helpers ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, False),
        ("", False),
        ("x", True),
        ([], False),
        (["x"], True),
        ({}, False),
        ({"a": 1}, True),
        (b"", False),
        (b"x", True),
        (0, True),
        (False, True),
        (True, True),
    ],
)
def test_presence_of_a_value(value, expected):
    """``False`` and ``0`` are values, and are therefore present."""
    assert is_present(value) is expected


@pytest.mark.parametrize(
    ("actual", "expected_value", "operator", "expected"),
    [
        (None, None, "eq", True),
        (None, "x", "eq", False),
        (None, "x", "ne", True),
        ("x", None, "ne", True),
        (None, None, "ne", False),
        (None, "x", "co", False),
        (1, "x", "co", False),
        ("x", 1, "sw", False),
        ("x", "x", "gt", False),
        (2, 1, "gt", True),
        (1, 2, "lt", True),
        ("x", 1, "gt", False),
        (1, "x", "lt", False),
    ],
)
def test_comparing_two_values(actual, expected_value, operator, expected):
    """Incomparable values never match rather than raising."""
    assert compare(actual, expected_value, CompareOperator(operator)) is expected


def test_a_visitor_must_implement_every_node_type():

    class Incomplete(FilterVisitor[str]):
        pass

    for expression in [
        'a eq "x"',
        "a pr",
        'not (a eq "x")',
        "a pr and b pr",
        'a[b eq "x"]',
    ]:
        with pytest.raises(NotImplementedError):
            Incomplete().visit(parse_filter(expression))


def test_a_visitor_can_transpile_a_filter():
    """The visitor is the extension point a backend query is written with."""

    class SqlVisitor(FilterVisitor[str]):
        def visit_comparison(self, node):
            return f"{node.attr_path.attr} = {node.value!r}"

        def visit_present(self, node):
            return f"{node.attr_path.attr} IS NOT NULL"

        def visit_not(self, node):
            return f"NOT ({self.visit(node.expr)})"

        def visit_logical_expr(self, node):
            joiner = " AND " if node.op == LogicalOperator.and_ else " OR "
            return joiner.join(self.visit(term) for term in node.terms)

        def visit_value_path(self, node):
            return f"EXISTS (SELECT 1 FROM {node.attr_path.attr})"

    assert (
        SqlVisitor().visit(parse_filter('userName eq "x" and title pr'))
        == "userName = 'x' AND title IS NOT NULL"
    )
    assert SqlVisitor().visit(parse_filter('not (a eq "x")')) == "NOT (a = 'x')"
    assert (
        SqlVisitor().visit(parse_filter('emails[type eq "work"]'))
        == "EXISTS (SELECT 1 FROM emails)"
    )
    assert isinstance(parse_filter("a pr or b pr"), LogicalExpr)
    assert isinstance(parse_filter("not (a pr)"), Not)
    assert isinstance(parse_filter("a[b pr]"), ValuePath)


# --- Remaining corners ---


def test_validating_a_negation_tolerantly_walks_its_operand():
    ScimFilter[User]('not (nonexistent eq "x")')._validate_semantics(strict=False)


def test_validating_a_value_selection_on_an_unknown_attribute_tolerantly():
    ScimFilter[User]('nonexistent[type eq "x"]')._validate_semantics(strict=False)


def test_validating_a_comparison_on_an_unknown_attribute_tolerantly():
    ScimFilter[User]('nonexistent eq "x"')._validate_semantics(strict=False)


def test_validating_a_presence_walks_the_attribute():
    with pytest.raises(InvalidFilterException):
        ScimFilter[User]("nonexistent pr")._validate_semantics()


def test_an_unknown_attribute_makes_the_filter_invalid_not_the_path():
    """§3.12 defines ``invalidPath`` for the ``path`` of a PATCH operation.

    A search filter naming an attribute the model does not declare is an
    ``invalidFilter``, which is what a server answers ``400`` with.
    """
    with pytest.raises(InvalidFilterException) as exc_info:
        ScimFilter[User]('nonexistent eq "x"')._validate_semantics()
    assert exc_info.value.scim_type == "invalidFilter"
    assert "nonexistent" in str(exc_info.value)

    with pytest.raises(InvalidFilterException) as exc_info:
        ScimFilter[User]('emails.nonexistent eq "x"').resolve_comparison(
            AttrPath("emails", "nonexistent")
        )
    assert exc_info.value.scim_type == "invalidFilter"


def test_a_patch_path_keeps_naming_the_path_as_the_invalid_one():
    """The same unknown attribute reached through a PATCH path stays an ``invalidPath``."""
    with pytest.raises(PathNotFoundException) as exc_info:
        Path[User]("nonexistent").get(User(user_name="x"))
    assert exc_info.value.scim_type == "invalidPath"


def test_a_failure_without_a_position_still_reports_a_reason():
    """Not every parse failure carries a column to point at."""
    assert _error_detail(LarkError()) == "invalid syntax"


def test_the_model_of_a_sub_attribute_on_a_simple_attribute_is_unknown():
    """``target_model`` has nothing to point at when the head is not complex."""
    resolved = ResolvedAttribute(
        model=User,
        field_name="user_name",
        field_type=str,
        is_multivalued=False,
        sub_field_name="sub",
        sub_field_type=str,
    )
    assert resolved.target_model is None


def test_an_extension_attribute_read_from_the_extension_itself():
    """Evaluating against an extension instance needs no lookup on a resource."""
    extension = EnterpriseUser(employee_number="1")
    assert ScimFilter[EnterpriseUser]('employeeNumber eq "1"').match(extension)


def test_a_binary_operand_is_left_alone():
    """A ``binary`` attribute is compared against its base64 form."""
    resolved = resolve_attr_path(User, AttrPath("x509Certificates", "value"))
    assert coerce_value(resolved, "aGVsbG8=") == b"hello"


def test_a_complex_attribute_operand_is_left_alone():
    """There is nothing to coerce a whole complex attribute into."""
    resolved = resolve_attr_path(User, AttrPath("name"))
    assert coerce_value(resolved, "anything") == "anything"


def test_validating_a_conjunction_walks_every_term():
    """Every term of a logical expression is checked, not only the first."""
    ScimFilter[User](
        "userName pr and title pr and active eq true"
    )._validate_semantics()


def test_evaluating_a_value_selection_nested_by_hand_on_a_scalar_list():
    """The grammar forbids nesting, but a hand-built tree may still contain it."""
    nested = ValuePath(
        attr_path=AttrPath("schemas"),
        val_filter=ValuePath(
            attr_path=AttrPath("value"),
            val_filter=Present(AttrPath("value")),
        ),
    )
    user = User(
        user_name="x", schemas=["urn:ietf:params:scim:schemas:core:2.0:User", "urn:x"]
    )
    assert not ScimFilter[User](nested).match(user)


def test_resolution_skips_extensions_that_do_not_match_the_urn():
    """A resource may carry several extensions, only one of which is targeted."""

    class SuperHero(Extension):
        __schema__ = "example:extensions:SuperHero"
        superpower: Annotated[str | None, Required.false] = None

    model = User[EnterpriseUser | SuperHero]
    resolved = resolve_attr_path(
        model, AttrPath("superpower", uri="example:extensions:SuperHero")
    )
    assert resolved.model is SuperHero
    assert resolved.field_name == "superpower"


def test_presence_of_a_complex_attribute_without_any_value():
    """§3.4.2.2 matches "a non-empty node for complex attributes"."""
    assert not ScimFilter[User]("name pr").match(User(user_name="x", name=Name()))
    assert ScimFilter[User]("name pr").match(
        User(user_name="x", name=Name(family_name="Jensen"))
    )


def test_presence_of_a_multivalued_attribute_holding_empty_entries():
    assert not ScimFilter[User]("emails pr").match(
        User(user_name="x", emails=[User.Emails()])
    )
    assert ScimFilter[User]("emails pr").match(
        User(user_name="x", emails=[User.Emails(value="b@example.com")])
    )


def test_presence_of_a_falsy_value_still_matches():
    """``False`` and ``0`` are values, and are thus present."""
    assert ScimFilter[User]("active pr").match(User(user_name="x", active=False))


def test_a_bound_filter_rejects_an_operator_its_attribute_forbids():
    with pytest.raises(InvalidFilterException, match="operator 'gt' cannot be applied"):
        ScimFilter[User]("active gt true")


def test_a_bound_filter_rejects_a_value_its_attribute_cannot_take():
    with pytest.raises(InvalidFilterException, match="is not valid for attribute"):
        ScimFilter[User]('meta.created gt "yesterday"')


def test_a_bound_filter_rejects_a_value_selection_on_a_single_valued_attribute():
    with pytest.raises(InvalidFilterException, match="is not multi-valued"):
        ScimFilter[User]('userName[value eq "x"]')


def test_a_branch_the_evaluation_never_walks_is_still_rejected():
    """The boolean operators short-circuit, so evaluation alone would report it against some resources only."""
    with pytest.raises(InvalidFilterException, match="operator 'gt' cannot be applied"):
        ScimFilter[User]('userName eq "bjensen" and active gt true')


def test_a_bound_filter_accepts_an_attribute_the_model_does_not_declare():
    """§3.4.2.1 has an endpoint covering several resource types evaluate those to false."""
    scim_filter = ScimFilter[Group]('emails co "@example.com"')
    assert not scim_filter.match(Group(display_name="admins"))

    with pytest.raises(InvalidFilterException, match="Field not found: emails"):
        scim_filter._validate_semantics()


def test_an_unbound_filter_is_only_checked_for_syntax():
    """Nothing resolves attribute names until a filter is bound to a model."""
    assert ScimFilter("active gt true") == "active gt true"


def test_a_filter_binds_to_a_union_of_resource_types():
    """An endpoint covering several resource types binds them all, per §3.4.2.1."""
    scim_filter = ScimFilter[User | Group]('userName eq "bjensen"')
    assert scim_filter.models == (User, Group)
    assert scim_filter.model is None


def test_a_union_accepts_the_pipe_syntax():
    assert ScimFilter[User | Group]("members pr").models == (User, Group)


def test_a_union_evaluates_against_the_type_of_the_resource():
    """§3.4.2.1 has an attribute a resource type does not declare evaluate to false."""
    scim_filter = ScimFilter[User | Group]('userName eq "bjensen"')
    assert scim_filter.match(User(user_name="bjensen"))
    assert not scim_filter.match(Group(display_name="admins"))

    members = ScimFilter[User | Group]("members pr")
    assert members.match(Group(display_name="admins", members=[{"value": "u1"}]))
    assert not members.match(User(user_name="bjensen"))


def test_a_union_accepts_an_attribute_a_single_member_declares():
    """A root query names attributes of any type it serves, and of several at once."""
    ScimFilter[User | Group]("members pr")._validate_semantics()
    ScimFilter[User | Group](
        'userName eq "bjensen" or members pr'
    )._validate_semantics()


def test_a_union_rejects_an_attribute_no_member_declares():
    with pytest.raises(InvalidFilterException, match="Field not found: nonexistent"):
        ScimFilter[User | Group]('nonexistent eq "x"')._validate_semantics()


def test_a_union_rejects_a_comparison_its_attribute_cannot_take():
    with pytest.raises(InvalidFilterException, match="operator 'gt' cannot be applied"):
        ScimFilter[User | Group]("active gt true")


def test_resolving_a_union_takes_one_resource_type_at_a_time():
    """A transpiler emits one query per resource type, so it binds each of them in turn."""
    scim_filter = ScimFilter[User | Group]('userName eq "bjensen"')
    with pytest.raises(TypeError, match="union of User, Group"):
        scim_filter.resolve(AttrPath("userName"))

    with pytest.raises(TypeError, match="union of User, Group"):
        scim_filter.resolve_comparison(AttrPath("userName"))

    assert ScimFilter[User](scim_filter).resolve(AttrPath("userName")) is not None


def test_a_union_of_something_else_than_models_is_left_alone():
    assert ScimFilter[str | int]("userName pr").models == ()


def test_a_filter_is_usable_as_a_pydantic_field():
    """A field parses the filter assigned to it, and declares a string in a JSON schema.

    This is how a request message carries its filter: the parsing happens on
    the field, so a malformed filter is refused when the message is built.
    """

    class Query(PydanticBaseModel):
        scim_filter: ScimFilter[User]

    query = Query(scim_filter='userName eq "bjensen"')
    assert isinstance(query.scim_filter, ScimFilter)
    assert query.scim_filter.ast == Comparison(
        AttrPath("userName"), CompareOperator.eq, "bjensen"
    )
    assert query.model_dump() == {"scim_filter": 'userName eq "bjensen"'}
    assert Query.model_json_schema()["properties"]["scim_filter"]["type"] == "string"
    assert Query(scim_filter=query.scim_filter).scim_filter == query.scim_filter

    with pytest.raises(ValidationError, match="Expected str or ScimFilter, got int"):
        Query(scim_filter=42)
