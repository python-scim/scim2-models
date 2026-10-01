Changelog
=========

[0.10.2] - Unreleased
---------------------

Fixed
^^^^^
- :meth:`PatchOp.build_from <scim2_models.PatchOp.build_from>` leaves out the read-only
  sub-attributes of multi-valued attributes, such as a read-only ``members.display``.
  The patch it builds is no longer rejected.

[0.10.1] - 2026-09-30
---------------------

Removed
^^^^^^^
- The ``attributes`` and ``excluded_attributes`` parameters of
  :meth:`~scim2_models.BaseModel.model_dump` and
  :meth:`~scim2_models.BaseModel.model_dump_json`, deprecated in 0.8.0. Pass a
  :class:`~scim2_models.ResponseParameters` as ``response_parameters`` instead. :issue:`141`

Fixed
^^^^^
- :class:`~scim2_models.ListResponse` reads the pagination capabilities of the
  :class:`~scim2_models.ScimProvider`, including a provider opened around the validation.
  The last page of a server that only supports cursor pagination no longer needs ``totalResults``.
- The policy of a :class:`~scim2_models.ScimProvider` passed as ``scim_provider`` applies to
  the validation and the serialization. It wins over the policy of an open block.
  ``scim_policy`` still wins over both.

[0.10.0] - 2026-09-30
---------------------

Added
^^^^^
- Support for :rfc:`RFC9865 <9865>`
- :meth:`Resource.replace <scim2_models.Resource.replace>` returns whether the replacement
  changes the resource, the order of multi-valued entries aside. A server can keep
  ``meta.version`` and ``meta.lastModified`` when a PUT changes nothing.
- In the :attr:`~scim2_models.Context.BULK_REQUEST` context, an invalid operation of a
  :class:`~scim2_models.BulkRequest` no longer fails the whole request. It becomes its own failed
  result, with a ``status`` and an :class:`~scim2_models.Error`, as
  :rfc:`RFC7644 §3.7.3 <7644#section-3.7.3>` requires. Under a
  :class:`~scim2_models.ScimProvider`, each operation is read as the resource type its ``path``
  targets. An endpoint that serves none of the types of the request fails the operation with
  ``invalidPath``.
- :attr:`BulkOperation.endpoint <scim2_models.BulkOperation.endpoint>` and
  :attr:`BulkOperation.resource_id <scim2_models.BulkOperation.resource_id>` read the target of
  an operation from its ``path``.

Changed
^^^^^^^
- :meth:`SCIMException.from_error <scim2_models.SCIMException.from_error>` reconstructs
  :class:`~scim2_models.InvalidCursorException`, :class:`~scim2_models.ExpiredCursorException` and
  :class:`~scim2_models.InvalidCountException` from an :class:`~scim2_models.Error` carrying the
  matching ``scimType``, as :rfc:`RFC9865 §2.1 <9865#section-2.1>` defines them. They used to fall
  back to the base :class:`~scim2_models.SCIMException`.
- :attr:`AttributeBinding.urn <scim2_models.AttributeBinding.urn>` and the error messages
  that quote it spell the attribute as the schema declares it, such as ``userName``, whatever
  case the path used.
- Validation errors locate the value with an attribute path, such as ``emails[1].value``, and no
  longer expose internal names of pydantic.

Fixed
^^^^^
- A :class:`~scim2_models.ScimProvider` or :class:`~scim2_models.ScimPolicy` block that exits in
  a context where it did not enter, such as another thread or another asyncio task, raises an
  error. It used to remove the provider or the policy of another block.

Security
^^^^^^^^
- The ``password`` of a :class:`~scim2_models.User` is case-exact, so ``password eq "SECRET"``
  no longer matches ``secret``. RFC 7643 declares it case-insensitive, but compares passwords
  by salted hash (:rfc:`RFC7643 §4.1.1 <7643#section-4.1.1>`), and the rules of
  :rfc:`RFC7644 §5 <7644#section-5>` keep the case of passwords.
- A filter or a PATCH path that nests more than 32 expressions, such as ``not(not(...))``, is
  refused with ``invalidFilter`` or ``invalidPath``. A deep one used to raise a
  :class:`RecursionError`. Parentheses and chains of ``and`` or ``or`` do not count.
- Filters and paths from clients no longer grow memory without limit. Each unknown attribute
  name, and each spelling of a known one such as ``USERNAME``, used to stay in memory for the
  life of the process. Filters and paths longer than 1024 characters are no longer cached.
- Write-only and never-returned attributes, such as ``password``, no longer appear in the
  ``repr`` of a model. A :class:`~scim2_models.PatchOperation` bound to a resource type, as in a
  ``PatchOp[User]``, leaves out a ``value`` that writes one of them. Validation error messages no
  longer include the input values, which
  :meth:`ValidationError.errors() <pydantic_core.ValidationError.errors>` still returns.
- Under :attr:`RemoveValue.apply <scim2_models.ScimPolicy.RemoveValue.apply>`, a PATCH
  ``remove`` whose ``value`` has a key that is not an attribute name, such as
  ``"value pr or value"``, is refused with ``invalidValue``.
- In a :class:`~scim2_models.BulkRequest`, the ``data`` of a ``PATCH`` operation must be a
  :class:`~scim2_models.PatchOp`, and the ``data`` of a ``POST`` or a ``PUT`` must be a resource.
  A full resource sent as the ``data`` of a ``PATCH`` used to be accepted with its read-only
  attributes, such as ``id`` and ``groups``. An invalid ``data`` only reports the errors of the
  type the method expects.
- In the :attr:`~scim2_models.Context.BULK_REQUEST` context, the ``location``, ``status`` and
  ``response`` of an operation are ignored, and they are left out of a serialized request.
  A client can no longer make an operation look like it failed.

[0.9.0] - 2026-09-27
--------------------

Added
^^^^^
- :attr:`ScimPolicy.unmatched_path_filter <scim2_models.ScimPolicy.unmatched_path_filter>` can
  make a PATCH ``add`` or ``replace`` create the entry its path filter describes when no entry
  matches, as Microsoft Entra ID expects. By default, the operation still fails with ``noTarget``.

Changed
^^^^^^^
- Python 3.11 is now the minimum supported version.
- The enumerations, such as :class:`~scim2_models.Mutability`, are :class:`~enum.StrEnum`:
  :class:`str` and f-strings give their value, ``readOnly`` rather than ``Mutability.read_only``.
