"""How a peer's deviations from the specification are treated."""

from collections.abc import Callable
from enum import StrEnum
from types import TracebackType
from typing import Any
from unicodedata import normalize

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import SerializationInfo
from pydantic import ValidationInfo

from .utils import _AmbientStack

_AMBIENT_POLICIES: _AmbientStack["ScimPolicy"] = _AmbientStack("scim2_models_policies")
"""The policies of the blocks a call is running inside."""


def default_comparison_key(binding: Any, value: str) -> str:
    """Return the string that comparisons use in place of a value, by default.

    The string is normalized to Normalization Form C (NFC), and mapped to
    lowercase unless its attribute is ``caseExact``. This is the
    ``UsernameCaseMapped`` profile of :rfc:`8265`, without its width mapping
    and without the strings it refuses.

    >>> from scim2_models import Path, User, default_comparison_key
    >>> binding = Path[User]("userName").resolve()
    >>> default_comparison_key(binding, "BJensen")
    'bjensen'
    >>> binding = Path[User]("externalId").resolve()
    >>> default_comparison_key(binding, "BJensen")
    'BJensen'

    :param binding: The :class:`~scim2_models.AttributeBinding` of the
        attribute the string is a value of.
    :param value: The string to compare.
    :returns: The string that comparisons use in place of the value.
    """
    normalized = normalize("NFC", value)
    if binding.case_exact:
        return normalized

    # Mapping to lowercase does not preserve the normalization form, so NFC is
    # applied to its result too, and every operand comes out in the same form.
    return normalize("NFC", normalized.lower())


