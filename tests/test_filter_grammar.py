import pytest

from scim2_models import InvalidFilterException
from scim2_models import InvalidPathException
from scim2_models.filters import AttrPath
from scim2_models.filters import CompareOperator
from scim2_models.filters import Comparison
from scim2_models.filters import FilterNode
from scim2_models.filters import FilterVisitor
from scim2_models.filters import LogicalExpr
from scim2_models.filters import LogicalOperator
from scim2_models.filters import Not
from scim2_models.filters import Present
from scim2_models.filters import ValuePath
from scim2_models.filters import parse_filter
from scim2_models.filters import parse_path


@pytest.mark.parametrize(
    "expression",
    [
        'userName eq "bjensen"',
        'name.familyName co "O\'Malley"',
        'userName sw "J"',
        'urn:ietf:params:scim:schemas:core:2.0:User:userName sw "J"',
        "title pr",
        'meta.lastModified gt "2011-05-13T04:42:34Z"',
        'meta.lastModified ge "2011-05-13T04:42:34Z"',
        'meta.lastModified lt "2011-05-13T04:42:34Z"',
        'meta.lastModified le "2011-05-13T04:42:34Z"',
        'title pr and userType eq "Employee"',
        'title pr or userType eq "Intern"',
        'schemas eq "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"',
        'userType eq "Employee" and (emails co "example.com" or emails.value co "example.org")',
        'userType ne "Employee" and not (emails co "example.com" or emails.value co "example.org")',
        'userType eq "Employee" and (emails.type eq "work")',
        'userType eq "Employee" and emails[type eq "work" and value co "@example.com"]',
        'emails[type eq "work" and value co "@example.com"] or ims[type eq "xmpp" and value co "@foo.com"]',
    ],
)
def test_the_examples_of_the_rfc_are_parsed(expression):
    """Every filter of Figure 2 of §3.4.2.2 has to be accepted."""
    assert parse_filter(expression) is not None


@pytest.mark.parametrize(
    "attr_name",
    [
        "never",
        "prime",
        "nullable",
        "organization",
        "andrew",
        "equipment",
        "lease",
        "greatest",
        "coworker",
        "swimming",
        "network",
        "notation",
        "trueValue",
        "presence",
    ],
)
def test_attribute_names_starting_like_a_keyword(attr_name):
    """An attribute whose name begins with an operator or keyword is not one.

    ``ATTRNAME = ALPHA *(nameChar)`` accepts them all, so the lexer has to
    require a word boundary after every keyword.
    """
    node = parse_filter(f'{attr_name} eq "x"')
    assert node == Comparison(AttrPath(attr_name), CompareOperator.eq, "x")


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:userName pr",
            AttrPath("userName", uri="urn:ietf:params:scim:schemas:core:2.0:User"),
        ),
        (
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value pr",
            AttrPath(
                "manager",
                sub_attr="value",
                uri="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            ),
        ),
        (
            "URN:IETF:PARAMS:SCIM:SCHEMAS:CORE:2.0:USER:userName pr",
            AttrPath("userName", uri="URN:IETF:PARAMS:SCIM:SCHEMAS:CORE:2.0:USER"),
        ),
    ],
)
def test_urn_is_split_on_its_last_colon(expression, expected):
    """A qualified attribute path separates its URN from the attribute name."""
    assert parse_filter(expression) == Present(expected)


def test_dollar_prefixed_attribute_name():
    """``$ref`` is accepted even though the published ABNF excludes it.

    Errata 8924 of RFC 7643 corrects ``ATTRNAME`` to allow a leading ``$``.
    """
    assert parse_filter("groups.$ref pr") == Present(AttrPath("groups", "$ref"))


@pytest.mark.parametrize("expression", ["not (title pr)", "not(title pr)"])
def test_negation_with_and_without_space(expression):
    """A space between ``not`` and its parenthesis is optional.

    The published ABNF forbids it while the examples of the RFC use it, which
    errata 7319 corrects.
    """
    assert parse_filter(expression) == Not(Present(AttrPath("title")))


@pytest.mark.parametrize(
    ("expression", "expected_ops"),
    [
        ("a eq 1 and b eq 2 or c eq 3", ["or", "and"]),
        ("a eq 1 or b eq 2 and c eq 3", ["or", "and"]),
    ],
)
def test_and_binds_tighter_than_or(expression, expected_ops):
    """Conjunction binds tighter than disjunction, so ``or`` sits at the root."""
    node = parse_filter(expression)
    assert node.op == LogicalOperator(expected_ops[0])
    nested = [term for term in node.terms if isinstance(term, LogicalExpr)]
    assert [term.op.value for term in nested] == expected_ops[1:]


def test_comparison_binds_tighter_than_logical_operators():
    """Attribute operators are applied before logical ones, per errata 4670."""
    node = parse_filter('title sw "M" and userType eq "Employee"')
    assert node == LogicalExpr(
        op=LogicalOperator.and_,
        terms=(
            Comparison(AttrPath("title"), CompareOperator.sw, "M"),
            Comparison(AttrPath("userType"), CompareOperator.eq, "Employee"),
        ),
    )


