from scim2_models.resources.enterprise_user import EnterpriseUser
from scim2_models.resources.user import User
from scim2_models.utils import _to_camel


def test_to_camel():
    """Test camilization utility."""
    assert _to_camel("foo") == "foo"
    assert _to_camel("Foo") == "foo"
    assert _to_camel("fooBar") == "fooBar"
    assert _to_camel("FooBar") == "fooBar"
    assert _to_camel("foo_bar") == "fooBar"
    assert _to_camel("Foo_bar") == "fooBar"
    assert _to_camel("foo_Bar") == "fooBar"
    assert _to_camel("Foo_Bar") == "fooBar"

    assert _to_camel("$foo$") == "$foo$"


def test_get_extension_for_schema():
    """Test get_extension_model method on Resource."""
    user = User[EnterpriseUser]()
    extension_class = user.get_extension_model(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert extension_class == EnterpriseUser

    extension_class = user.get_extension_model("urn:unknown:schema")
    assert extension_class is None