class ScimPolicy(BaseModel):
    """What a service tolerates from the payloads it reads.

    A :class:`~scim2_models.Context` says what a payload *is*: a creation
    request, a query response. A policy says how much its author is allowed to
    depart from :rfc:`RFC7643 <7643>` and :rfc:`RFC7644 <7644>`. The first is
    on the wire, symmetric, and defined by the specification; the second is
    local, and nothing on the wire announces it.

    A policy also says how attribute values are compared, which the
    specification leaves to the service provider.

    Every setting defaults to the strict reading of the specification, except
    :attr:`comparison_key`. A tolerance that cannot confuse one payload with
    another, such as a PATCH value key that is an attribute path, needs no
    setting.

    >>> from scim2_models import ScimPolicy
    >>> ScimPolicy().unknown is ScimPolicy.Unknown.forbid
    True

    Pass a policy to the call that reads or writes a payload:

    >>> from scim2_models import User
    >>> payload = {"schemas": [str(User.__schema__)], "userName": "bjensen"}
    >>> tolerant = ScimPolicy(unknown=ScimPolicy.Unknown.ignore)
    >>> User.model_validate(payload, scim_policy=tolerant).user_name
    'bjensen'

    Or open a block. A server does this once per request, instead of passing
    the policy to every call:

    >>> with tolerant:
    ...     user = User.model_validate(payload)
    >>> user.user_name
    'bjensen'

    A policy passed to the call wins over the block. Leaving the block
    restores the policy it interrupted.

    A policy cannot change once built. A validation or a dump sees the same
    settings from start to end.
    """

    model_config = ConfigDict(frozen=True)

    class Unknown(StrEnum):
        """What becomes of an attribute no model declares."""

        forbid = "forbid"
        """The payload is refused with a validation error.

        §5.3 of the SCIM interoperability profile asks a service provider to
        reject the attributes and the schema URNs it does not define.
        """

        ignore = "ignore"
        """The payload is accepted and the attribute is dropped.

        It stays readable on
        :attr:`~scim2_models.BaseModel.unknown_attributes`, and no dump
        restores it. A PATCH operation on such an attribute changes
        nothing.
        """

        keep = "keep"
        """The payload is accepted and the attribute is dumped back.

        The original spelling is preserved. No attribute characteristic is
        declared for it, so no context filters it out. In the value or the
        path of a PATCH operation, it has no field to write to, so it is
        dropped as with ``ignore``.
        """

    class RemoveValue(StrEnum):
        """What becomes of a PATCH ``remove`` operation carrying a ``value``."""

        forbid = "forbid"
        """The operation is refused with ``invalidValue``.

        :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` reads the target of a
        ``remove`` in its ``path`` alone.
        """

        apply = "apply"
        """The ``value`` selects what to remove, as Microsoft Entra sends it."""

    class UnmatchedPathFilter(StrEnum):
        """What becomes of a PATCH operation whose path filter matches no entry."""

        forbid = "forbid"
        """The ``add`` or ``replace`` operation is rejected with ``noTarget``.

        :rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>` requires it for
        ``replace``, and Table 9 of :rfc:`RFC7644 §3.12 <7644#section-3.12>`
        defines ``noTarget`` for a filter that "yields no match".
        """

        create = "create"
        """The entry the filter describes is added, as Microsoft Entra expects.

        Only ``eq`` comparisons on sub-attributes, joined by ``and``, describe
        an entry. The entry gets the compared values, then the operation
        writes its value. Any other filter is still rejected with
        ``noTarget``. A ``remove`` is not affected: it changes nothing.
        """

    unknown: Unknown = Unknown.forbid
    """What becomes of an attribute no model declares."""

    remove_value_as_filter: RemoveValue = RemoveValue.forbid
    """What becomes of a PATCH ``remove`` operation carrying a ``value``."""

    unmatched_path_filter: UnmatchedPathFilter = UnmatchedPathFilter.forbid
    """What becomes of a PATCH operation whose path filter matches no entry."""

    comparison_key: Callable[[Any, str], str] = default_comparison_key
    """The function giving the string that comparisons use in place of a value.

    Filters, sorting, uniqueness checks and the PATCH operations that look for
    a value compare strings through it. The callable has two arguments:
    the :class:`~scim2_models.AttributeBinding` of an attribute, and a
    string value of that attribute. It returns the string that comparisons
    use in place of the value.

    It must be deterministic, free of side effects, and return its input
    unchanged when given its own output: a storage may keep the form it
    returns, and apply it again. It raises :exc:`ValueError` on a string it
    cannot prepare. Such a string is equal to no other, and a request that
    writes it is refused with ``invalidValue``.

    The default, :func:`~scim2_models.default_comparison_key`, does not apply
    the PRECIS rules :rfc:`RFC7644 §5 <7644#section-5>` requires for
    ``userName`` and ``password``. It is the one setting whose default is not
    the strict reading. :doc:`/how-to/compare-values` shows how to apply them.
    """

    def __enter__(self) -> "ScimPolicy":
        """Make this policy the one every call in the block runs under."""
        _AMBIENT_POLICIES.enter(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Restore the policy the block interrupted."""
        _AMBIENT_POLICIES.exit(self)


_DEFAULT_POLICY = ScimPolicy()


def _ambient_policy() -> ScimPolicy | None:
    """Return the policy of the innermost open block, if any."""
    return _AMBIENT_POLICIES.get()


def _effective_policy(explicit: ScimPolicy | None = None) -> ScimPolicy:
    """Return the policy a call runs under, outside of a validation pass."""
    return explicit or _ambient_policy() or _DEFAULT_POLICY


def _policy(info: ValidationInfo | SerializationInfo) -> ScimPolicy:
    """Return the policy a validation or a serialization runs under.

    A policy passed at the call wins over the one of the provider passed at
    the call, which wins over the ambient policy.

    Passes that no call of ours started carry no context — an assignment
    revalidated under ``validate_assignment``, a round trip made by the PATCH
    machinery — and fall back on the ambient policy.
    """
    context = getattr(info, "context", None) or {}
    provider = context.get("scim_provider")
    return (
        context.get("scim_policy")
        or (provider.policy if provider else None)
        or _ambient_policy()
        or _DEFAULT_POLICY
    )