def test_chained_conjunction_is_flattened():
    """Repeating the same operator yields a single node holding every term."""
    node = parse_filter("a eq 1 and b eq 2 and c eq 3")
    assert node.op == LogicalOperator.and_
    assert len(node.terms) == 3


def test_grouping_overrides_precedence():
    """Parentheses make a disjunction the operand of a conjunction."""
    node = parse_filter("(a eq 1 or b eq 2) and c eq 3")
    assert node.op == LogicalOperator.and_
    assert node.terms[0].op == LogicalOperator.or_


def test_value_path_accepts_a_full_boolean_expression():
    """Brackets hold conjunctions, disjunctions, negations and parentheses.

    The published ABNF restricts ``valFilter`` in a way errata 4690 and 7322
    correct, the latter allowing nested logical expressions.
    """
    node = parse_filter('emails[type eq "work" or (type eq "home" and primary pr)]')
    assert isinstance(node, ValuePath)
    assert node.attr_path == AttrPath("emails")
    assert node.val_filter.op == LogicalOperator.or_


def test_value_path_accepts_a_negation():
    node = parse_filter('emails[not (type eq "work")]')
    assert node.val_filter == Not(
        Comparison(AttrPath("type"), CompareOperator.eq, "work")
    )


@pytest.mark.parametrize(
    "expression",
    [
        'emails[type eq "work" and emails[type eq "home"]]',
        'emails[emails[type eq "work"].value co "x"]',
    ],
)
def test_nested_value_path_is_rejected(expression):
    """A value selection cannot contain another one.

    The published ABNF allows it through ``logExp``, which errata 4690
    identifies as unintended.
    """
    with pytest.raises(InvalidFilterException):
        parse_filter(expression)


@pytest.mark.parametrize(
    "expression",
    ['emails[type eq "work"].value', 'emails[type eq "work"].value eq "x"'],
)
def test_sub_attribute_after_value_path_is_rejected_in_a_filter(expression):
    """Only a PATCH path may follow a value selection with a sub-attribute."""
    with pytest.raises(InvalidFilterException):
        parse_filter(expression)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('x eq "text"', "text"),
        ("x eq true", True),
        ("x eq false", False),
        ("x eq null", None),
        ("x eq 42", 42),
        ("x eq -42", -42),
        ("x eq 4.5", 4.5),
        ("x eq -2.5e3", -2500.0),
        ("x eq 0", 0),
        (r'x eq "with \" quote"', 'with " quote'),
        (r'x eq "with \\ backslash"', "with \\ backslash"),
        (r'x eq "tab\there"', "tab\there"),
    ],
)
def test_comparison_values_follow_json_syntax(expression, expected):
    """``compValue`` is built on the JSON rules for values."""
    assert parse_filter(expression).value == expected


@pytest.mark.parametrize(
    "operator",
    ["eq", "ne", "co", "sw", "ew", "gt", "lt", "ge", "le"],
)
def test_every_comparison_operator_is_parsed(operator):
    node = parse_filter(f'x {operator} "v"')
    assert node.op == CompareOperator(operator)


@pytest.mark.parametrize(
    "expression",
    [
        'userName EQ "x"',
        'userName Eq "x"',
        'a eq "x" AND b pr',
        'a eq "x" Or b pr',
        "NOT (a pr)",
        "a PR",
    ],
)
def test_keywords_are_case_insensitive(expression):
    """Operators and keywords ignore case, as required by §3.4.2.2."""
    assert parse_filter(expression) is not None


@pytest.mark.parametrize(
    "expression",
    [
        'userName    eq     "x"',
        'userName eq"x"',
        '  userName eq "x"  ',
        'emails[ type eq "work" ]',
    ],
)
def test_surrounding_whitespace_is_tolerated(expression):
    """Servers receive filters with irregular spacing, which stays acceptable."""
    assert parse_filter(expression) is not None


@pytest.mark.parametrize(
    "expression",
    [
        "",
        "   ",
        "userName",
        "userName eq",
        'eq "x"',
        "emails[]",
        "a eq 1 and",
        "and a eq 1",
        "a eq 1)",
        "(a eq 1",
        'a eq "unterminated',
        "a @ 1",
        "1a eq 2",
        "a..b eq 1",
        "a.b.c eq 1",
    ],
)
def test_malformed_filters_are_rejected(expression):
    with pytest.raises(InvalidFilterException):
        parse_filter(expression)


def test_a_string_with_an_invalid_escape_is_rejected():
    """``compValue`` follows the JSON rules, which only allow known escapes.

    An unknown one is a syntax error located like any other, rather than a
    failure raised later while decoding the string.
    """
    with pytest.raises(InvalidFilterException) as exc_info:
        parse_filter(r'userName eq "a\q"')
    assert exc_info.value.detail == "invalid syntax at column 13"


