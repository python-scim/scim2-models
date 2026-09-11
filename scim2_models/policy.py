"""How a peer's deviations from the specification are treated."""

from contextvars import ContextVar
from enum import Enum
from types import TracebackType

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import SerializationInfo
from pydantic import ValidationInfo

_AMBIENT_POLICIES: ContextVar[tuple["ScimPolicy", ...]] = ContextVar(
    "scim2_models_policies", default=()
)
"""The policies of the blocks a call is running inside, innermost last."""


class ScimPolicy(BaseModel):
    """What a service tolerates from the payloads it reads.

    A :class:`~scim2_models.Context` says what a payload *is*: a creation
    request, a query response. A policy says how much its author is allowed to
    depart from :rfc:`RFC7643 <7643>` and :rfc:`RFC7644 <7644>`. The first is
    on the wire, symmetric, and defined by the specification; the second is
    local, and nothing on the wire announces it.

    Every setting defaults to the strict reading of the specification.

    >>> from scim2_models import ScimPolicy
    >>> ScimPolicy().unknown is ScimPolicy.Unknown.forbid
    True

    Name a policy at the call that reads or writes a payload:

    >>> from scim2_models import User
    >>> payload = {"schemas": [str(User.__schema__)], "userName": "bjensen"}
    >>> tolerant = ScimPolicy(unknown=ScimPolicy.Unknown.ignore)
    >>> User.model_validate(payload, scim_policy=tolerant).user_name
    'bjensen'

    Or open a block, which is how a server states once per request what it
    tolerates instead of naming it at every call:

    >>> with tolerant:
    ...     user = User.model_validate(payload)
    >>> user.user_name
    'bjensen'

    An argument named at the call site wins over the block, and leaving the
    block restores what it interrupted.

    A policy is settled once built: the pass running under one cannot be
    contradicted halfway through.
    """

    model_config = ConfigDict(frozen=True)

    class Unknown(str, Enum):
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
        restores it.
        """

        keep = "keep"
        """The payload is accepted and the attribute is dumped back.

        The original spelling is preserved. No attribute characteristic is
        declared for it, so no context filters it out.
        """

    class RemoveValue(str, Enum):
        """What becomes of a PATCH ``remove`` operation carrying a ``value``."""

        forbid = "forbid"
        """The operation is refused with ``invalidValue``.

        :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` reads the target of a
        ``remove`` in its ``path`` alone.
        """

        apply = "apply"
        """The ``value`` selects what to remove, as Microsoft Entra sends it."""

    unknown: Unknown = Unknown.forbid
    """What becomes of an attribute no model declares."""

    remove_value_as_filter: RemoveValue = RemoveValue.forbid
    """What becomes of a PATCH ``remove`` operation carrying a ``value``."""

    def __enter__(self) -> "ScimPolicy":
        """Make this policy the one every call in the block runs under."""
        _AMBIENT_POLICIES.set(_AMBIENT_POLICIES.get() + (self,))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Restore the policy the block interrupted."""
        _AMBIENT_POLICIES.set(_AMBIENT_POLICIES.get()[:-1])


_DEFAULT_POLICY = ScimPolicy()


def _ambient_policy() -> ScimPolicy | None:
    """Return the policy of the innermost open block, if any."""
    policies = _AMBIENT_POLICIES.get()
    return policies[-1] if policies else None


def _effective_policy(explicit: ScimPolicy | None = None) -> ScimPolicy:
    """Return the policy a call runs under, outside of a validation pass."""
    return explicit or _ambient_policy() or _DEFAULT_POLICY


def _policy(info: ValidationInfo | SerializationInfo) -> ScimPolicy:
    """Return the policy a validation or a serialization runs under.

    Passes that no call of ours started carry no context — an assignment
    revalidated under ``validate_assignment``, a round trip made by the PATCH
    machinery — and fall back on the ambient policy.
    """
    context = getattr(info, "context", None) or {}
    return context.get("scim_policy") or _ambient_policy() or _DEFAULT_POLICY