- In a model built from a schema, an attribute named after a member of the model, such as
  ``copy``, is held as ``copy_``. Its SCIM name is unchanged.
- A PATCH ``add`` whose path filter matches no entry, such as ``emails[type eq "work"].value``
  on a user without a work email, now fails with ``noTarget`` instead of silently doing nothing.
  :meth:`Path.set <scim2_models.Path.set>` raises :class:`~scim2_models.NoTargetException` in
  that case when strict.
- A PATCH ``add`` or ``replace`` on a filtered path, such as ``emails[type eq "work"]``, merges
  its value into the matching entries instead of replacing them
  (:rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>`). The entries are updated in place, so the
  immutable sub-attributes of a group member cannot be changed this way.

Fixed
^^^^^
- A :class:`~scim2_models.PatchOperation` with a null value keeps it when dumped. A ``replace``
  that clears its target used to be sent without a value.
- Setting a null value under an unset complex attribute or extension no longer creates an empty
  one, and no longer reports the resource as modified.
- A :class:`~scim2_models.PatchOp` with no operation, or with an operation other than ``add``,
  ``remove`` and ``replace``, fails with ``invalidValue`` instead of a validation error without
  ``scimType``.
- A PATCH ``add`` or ``replace`` on a complex attribute keeps the sub-attributes its value leaves
  out, instead of replacing the whole attribute (:rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>`).
- A PATCH ``add`` without a path adds to the multi-valued attributes in its value, like an
  ``add`` with a path, instead of replacing their values.
- A key of a PATCH value can be an attribute path, such as ``name.givenName`` or
  ``urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber``, as Microsoft
  Entra ID and its SCIM Validator send. It used to be rejected as an undeclared attribute.
- Undeclared attributes and sub-attributes in a PATCH value follow
  :attr:`ScimPolicy.unknown <scim2_models.ScimPolicy.unknown>`.
- PATCH checks immutable attributes at every level and in every operation, including operations
  with no path, an empty path or a schema URN, and the removal of an extension. For example, the
  ``value`` of a group member can be added and removed, but not changed
  (:rfc:`RFC7643 §4.2 <7643#section-4.2>`). Setting a first value with ``replace``, or writing
  back the current value, is accepted.
- PATCH checks read-only attributes at every level, such as the ``displayName`` of the
  enterprise ``manager``. A path to one is rejected. A value that contains one is
  rejected only if it changes it, so an attribute sent back as it was read is accepted. Okta, for
  example, sends back the ``id`` of a group it renames.