def test_a_path_string_with_an_invalid_escape_is_rejected():
    with pytest.raises(InvalidPathException) as exc_info:
        parse_path(r'emails[type eq "a\q"]')
    assert exc_info.value.detail == "invalid syntax at column 16"


def test_rejection_reports_the_offending_column():
    """A parse failure says where it happened, so a server can explain itself."""
    with pytest.raises(InvalidFilterException) as exc_info:
        parse_filter('userName eq "x" and')
    assert "column" in exc_info.value.detail


def test_rejection_carries_the_offending_filter():
    with pytest.raises(InvalidFilterException) as exc_info:
        parse_filter("nonsense @")
    assert exc_info.value.filter == "nonsense @"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("members", AttrPath("members")),
        ("name.familyName", AttrPath("name", "familyName")),
        (
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
            AttrPath(
                "employeeNumber",
                uri="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            ),
        ),
    ],
)
def test_attribute_paths_are_valid_patch_paths(path, expected):
    assert parse_path(path) == expected


def test_value_path_carries_its_sub_attribute_in_a_patch_path():
    """``PATH = attrPath / valuePath [subAttr] / attrExp``."""
    node = parse_path('members[value eq "2819c223"].displayName')
    assert node == ValuePath(
        attr_path=AttrPath("members"),
        val_filter=Comparison(AttrPath("value"), CompareOperator.eq, "2819c223"),
        sub_attr="displayName",
    )


def test_value_path_without_sub_attribute_is_a_valid_patch_path():
    node = parse_path('addresses[type eq "work"]')
    assert isinstance(node, ValuePath)
    assert node.sub_attr is None


def test_bare_comparison_is_a_valid_patch_path():
    """Errata 7122 adds ``attrExp``, the only way to target a scalar list value."""
    node = parse_path('schemas eq "urn:ietf:params:scim:schemas:core:2.0:User"')
    assert node == Comparison(
        AttrPath("schemas"),
        CompareOperator.eq,
        "urn:ietf:params:scim:schemas:core:2.0:User",
    )


def test_bare_presence_is_a_valid_patch_path():
    assert parse_path("title pr") == Present(AttrPath("title"))


@pytest.mark.parametrize(
    "path",
    [
        "",
        'emails[type eq "work"] and active eq true',
        'not (emails[type eq "work"])',
        '(emails[type eq "work"])',
        "name..familyName",
        "a.b.c",
        "123invalid",
        "invalid@path",
    ],
)
def test_malformed_patch_paths_are_rejected(path):
    """A PATCH path holds no boolean expression at its root."""
    with pytest.raises(InvalidPathException):
        parse_path(path)


def test_path_rejection_carries_the_offending_path():
    with pytest.raises(InvalidPathException) as exc_info:
        parse_path("name..familyName")
    assert exc_info.value.path == "name..familyName"


@pytest.mark.parametrize(
    "expression",
    [
        'userName eq "bjensen"',
        "title pr",
        'emails[type eq "work" or (type eq "home" and value ew "@example.com")]',
        'title pr or userType eq "Intern" and active eq true',
        "(a eq 1 or b eq 2) and c eq 3",
        "a eq 1 and (b eq 2 or c eq 3)",
        "not (a eq 1) and b pr",
        "x eq null",
        "y eq false",
        "z eq -2.5",
        r'display eq "with \" quote"',
        'urn:ietf:params:scim:schemas:core:2.0:User:userName eq "x"',
    ],
)
def test_rendering_a_filter_yields_an_equivalent_filter(expression):
    """Rendering then reparsing a filter gives back the same tree."""
    tree = parse_filter(expression)
    assert parse_filter(str(tree)) == tree


@pytest.mark.parametrize(
    "path",
    [
        "members",
        "name.familyName",
        'members[value eq "abc"].displayName',
        'addresses[type eq "work"]',
        'schemas eq "urn:x:y:z"',
    ],
)
def test_rendering_a_path_yields_an_equivalent_path(path):
    tree = parse_path(path)
    assert parse_path(str(tree)) == tree


def test_nodes_are_hashable():
    """Immutability lets a node be cached or used as a dictionary key."""
    node = parse_filter('userName eq "x"')
    assert {node: "value"}[parse_filter('userName eq "x"')] == "value"


def test_visiting_an_unknown_node_type_is_rejected():
    with pytest.raises(TypeError, match="Unsupported filter node"):
        FilterVisitor().visit(FilterNode())


def test_a_number_out_of_range_is_rejected():
    """``1e400`` reads as an infinity, which the ABNF has no syntax for."""
    with pytest.raises(InvalidFilterException, match="number out of range"):
        parse_filter("userName eq 1e400")

    assert parse_filter("userName eq 1e300").value == 1e300


def test_rendering_a_value_json_cannot_express_is_rejected():
    """A node built by hand can hold a float no filter could carry."""
    node = Comparison(AttrPath("userName"), CompareOperator.eq, float("inf"))
    with pytest.raises(ValueError, match="not JSON compliant"):
        str(node)
