from scim2_models.utils import to_camel


def test_to_camel():
    """Test camilization utility."""
    assert to_camel("foo") == "foo"
    assert to_camel("Foo") == "foo"
    assert to_camel("fooBar") == "fooBar"
    assert to_camel("FooBar") == "fooBar"
    assert to_camel("foo_bar") == "fooBar"
    assert to_camel("Foo_bar") == "fooBar"
    assert to_camel("foo_Bar") == "fooBar"
    assert to_camel("Foo_Bar") == "fooBar"

    assert to_camel("$foo$") == "$foo$"
