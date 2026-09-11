Validate and serialize SCIM payloads
====================================

Use this guide when an application receives or sends a SCIM resource outside a framework
integration. It shows which context each HTTP operation calls for, how to apply the projection a
client asked for, what :meth:`~scim2_models.Resource.replace` settles on a ``PUT``, and how to
answer a rejected payload. It assumes the :doc:`../overview`.
:doc:`../explanation/scim-contexts` gives the rules behind the contexts, and the
:doc:`../integrations/index` guides wire them into a framework.

Choose the context of an operation
----------------------------------

A :class:`~scim2_models.Context` names one representation of a resource. Requests are validated
in a request context, responses are validated and serialized in the matching response context:

.. list-table::
   :header-rows: 1
   :widths: 34 33 33

   * - Operation
     - Validate the request with
     - Serialize the response with
   * - ``POST /Users``
     - :attr:`~scim2_models.Context.RESOURCE_CREATION_REQUEST`
     - :attr:`~scim2_models.Context.RESOURCE_CREATION_RESPONSE`
   * - ``GET /Users/<id>``, ``GET /Users``
     - :attr:`~scim2_models.Context.RESOURCE_QUERY_REQUEST`
     - :attr:`~scim2_models.Context.RESOURCE_QUERY_RESPONSE`
   * - ``PUT /Users/<id>``
     - :attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST`
     - :attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_RESPONSE`
   * - ``PATCH /Users/<id>``
     - :attr:`~scim2_models.Context.RESOURCE_PATCH_REQUEST`
     - :attr:`~scim2_models.Context.RESOURCE_PATCH_RESPONSE`
   * - ``POST /Users/.search``
     - :attr:`~scim2_models.Context.SEARCH_REQUEST`
     - :attr:`~scim2_models.Context.SEARCH_RESPONSE`

:attr:`~scim2_models.Context.DEFAULT` applies neither set of rules, and suits a resource held in
application state rather than exchanged over HTTP.

Validate a creation request
---------------------------

Pass the creation-request context while parsing a client payload. It rejects required attributes
that are absent and removes server-managed read-only attributes:

.. doctest::

   >>> from scim2_models import Context, User
   >>> payload = {
   ...     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
   ...     "id": "client-supplied",
   ...     "userName": "bjensen",
   ... }
   >>> user = User.model_validate(payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST)
   >>> user.id is None
   True

Return only the attributes a client asked for
---------------------------------------------

A client narrows a response with the ``attributes`` or ``excludedAttributes`` query parameters of
:rfc:`RFC7644 §3.9 <7644#section-3.9>`. Read them into a
:class:`~scim2_models.ResponseParameters` and hand it to the dump method:

.. doctest::

   >>> from scim2_models import ResponseParameters
   >>> user.id = "2819c223-7f76-453a-919d-413861904646"
   >>> user.display_name = "Babs Jensen"
   >>> user.title = "Manager"
   >>> user.model_dump(
   ...     scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
   ...     response_parameters=ResponseParameters(attributes=["userName"]),
   ... )  # doctest: +NORMALIZE_WHITESPACE
   {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'],
    'id': '2819c223-7f76-453a-919d-413861904646',
    'userName': 'bjensen'}

``id`` and ``schemas`` stay in the response although the projection did not ask for them: an
attribute annotated :attr:`Returned.always <scim2_models.Returned.always>` cannot be left out.
Symmetrically, an attribute annotated :attr:`Returned.never <scim2_models.Returned.never>`, such
as :attr:`User.password <scim2_models.User.password>`, never appears whatever a client asks.

A :class:`~scim2_models.SearchRequest` is a :class:`~scim2_models.ResponseParameters`, so a server
answering ``POST /.search`` passes the request it received rather than spelling the two parameters
out.

Replace a stored resource
-------------------------

A ``PUT`` carries a complete resource, and what the client sends is not the whole story: the
server owns the read-only attributes, and the immutable ones keep the value they were created
with. Parse the payload in the replacement-request context, then call
:meth:`~scim2_models.Resource.replace` with the resource currently stored:

.. doctest::

   >>> from scim2_models import Meta
   >>> stored = User(
   ...     id="2819c223-7f76-453a-919d-413861904646",
   ...     user_name="bjensen",
   ...     meta=Meta(resource_type="User", version='W/"1"'),
   ... )
   >>> replacement = User.model_validate(
   ...     {
   ...         "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
   ...         "userName": "bjensen",
   ...         "displayName": "Babs Jensen",
   ...     },
   ...     scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
   ... )
   >>> replacement.replace(stored)
   >>> replacement.id
   '2819c223-7f76-453a-919d-413861904646'
   >>> replacement.meta.version
   'W/"1"'

The read-only attributes of the stored resource are carried over, so the response reports the
identity and the version the server holds. An immutable attribute whose value differs from the
stored one raises :class:`~scim2_models.MutabilityException` instead. The check reaches the
sub-attributes of a complex attribute, and the entries of a multi-valued one that the stored
resource also holds: an entry is recognised by its ``value``, so adding and removing entries
stays free, while changing an immutable sub-attribute of one that stays is refused. Two cases stay
uncompared rather than risk refusing a legitimate replacement: an entry whose ``value``
designates several entries, and an immutable reference, two spellings of one URI being
equivalent per :rfc:`RFC7643 §2.4 <7643#section-2.4>`.

Answer a rejected payload
-------------------------

A payload that breaks a SCIM rule raises a Pydantic
:class:`~pydantic_core.ValidationError`. :meth:`~scim2_models.Error.from_validation_error` turns
one of its errors into the :class:`~scim2_models.Error` message a SCIM client expects, with the
HTTP status and the ``scimType`` that go with it:

.. doctest::

   >>> from pydantic import ValidationError
   >>> from scim2_models import Error
   >>> try:
   ...     User.model_validate(
   ...         {"userName": None},
   ...         scim_ctx=Context.RESOURCE_CREATION_REQUEST,
   ...     )
   ... except ValidationError as exc:
   ...     error = Error.from_validation_error(exc.errors()[0])
   >>> error.status, error.scim_type
   (400, 'invalidValue')

Serialize that error with :attr:`~scim2_models.Context.DEFAULT`, and answer it with its own
``status`` as the HTTP status code. A :class:`~scim2_models.SCIMException` raised while applying an
operation, such as :class:`~scim2_models.MutabilityException`, carries the same information.

:doc:`../explanation/patch` describes what a PATCH operation does to its target.
