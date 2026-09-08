"""t-strings are Python 3.14 syntax, so conftest leaves this module out of older collections."""

from datetime import UTC
from datetime import datetime

import pytest

from scim2_models import InvalidFilterException
from scim2_models import ScimFilter
from scim2_models import User
from scim2_models.filters import Comparison
from scim2_models.filters import LogicalExpr


def test_an_interpolated_string_stays_a_value_whatever_it_contains():
    untrusted = 'x" or userName pr or userName eq "y'
    scim_filter = ScimFilter[User](t"userName eq {untrusted}")
    assert scim_filter == r'userName eq "x\" or userName pr or userName eq \"y"'
    assert isinstance(scim_filter.ast, Comparison)
    assert scim_filter.ast.value == untrusted
    assert not scim_filter.match(User(user_name="bjensen"))


def test_an_interpolated_value_keeps_its_type():
    assert ScimFilter[User](t"active eq {True}") == "active eq true"
    assert ScimFilter(t"count eq {18}") == "count eq 18"
    assert ScimFilter(t"title eq {None}") == "title eq null"


def test_an_interpolated_datetime_renders_as_a_string():
    since = datetime(2011, 5, 13, 4, 42, 34, tzinfo=UTC)
    scim_filter = ScimFilter[User](t"meta.lastModified gt {since}")
    assert scim_filter == 'meta.lastModified gt "2011-05-13T04:42:34+00:00"'


def test_a_conversion_or_a_format_spec_applies_before_quoting():
    assert ScimFilter(t"userName eq {18!r}") == 'userName eq "18"'
    assert ScimFilter(t"userName eq {7:03d}") == 'userName eq "007"'


def test_interpolations_render_where_they_stand():
    kind, domain = "work", "@example.com"
    scim_filter = ScimFilter[User](t"emails[type eq {kind} and value ew {domain}]")
    assert scim_filter == 'emails[type eq "work" and value ew "@example.com"]'
    user = User(
        user_name="bjensen", emails=[{"type": "work", "value": "b@example.com"}]
    )
    assert scim_filter.match(user)


def test_a_template_is_checked_like_the_string_it_renders():
    with pytest.raises(InvalidFilterException):
        ScimFilter(t"userName eq {1} eq")


def test_an_interpolated_filter_is_inserted_as_syntax():
    inner = ScimFilter('userName eq "bjensen"')
    scim_filter = ScimFilter[User](t"{inner} and title pr")
    assert scim_filter == 'userName eq "bjensen" and title pr'
    assert isinstance(scim_filter.ast, LogicalExpr)


def test_a_converted_filter_is_a_value_again():
    inner = ScimFilter('userName eq "bjensen"')
    assert ScimFilter(t"title eq {inner!s}") == r'title eq "userName eq \"bjensen\""'
