from scim2_models.exceptions import InvalidFilterException
from scim2_models.exceptions import InvalidPathException
from scim2_models.exceptions import InvalidSyntaxException
from scim2_models.exceptions import InvalidValueException
from scim2_models.exceptions import InvalidVersionException
from scim2_models.exceptions import MutabilityException
from scim2_models.exceptions import NoTargetException
from scim2_models.exceptions import SensitiveException
from scim2_models.exceptions import TooManyException
from scim2_models.exceptions import UniquenessException
from scim2_models.messages.error import Error


def test_predefined_errors():
    for exc in (
        InvalidFilterException(),
        TooManyException(),
        UniquenessException(),
        MutabilityException(),
        InvalidSyntaxException(),
        InvalidPathException(),
        NoTargetException(),
        InvalidValueException(),
        InvalidVersionException(),
        SensitiveException(),
    ):
        assert isinstance(exc.to_error(), Error)