- PATCH rejects a change to a required attribute only when it leaves the attribute unset
  (:rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>`). Removing some values of a required
  multi-valued attribute, removing a sub-attribute of a required complex attribute, or adding an
  empty list is now accepted. Required sub-attributes and extensions are checked too.
- A PATCH ``replace`` without a value fails with ``invalidValue`` instead of clearing its
  target. So does an operation whose path targets the resource or an extension with a value that
  is not an object, which used to be ignored.
- A PATCH ``replace`` that sets several ``primary`` entries fails with ``invalidValue``, like
  ``add`` already did, instead of keeping one of them at random.
- :meth:`PatchOp.patch <scim2_models.PatchOp.patch>` raises
  :class:`~scim2_models.InvalidValueException` when the attribute rejects a value, instead of a
  pydantic :class:`~pydantic.ValidationError` without ``scimType``.
- :meth:`PatchOp.patch <scim2_models.PatchOp.patch>` no longer reports a resource as modified
  when an operation writes a complex or multi-valued value it already has.
- A PATCH path to an undeclared attribute follows
  :attr:`ScimPolicy.unknown <scim2_models.ScimPolicy.unknown>`, like a value does. With ``ignore``
  or ``keep``, the operation changes nothing instead of failing the whole patch with
  ``invalidPath``. An undeclared sub-attribute in a filter still fails with ``invalidFilter``.

Security
^^^^^^^^
- A published schema can no longer break the models built from it, nor make
  :meth:`ScimProvider.from_discovery <scim2_models.ScimProvider.from_discovery>` raise another
  exception than :class:`~scim2_models.ScimProviderError`. Complex attributes are nested two
  levels deep at most, as :rfc:`RFC7643 §7 <7643#section-7>` allows for ``Schema``.
- :func:`~scim2_models.get_model_by_payload` matches no model when ``schemas`` is not a list
  of strings.

[0.8.2] - 2026-09-25
--------------------

Added
^^^^^
- :meth:`SearchRequest.sort <scim2_models.SearchRequest.sort>` orders resources as
  :rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>` describes, for a server keeping them in memory.

Changed
^^^^^^^
- A filter on a write-only attribute, such as ``password``, only takes ``eq``, ``ne`` and ``pr``,
  :rfc:`RFC7643 §4.1.1 <7643#section-4.1.1>` comparing it for equality alone. Any other operator
  answers ``invalidFilter``.
- :attr:`SearchRequest.sort_by <scim2_models.SearchRequest.sort_by>` refuses a complex
  attribute, such as ``name`` or ``addresses``, where :rfc:`RFC7644 §3.4.2.3
  <7644#section-3.4.2.3>` asks for a sub-attribute, a binary attribute, and a write-only
  attribute, such as ``password``. A multi-valued attribute holding a ``value``, such as
  ``emails``, is still sorted on it.

Fixed
^^^^^
- :attr:`Resource.id <scim2_models.Resource.id>` is case-exact, as :rfc:`RFC7643 §3.1
  <7643#section-3.1>` declares it, so filters and orders on it respect the case.
- The :class:`~scim2_models.Meta` sub-attributes are read-only, and ``resourceType`` and
  ``version`` are case-exact, as :rfc:`RFC7643 §3.1 <7643#section-3.1>` declares them.
- :meth:`Resource.replace <scim2_models.Resource.replace>` keeps a write-only attribute, such
  as ``password``, that the replacement leaves out, and clears it on an explicit null only. A
  client never gets that value back, so a PUT built from a GET used to erase it.
- A model built with :meth:`Resource.from_schema <scim2_models.Resource.from_schema>` or
  :meth:`Extension.from_schema <scim2_models.Extension.from_schema>` is named as its schema, and
  its docstring is the description of the schema, so ``to_schema`` publishes both again. A
  schema named ``petOwner`` used to build a ``PetOwner`` class, and to lose its description.

[0.8.1] - 2026-09-25
--------------------

Changed
^^^^^^^
- :meth:`Error.from_validation_error <scim2_models.Error.from_validation_error>` follows
  :rfc:`RFC7644 §3.12 <7644#section-3.12>`: an invalid value answers ``invalidValue``, where
  it used to be ``invalidSyntax`` or nothing, and an invalid payload structure answers
  ``invalidSyntax``.

Fixed
^^^^^
- :meth:`~scim2_models.SCIMException.from_error` keeps the :class:`~scim2_models.Error`
  object it is built from, and :meth:`~scim2_models.SCIMException.to_error` gives it back.
  The status and the scimType a server sent used to be replaced by the ones of the
  exception class, which dropped everything it has no class for, such as a ``429`` status
  or a vendor specific scimType.
- Validation error messages name attributes as SCIM spells them, such as ``userName`` instead
  of ``user_name``, and extensions by their schema URN.

[0.8.0] - 2026-09-20
--------------------

Added
^^^^^
- :class:`~scim2_models.ScimFilter` parses the ``filter`` query parameter and matches resources
  against it with :meth:`~scim2_models.ScimFilter.match`. See :doc:`explanation/filters`.
  :issue:`17`
- PATCH paths take a value selection, such as ``emails[type eq "work"].value``.
- :class:`~scim2_models.SearchRequest` and :class:`~scim2_models.ResponseParameters` take the
  resource type an endpoint serves, as in ``SearchRequest[User]`` or ``SearchRequest[User |
  Group]``. Their ``filter``, ``sortBy``, ``attributes`` and ``excludedAttributes`` resolve
  against those models, so a misspelled attribute is caught at validation time.
- :meth:`Path.resolve <scim2_models.Path.resolve>` answers the
  :class:`~scim2_models.AttributeBinding` a path designates.
- :meth:`ScimFilter.quote <scim2_models.ScimFilter.quote>` renders a value as a filter literal.
  On Python 3.14, :class:`~scim2_models.ScimFilter` and :class:`~scim2_models.Path` take a
  t-string and quote what is interpolated. See :doc:`how-to/build-filters`.
- :class:`~scim2_models.ScimProvider` describes a SCIM service: the models it serves, and the
  objects its discovery endpoints answer. :meth:`~scim2_models.ScimProvider.from_discovery`
  builds one from what a service publishes, and a service that cannot be described is refused
  with :class:`~scim2_models.ScimProviderError`. See :doc:`how-to/describe-a-scim-service`.
  :issue:`108`
- An extension may be declared required, as in ``User[Annotated[EnterpriseUser, Required.true]]``.
  A creation or a replacement request that leaves it out is refused.
  See :doc:`how-to/define-custom-models`. :issue:`105`
- :class:`~scim2_models.ScimPolicy` states how much a payload may depart from the specification
  and still be read. Name a policy at the call, or open a ``with`` block on it or on a provider
  carrying one. Every setting defaults to the strict reading, so nothing changes until one is
  chosen. See :doc:`how-to/tolerate-a-nonconformant-peer`. :issue:`85` :issue:`108`
- :meth:`~scim2_models.BaseModel.model_dump` and
  :meth:`~scim2_models.BaseModel.model_dump_json` take a ``response_parameters``, the
  :class:`~scim2_models.ResponseParameters` a client sent. A :class:`~scim2_models.SearchRequest`
  is one, so a server answering ``POST /.search`` passes the request it received. :issue:`141`
- :meth:`~scim2_models.BaseModel.model_validate`,
  :meth:`~scim2_models.BaseModel.model_validate_json`,
  :meth:`~scim2_models.BaseModel.model_dump` and
  :meth:`~scim2_models.BaseModel.model_dump_json` take a ``scim_provider`` and a ``scim_spc``, so
  that the rules the specification makes conditional on a declared capability are read. A ``with``
  block opened on a provider lends both. See :doc:`how-to/describe-a-scim-service`.
- :meth:`~scim2_models.PatchOp.build_from` builds the patch turning one resource state into
  another. Only the attributes the wanted state names take part in the comparison.
  See :doc:`how-to/build-a-patch`. :issue:`104`
- Bulk messages are validated, in the new :attr:`~scim2_models.Context.BULK_REQUEST` and
  :attr:`~scim2_models.Context.BULK_RESPONSE` contexts. Each operation's
  :attr:`~scim2_models.BulkOperation.data` is checked as the single request it stands for.
  See :ref:`helpers-bulk`. :pr:`149`
- lark is a new dependency.

Changed
^^^^^^^
- :meth:`Resource.from_schema <scim2_models.Resource.from_schema>` and
  :meth:`Extension.from_schema <scim2_models.Extension.from_schema>` refuse a schema declaring
  two attributes whose names only differ by case, and report both.
  :rfc:`RFC7643 §2.1 <7643#section-2.1>` :issue:`166`
- Attribute names are matched case-insensitively, and nothing else: ``{"user-name": "x"}``, which
  0.7 read as ``userName``, is now an unknown attribute that
  :attr:`~scim2_models.ScimPolicy.unknown` governs. Paths, filters and ``sortBy`` resolve the same
  way, and a model whose fields answer to one attribute name raises a :class:`TypeError` where it
  is defined. :rfc:`RFC7643 §2.1 <7643#section-2.1>` :issue:`166`
- The bulk models take the resource type their operations carry, as in ``BulkRequest[User]`` or
  ``BulkRequest[User | Group]``, and raise a :class:`TypeError` when used bare. A payload the type
  parameter does not cover is now refused, and a bulk response no longer dumps ``path``.
- :class:`~scim2_models.ListResponse` raises a :class:`TypeError` when used without the resource
  type its entries carry, as :class:`~scim2_models.PatchOp` and the bulk models do. A bare
  ``ListResponse`` used to answer a pydantic error naming ``Resource``.
- A message type parameter must name resource types. ``ListResponse[str]`` used to build a class
  that read anything as its entries.
- ``ListResponse[Resource]``, ``PatchOp[Resource]`` and their bulk counterparts stay writable where
  a type is expected, and raise a :class:`TypeError` when they read or build a payload.
  ``PatchOp[Resource]`` used to be refused as a type, and ``ListResponse[Resource]`` used to read
  payloads.
- :attr:`SearchRequest.filter <scim2_models.SearchRequest.filter>` is a
  :class:`~scim2_models.ScimFilter` instead of a :class:`str`, so a malformed filter is rejected
  at validation time.
- Paths are parsed with the :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` grammar, so malformed ones
  such as ``emails[`` or ``userName ==``, which used to be accepted, are now rejected.
- :attr:`Path.model <scim2_models.Path.model>` answers the model a path designates when it names
  no attribute, and :data:`None` otherwise. :meth:`~scim2_models.Path.resolve` answers what it
  used to.
- :attr:`SearchRequest.sort_by <scim2_models.SearchRequest.sort_by>` naming an attribute no
  resource type declares answers ``invalidPath``, where it used to be carried to the endpoint.
- A PATCH ``remove`` carrying a ``value`` is refused with ``invalidValue``, at validation and
  when applied. It used to remove the entries equal to that ``value``. Set
  :attr:`~scim2_models.ScimPolicy.remove_value_as_filter` to keep reading it.
- A PATCH reaching an extension attribute takes the extended resource type, as in
  ``PatchOp[User[EnterpriseUser]]``. ``PatchOp[User]`` used to carry such an operation to the
  endpoint, and now refuses a path its type parameter leaves out.

Removed
^^^^^^^
- ``Resource.get_by_schema`` and ``Resource.get_by_payload``, deprecated in 0.6.13. Use
  :func:`~scim2_models.get_model_by_schema` and :func:`~scim2_models.get_model_by_payload`, whose
  ``resource_types`` parameter is named ``models``.
- The ``original`` parameter of :meth:`~scim2_models.BaseModel.model_validate`, deprecated in
  0.6.7. Validate the payload, then call :meth:`~scim2_models.Resource.replace` on the result to
  compare it against the stored resource: an immutable attribute that changed raises
  :exc:`~scim2_models.MutabilityException` from ``replace`` instead of a
  :exc:`~pydantic.ValidationError` from ``model_validate``.
- ``Path.field_name``, ``Path.field_type``, ``Path.is_multivalued``, ``Path.get_annotation`` and
  ``Path.urn``. Use :meth:`~scim2_models.Path.resolve`, whose
  :class:`~scim2_models.AttributeBinding` carries them.
- ``Path.is_prefix_of`` and ``Path.has_prefix``. They compared the text of two paths, which
  anything between brackets defeated.

Deprecated
^^^^^^^^^^
- The ``attributes`` and ``excluded_attributes`` parameters of
  :meth:`~scim2_models.BaseModel.model_dump` and
  :meth:`~scim2_models.BaseModel.model_dump_json`. Pass a
  :class:`~scim2_models.ResponseParameters` as ``response_parameters`` instead; naming both
  raises a :exc:`TypeError`. They will be removed in 0.9.0. :issue:`141`

Fixed
^^^^^
- A PATCH operation carrying no ``path`` that unassigns an extension declared
  :attr:`Required.true <scim2_models.Required.true>` is refused. :issue:`166`
- A filter or a path accepts a ``$`` anywhere in an attribute name, as ``nameChar`` allows.
  :issue:`166`
- A schema declaring several attributes that yield one Python name builds a field for each of
  them: the attribute already spelled as that name keeps it, and the others are held under their
  SCIM name. An attribute is read under the name SCIM gives it, as in ``resource["employeeId"]``.
  :issue:`166`
- A pydantic error spells the attribute as SCIM does, ``userName`` and ``$ref``, and so does the
  JSON schema a model publishes. :issue:`166`
- A field declaring its own ``alias`` is read under it, and an unknown attribute is refused under
  the spelling the peer used. :issue:`166`
- An extension is read under its class name as well as under its URN, so
  ``User[EnterpriseUser](EnterpriseUser=extension)`` is accepted and a resource carrying an
  extension survives a dump without aliases read back. :issue:`166`
- A bulk model indexed with something other than a resource type names itself in the error, where
  ``BulkRequest[str]`` used to tell the caller to write ``PatchOp[User]``.
- A subclass of a parameterized message, such as ``class Users(ListResponse[User])``, reads its
  payloads with the type parameter it inherits. It used to raise an :exc:`IndexError`.
- A PATCH operation targeting an attribute of an extension answers for the constraints that
  extension declares, where it used to look them up on the resource and find none. A refused
  operation no longer leaves the extension instantiated on the resource.
- A PATCH operation carrying no ``path`` accepts a resource as its ``value``, and checks the
  attributes it names against the model. They used to go through unexamined.
- A PATCH operation whose ``path`` names an attribute the resource schema does not declare is
  refused with ``invalidPath``. :issue:`164`
- A refused PATCH ``add`` on a multi-valued attribute leaves the attribute as it was. The entry
  used to be appended before being validated, and outlived the failure.
- A PATCH operation carrying no ``path`` marks the attributes it assigns as set, so
  ``exclude_unset`` dumps them.
- A PATCH ``replace`` of a :attr:`Required.true <scim2_models.Required.true>` attribute with a
  null value or an empty array is refused, and an operation leaving such an attribute unassigned
  answers ``invalidValue`` instead of ``mutability``.
- Attributes annotated :attr:`~scim2_models.Mutability.read_only` are left out of a payload
  dumped in the :attr:`~scim2_models.Context.RESOURCE_PATCH_REQUEST` context, as they already are
  in a creation or a replacement request.
- Paths resolve against the attributes a model declares instead of the values a resource carries,
  so ``name.unknown`` is refused on a resource carrying no ``name``, and ``userName.foo`` answers
  ``invalidPath`` instead of raising an :exc:`AttributeError`.
- A path crossing a multi-valued attribute, such as ``emails.value``, reads, writes and removes
  the sub-attribute of every entry, where it used to raise an :exc:`AttributeError` or do nothing.
- A path names a ``$ref`` sub-attribute under that spelling, as in ``members.$ref``, both when it
  is parsed and in :meth:`~scim2_models.Path.iter_paths`.
- A schema URN carries its attribute behind a colon, so
  ``urn:ietf:params:scim:schemas:core:2.0:UserId`` no longer reads as the ``id`` of a ``User``,
  and a URN that is neither the schema of the model nor that of one of its extensions designates
  nothing.
- :meth:`Resource.replace <scim2_models.Resource.replace>` checks the immutable and read-only
  sub-attributes of the entries a multi-valued attribute keeps.
- :meth:`Resource.to_schema <scim2_models.Resource.to_schema>` publishes the members of a string
  enumeration as ``canonicalValues``, and describes the resource alone on
  ``User[EnterpriseUser]``, where it used to publish the extension URN as an attribute of the
  ``User`` schema.
- :attr:`GroupMember.display <scim2_models.GroupMember.display>` is ``readWrite``, as
  :rfc:`RFC7643 §8.7.1 <7643#section-8.7.1>` declares it.
- Subscribing a :class:`~scim2_models.Path` to a model, and parameterizing a resource with an
  extension, no longer keep those classes alive for as long as the process runs. A server
  building a model per schema it discovers used to accumulate every one of them.

[0.7.0] - 2026-09-05
--------------------

Added
^^^^^
- :func:`~scim2_models.get_model_by_schema` and :func:`~scim2_models.get_model_by_payload` look a
  model up among any sequence of :class:`~scim2_models.ScimObject` subclasses, and reflect the
  input types in the returned type.
- :class:`~scim2_models.ScimObject` and ``AnyScimObject`` are exposed in the public API, so a
  downstream project can annotate a value that is either a resource or a message.
- :class:`~scim2_models.ExtensibleStringEnum` is exposed in the public API, so a custom model can
  suggest canonical values without restricting them.
- :meth:`~scim2_models.BaseModel.model_validate_json` takes a ``scim_ctx`` parameter, like the
  other validation and serialization methods, so a JSON payload can be validated without being
  decoded first. :issue:`150`

Changed
^^^^^^^
- :class:`~scim2_models.Path` subclasses :class:`str` instead of
  :class:`~collections.UserString`, so a path goes wherever a string does. Its string operators
  answer a plain :class:`str`: ``Path("emails.value")[6:]`` answers ``".value"`` where it used to
  answer ``invalidPath``.
- A malformed :class:`~scim2_models.Path` answers ``invalidPath`` instead of ``invalidSyntax``,
  and building one directly raises :exc:`~scim2_models.InvalidPathException` instead of a plain
  :exc:`ValueError`. A model holding one still raises a :exc:`~pydantic.ValidationError`, now
  naming the field and carrying the ``scimType``.
- :attr:`SearchRequest.sort_by <scim2_models.SearchRequest.sort_by>`,
  :attr:`~scim2_models.ResponseParameters.attributes` and
  :attr:`~scim2_models.ResponseParameters.excluded_attributes` refuse a path selecting values,
  such as ``emails[type eq "work"]``. The attribute notation of
  :rfc:`RFC7644 §3.10 <7644#section-3.10>` names an attribute, not the values it holds.
- ``model_dump`` and ``model_dump_json`` move from :class:`~scim2_models.ScimObject` to
  :class:`~scim2_models.BaseModel`, so every model is dumped in a SCIM context by default:
  ``Name(family_name="Doe").model_dump()`` returns ``{"familyName": "Doe"}`` instead of
  ``{"family_name": "Doe"}``.
- :meth:`~scim2_models.BaseModel.model_dump` with ``scim_ctx=None`` returns the native pydantic
  dump, ``None`` values included, as its documentation states. Pass ``exclude_none=True`` to get
  the former output.
- :meth:`~scim2_models.Resource.replace` leaves the fields it copies from the original resource
  unset, so ``model_fields_set`` only holds the attributes the client asserted.
- Attributes suggesting canonical values accept values outside that set, and match it
  case-insensitively: ``Email(type="WORK").type`` is ``Email.Type.work``. ``str()`` on them
  answers the SCIM value instead of the enum representation, and their JSON schema advertises the
  set as ``examples`` rather than a restrictive ``enum``. This covers the ``type`` of
  :class:`~scim2_models.Email`, :class:`~scim2_models.PhoneNumber`, :class:`~scim2_models.Im`,
  :class:`~scim2_models.Photo`, :class:`~scim2_models.Address` and
  :class:`~scim2_models.AuthenticationScheme`. :issue:`34`
- The ``schemas`` attribute is built from the model definition on serialization. It holds what a
  peer asserted otherwise, and is empty when the payload omitted it, so the omission stays
  visible in ``model_fields_set``. It is not subject to attribute filtering anymore.
- A resource omitting its ``schemas`` attribute is read instead of being rejected, which covers
  the partial responses of :rfc:`7644` §3.4.3. Its type comes from the
  :class:`~scim2_models.ListResponse` parameter, so a response holding several resource types
  still cannot tell what an unlabelled resource is. :issue:`20`
- A ``schemas`` attribute that does not contain the model base schema is rejected whatever the
  validation context. It used to be accepted without a SCIM context.

Fixed
^^^^^
- The ``readOnly``, ``immutable`` and ``required`` constraints of a PATCH operation are checked
  against the attribute its path resolves to, instead of a literal field name match. They used
  to be skipped whenever the two differed, so ``userName`` could be removed and a path spelled
  ``GROUPS`` could write to a ``readOnly`` attribute.
- :meth:`~scim2_models.Resource.replace` checks the constraints an extension declares,
  recursively.
- ``reference`` and ``binary`` attributes are case-exact, unless a schema states otherwise.
  :rfc:`7643` §2.3.6 and §2.3.7, `erratum 6001 <https://www.rfc-editor.org/errata/eid6001>`_
- :class:`~scim2_models.ResourceType` ``endpoint`` and the ``value`` of
  :class:`~scim2_models.GroupMember` and :class:`~scim2_models.GroupMembership` are case-exact,
  the latter holding resource ``id`` values. :rfc:`7643` errata
  `8475 <https://www.rfc-editor.org/errata/eid8475>`_ and
  `8472 <https://www.rfc-editor.org/errata/eid8472>`_
- :meth:`~scim2_models.Resource.from_schema` reads a ``reference`` attribute missing the optional
  ``referenceTypes`` as a :class:`~scim2_models.URI` reference, instead of crashing.
- Looking a model up by schema no longer crashes when the model list mixes resources with
  messages such as :class:`~scim2_models.ListResponse`.

Removed
^^^^^^^
- ``Error.make_*_error()`` class methods, deprecated in 0.6.0. Use the matching
  :class:`~scim2_models.SCIMException` subclass and its ``to_error()`` method instead.
- The ``ExternalReference`` and ``URIReference`` aliases, deprecated in 0.6.0. Use
  :class:`~scim2_models.External` and :class:`~scim2_models.URI` instead.
- The ``Reference[Literal["X"]]`` syntax, deprecated in 0.6.0. Use ``Reference["X"]`` instead.
- Defining a model schema with a ``schemas`` default value, deprecated in 0.6.0. Use
  ``__schema__ = URN("...")`` instead. Note that ``__schema__`` only accepts valid URNs, while
  the removed syntax silently ignored invalid ones.

Deprecated
^^^^^^^^^^
- ``Resource.get_by_schema`` and ``Resource.get_by_payload`` are deprecated in favor of
  :func:`~scim2_models.get_model_by_schema` and :func:`~scim2_models.get_model_by_payload`.
  Their ``resource_types`` parameter is named ``models`` in the new functions.
  They will be removed in 0.8.0.

Performance
^^^^^^^^^^^
- Validation and serialization each run through a single model validator and serializer, where
  every SCIM context used to add its own.
- Commonly used field metadata is cached on ``__scim_info__``, and so is attribute name
  normalization.

[0.6.12] - 2026-04-13
---------------------

Added
^^^^^
- Compatibility with Pydantic 2.13.

[0.6.11] - 2026-04-10
---------------------

Added
^^^^^
- add uniqueness, returned and case_exact filters to iter_paths

[0.6.10] - 2026-04-07
---------------------

Fixed
^^^^^
- replace copies readOnly and preserves immutable fields

[0.6.9] - 2026-04-07
--------------------

Added
^^^^^
- ``*RequestContext`` and ``*ResponseContext`` generic type aliases that wrap :class:`~scim2_models.SCIMValidator` and :class:`~scim2_models.SCIMSerializer` for each SCIM context (e.g. ``CreationRequestContext[User]``, ``CreationResponseContext[User]``).

[0.6.8] - 2026-04-03
--------------------

Added
^^^^^
- :class:`~scim2_models.SCIMValidator` and :class:`~scim2_models.SCIMSerializer` Pydantic Annotated markers to inject a SCIM :class:`~scim2_models.Context` during validation and serialization. :issue:`130`
- :class:`~scim2_models.MutabilityException` handler in framework integration examples (FastAPI, Flask, Django).

Deprecated
^^^^^^^^^^
- The ``original`` parameter of :meth:`~scim2_models.BaseModel.model_validate` is deprecated. Use :meth:`~scim2_models.Resource.replace` on the validated instance instead. Will be removed in 0.8.0.

Fixed
^^^^^
- PATCH operations on :attr:`~scim2_models.Mutability.immutable` fields are now validated at runtime per :rfc:`RFC 7644 §3.5.2 <7644#section-3.5.2>`: ``add`` is only allowed when the field has no previous value, ``replace`` is only allowed with the same value, and ``remove`` is only allowed on unset fields.

[0.6.7] - 2026-04-02
--------------------

Added
^^^^^
- :class:`~scim2_models.ListResponse` ``model_dump`` and ``model_dump_json`` now accept ``attributes`` and ``excluded_attributes`` parameters. :issue:`59`
- New :class:`~scim2_models.ResponseParameters` model for :rfc:`RFC7644 §3.9 <7644#section-3.9>` ``attributes`` and ``excludedAttributes`` query parameters. :class:`~scim2_models.SearchRequest` inherits from it.
- :class:`~scim2_models.ResponseParameters` and :class:`~scim2_models.SearchRequest` accept comma-separated strings for ``attributes`` and ``excludedAttributes``.

[0.6.6] - 2026-03-12
--------------------

Fixed
^^^^^
- Fix `ListResponse.totalResults` validation when `resources` is none. :pr:`133`

[0.6.5] - 2026-03-10
--------------------

Fixed
^^^^^
- Fix extension serialization crash when an extension is declared but not populated on a resource serialized outside of SCIM context (e.g. FastAPI ``response_model``). :pr:`131`

[0.6.4] - 2026-02-05
--------------------

Added
^^^^^
- :class:`~scim2_models.SCIMException` now accepts an optional ``scim_ctx`` parameter to indicate the SCIM context in which the exception occurred.

[0.6.3] - 2026-01-29
--------------------

Fixed
^^^^^
- Fix ``model_json_schema()`` generation for models containing :class:`~scim2_models.Reference` or :class:`~scim2_models.Path` fields. :issue:`125`
- Group ``displayName`` is required. :rfc:`7643` `erratum 5368 <https://www.rfc-editor.org/errata/eid5368>`_ :issue:`123` :pr:`128`
- :class:`~scim2_models.GroupMembership` ``$ref`` only references ``Group``. :rfc:`7643` `erratum 8471 <https://www.rfc-editor.org/errata/eid8471>`_
- :class:`~scim2_models.Manager` ``value`` is case-exact. :rfc:`7643` `erratum 8472 <https://www.rfc-editor.org/errata/eid8472>`_
- :class:`~scim2_models.ResourceType` ``name`` and ``endpoint`` have server uniqueness. :rfc:`7643` `erratum 8475 <https://www.rfc-editor.org/errata/eid8475>`_
- Complex attributes don't have ``uniqueness`` in schema representation. :rfc:`7643` `erratum 6004 <https://www.rfc-editor.org/errata/eid6004>`_

[0.6.2] - 2026-01-25
--------------------

Added
^^^^^
- :meth:`SCIMException.from_error <scim2_models.SCIMException.from_error>` to create an exception from a SCIM :class:`~scim2_models.Error` object.

[0.6.1] - 2026-01-25
--------------------

Added
^^^^^
- Allow ``Path`` objects in Pydantic validation methods.

[0.6.0] - 2026-01-25
--------------------

Added
^^^^^
- Resources define their schema URN with a ``__schema__`` classvar instead of a ``schemas`` default value. :issue:`110`
- :class:`~scim2_models.External` and :class:`~scim2_models.URI` marker classes for reference types.

Changed
^^^^^^^
- Introduce a :class:`~scim2_models.Path` object to handle paths. :issue:`111`
- :class:`~scim2_models.Reference` type parameters simplified:

  - ``Reference[ExternalReference]`` → ``Reference[External]``
  - ``Reference[URIReference]`` → ``Reference[URI]``
  - ``Reference[Literal["User"]]`` → ``Reference["User"]``
  - ``Reference[Literal["User"] | Literal["Group"]]`` → ``Reference[Union["User", "Group"]]``

- :class:`~scim2_models.Reference` now validates URI format for ``External`` and ``URI`` types.
- :class:`~scim2_models.Reference` inherits from ``str`` directly instead of ``UserString``.

Fixed
^^^^^
- Only allow one primary complex attribute value to be true. :issue:`10`

Deprecated
^^^^^^^^^^
- Defining ``schemas`` with a default value is deprecated. Use ``__schema__ = URN("...")`` instead.
- ``Error.make_*_error()`` methods are deprecated. Use ``<Exception>.to_error()`` instead.
- ``Reference[Literal["X"]]`` syntax is deprecated. Use ``Reference["X"]`` instead. Will be removed in 0.7.0.
- ``ExternalReference`` alias is deprecated. Use :class:`~scim2_models.External` instead. Will be removed in 0.7.0.
- ``URIReference`` alias is deprecated. Use :class:`~scim2_models.URI` instead. Will be removed in 0.7.0.
- Validation that the base schema is present in ``schemas`` during SCIM context validation.
- Validation that extension schemas are known during SCIM context validation.
- Introduce SCIM exceptions hierarchy (:class:`~scim2_models.SCIMException` and subclasses) corresponding to RFC 7644 error types. :issue:`103`
- :meth:`Error.from_validation_error <scim2_models.Error.from_validation_error>` to convert Pydantic :class:`~pydantic_core.ValidationError` to SCIM :class:`~scim2_models.Error`.
- :meth:`PatchOp.patch <scim2_models.PatchOp.patch>` auto-excludes other ``primary`` values when setting one to ``True``. :issue:`116`

[0.5.2] - 2026-01-22
--------------------

Fixed
^^^^^
- Sub-attributes of requested complex attributes are now included in responses. :issue:`114`

[0.5.1] - 2025-11-07
--------------------

Added
^^^^^
- Support for Python 3.14.
- Compile regexes.

Removed
^^^^^^^
- Support for Python 3.9.

[0.5.0] - 2025-08-18
--------------------

Added
^^^^^
- Validation that forbid :class:`~scim2_models.PatchOp` with zero ``operations``.

Fixed
^^^^^
- Allow PATCH operations on resources and extensions root path.
- Multiple ComplexAttribute do not inherit from MultiValuedComplexAttribute by default. :issue:`72` :issue:`73`

[0.4.2] - 2025-08-05
--------------------

Fixed
^^^^^
- The library is 100% typed with mypy strict.

[0.4.1] - 2025-07-23
--------------------

Fixed
^^^^^
- Allow ``TypeVar`` as type parameters for :class:`~scim2_models.PatchOp`.

[0.4.0] - 2025-07-23
--------------------

Added
^^^^^
- Proper path validation for :attr:`~scim2_models.ResponseParameters.attributes`, :attr:`~scim2_models.ResponseParameters.excluded_attributes` and :attr:`~scim2_models.SearchRequest.sort_by`.
- Implement :meth:`~scim2_models.PatchOp.patch`

Fixed
^^^^^
- When using ``model_dump``, ignore invalid ``attributes`` and ``excluded_attributes``
  as suggested by RFC7644.
- Don't normalize attributes typed with :data:`~typing.Any`. :issue:`20`

[0.3.7] - 2025-07-17
--------------------

Fixed
^^^^^
- All non strict mypy type annotations are fixed.

[0.3.6] - 2025-07-02
--------------------

Added
^^^^^
- Fix :meth:`ResourceType.from_resource <scim2_models.ResourceType.from_resource>`
  usage for resources with several extensions. :pr:`95`

[0.3.5] - 2025-06-05
--------------------

Added
^^^^^
- Fix dynamic schema generation for user defined classes with inheritance.

[0.3.4] - 2025-06-05
--------------------

Added
^^^^^
- Implement User and Group attributes types shortcuts to match dynamically created model types.

[0.3.3] - 2025-05-21
--------------------

Fixed
^^^^^
- User class typing. :pr:`92`

[0.3.2] - 2025-03-28
--------------------

Fixed
^^^^^
- Pydantic warning.

[0.3.1] - 2025-03-07
--------------------

Fixed
^^^^^
- Fix :attr:`~scim2_models.SearchRequest.start_index` and :attr:`~scim2_models.SearchRequest.count` limits. :issue:`84`
- :attr:`~scim2_models.ListResponse.total_results` is required. :issue:`88`

[0.3.0] - 2024-12-11
--------------------

Added
^^^^^
- :meth:`Attribute.get_attribute <scim2_models.Attribute.get_attribute>` can be called with brackets.

Changed
^^^^^^^
- Add a :paramref:`~scim2_models.BaseModel.model_validate.original`
  parameter to :meth:`~scim2_models.BaseModel.model_validate`
  mandatory for :attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST`.
  This *original* value is used to look if :attr:`~scim2_models.Mutability.immutable`
  parameters have mutated.
  :issue:`86`

[0.2.12] - 2024-12-09
---------------------

Added
^^^^^
- Implement :meth:`Attribute.get_attribute <scim2_models.Attribute.get_attribute>`.

[0.2.11] - 2024-12-08
---------------------

Added
^^^^^
- Implement :meth:`Schema.get_attribute <scim2_models.Schema.get_attribute>`.
- Implement :meth:`SearchRequest.start_index_0 <scim2_models.SearchRequest.start_index_0>`
  and ``SearchRequest.start_index_1``.

[0.2.10] - 2024-12-02
---------------------

Changed
^^^^^^^
- The ``schema`` attribute is annotated with :attr:`~scim2_models.Required.true`.

Fixed
^^^^^
- ``Base64Bytes`` compatibility between pydantic 2.10+ and <2.10

[0.2.9] - 2024-12-02
--------------------

Added
^^^^^
- Implement :meth:`Resource.get_extension_model <scim2_models.Resource.get_extension_model>`.

[0.2.8] - 2024-12-02
--------------------

Added
^^^^^
- Support for Pydantic 2.10.

[0.2.7] - 2024-11-30
--------------------

Added
^^^^^
- Implement :meth:`ResourceType.from_resource <scim2_models.ResourceType.from_resource>`.

[0.2.6] - 2024-11-29
--------------------

Fixed
^^^^^
- Implement :meth:`~scim2_models.BaseModel.model_dump_json`.
- Temporarily set Pydantic 2.9 as the maximum supported version.

[0.2.5] - 2024-11-13
--------------------

Fixed
^^^^^
- :meth:`~scim2_models.BaseModel.model_validate` types.

[0.2.4] - 2024-11-03
--------------------

Fixed
^^^^^
- Python 3.9 and 3.10 compatibility.

[0.2.3] - 2024-11-01
--------------------

Added
^^^^^
- Python 3.13 support.
- Proper Base64 serialization. :issue:`31`
- :meth:`~scim2_models.BaseModel.get_field_root_type` supports :class:`~types.UnionType`.

Changed
^^^^^^^
- :attr:`SearchRequest.attributes <scim2_models.ResponseParameters.attributes>` and :attr:`SearchRequest.attributes <scim2_models.ResponseParameters.excluded_attributes>` are mutually exclusive. :issue:`19`
- :class:`~scim2_models.Schema` ids must be valid URIs. :issue:`26`

[0.2.2] - 2024-09-20
--------------------

Fixed
^^^^^
- :class:`~scim2_models.ListResponse` pydantic discriminator issue introduced with pydantic 2.9.0. :issue:`75`
- Extension payloads are not required on response contexts. :issue:`77`

[0.2.1] - 2024-09-06
--------------------

Fixed
^^^^^
- :attr:`~scim2_models.Resource.external_id` is :data:`scim2_models.CaseExact.true`. :issue:`74`

[0.2.0] - 2024-08-18
--------------------

Fixed
^^^^^
- Fix the extension mechanism by introducing the :class:`~scim2_models.Extension` class. :issue:`60`, :issue:`63`

.. note::

    ``schema.make_model()`` becomes ``Resource.from_schema(schema)`` or ``Extension.from_schema(schema)``.

Changed
^^^^^^^
- Enable pydantic :attr:`~pydantic.config.ConfigDict.validate_assignment` option. :issue:`54`

[0.1.15] - 2024-08-18
---------------------

Added
^^^^^
- Add a PEP561 ``py.typed`` file to mark the package as typed.

Fixed
^^^^^
- :class:`scim2_models.Manager` is a :class:`~scim2_models.MultiValuedComplexAttribute`. :issue:`62`

Changed
^^^^^^^
- Remove :class:`~scim2_models.ListResponse` ``of`` method in favor of regular type parameters.

.. note::

  ``ListResponse.of(User)`` becomes ``ListResponse[User]`` and ListResponse.of(User, Group)`` becomes ``ListResponse[Union[User, Group]]``.

- :data:`~scim2_models.Reference` use :data:`~typing.Literal` instead of :class:`typing.ForwardRef`.

.. note::

  ``pet: Reference["Pet"]`` becomes ``pet: Reference[Literal["Pet"]]``

[0.1.14] - 2024-07-23
---------------------

Fixed
^^^^^
- `get_by_payload` return :data:`None` on invalid payloads
- instance :meth:`~scim2_models.BaseModel.model_dump` with multiple extensions :issue:`57`

[0.1.13] - 2024-07-15
---------------------

Fixed
^^^^^
- Schema dump with context was broken.
- :attr:`scim2_models.PatchOperation.op` attribute is case insensitive to be compatible with Microsoft Entra. :issue:`55`

[0.1.12] - 2024-07-11
---------------------

Fixed
^^^^^
- Additional bugfixes about attribute case sensitivity :issue:`45`
- Dump was broken after sub-model assignments :issue:`48`
- Extension attributes dump were ignored :issue:`49`
- :class:`~scim2_models.ListResponse` tolerate any schema order :issue:`50`

[0.1.11] - 2024-07-02
---------------------

Fixed
^^^^^
- Attributes are case insensitive :issue:`39`

[0.1.10] - 2024-06-30
---------------------

Added
^^^^^
- Export resource models with :data:`~scim2_models.Resource.to_schema` :issue:`7`

[0.1.9] - 2024-06-29
--------------------

Added
^^^^^
- :data:`~scim2_models.Reference` type parameters represent SCIM ReferenceType

Fixed
^^^^^
- :attr:`~scim2_models.SearchRequest.count` and :attr:`~scim2_models.SearchRequest.start_index` validators
  supports :data:`None` values.

[0.1.8] - 2024-06-26
--------------------

Added
^^^^^
- Dynamic pydantic model creation from SCIM schemas. :issue:`6`

Changed
^^^^^^^
- Use a custom :data:`~scim2_models.Reference` type instead of :class:`~pydantic.AnyUrl` as RFC7643 reference type.

Fix
^^^
- Allow relative URLs in :data:`~scim2_models.Reference`.
- Models with multiples extensions could not be initialized. :issue:`37`

[0.1.7] - 2024-06-16
--------------------

Added
^^^^^
- :attr:`~scim2_models.SearchRequest.count` value is floored to 1
- :attr:`~scim2_models.SearchRequest.start_index` value is floored to 0
- :attr:`~scim2_models.ListResponse.resources` must be set when :attr:`~scim2_models.ListResponse.total_results` is non-null.

Fix
^^^
- Add missing default values. :issue:`33`

[0.1.6] - 2024-06-06
--------------------

Added
^^^^^
- Implement :class:`~scim2_models.CaseExact` attributes annotations.
- Implement :class:`~scim2_models.Required` attributes annotations validation.

Changed
^^^^^^^
- Refactor :code:`get_field_mutability` and :code:`get_field_returnability` in :code:`get_field_annotation`.

[0.1.5] - 2024-06-04
--------------------

Fix
^^^
- :class:`~scim2_models.Schema` is a :class:`~scim2_models.Resource`.

[0.1.4] - 2024-06-03
--------------------

Fix
^^^
- :code:`ServiceProviderConfiguration` `id` is optional.

[0.1.3] - 2024-06-03
--------------------

Changed
^^^^^^^
- Rename :code:`ServiceProviderConfiguration` to :code:`ServiceProviderConfig` to match the RFCs naming convention.

[0.1.2] - 2024-06-02
--------------------

Added
^^^^^
- Implement ``Resource.guess_by_payload``

[0.1.1] - 2024-06-01
--------------------

Changed
^^^^^^^
- Pre-defined errors are not constants anymore

[0.1.0] - 2024-06-01
--------------------

Added
^^^^^
- Initial release
