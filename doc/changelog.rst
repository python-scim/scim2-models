Changelog
=========

[0.7.0] - 2026-09-05
--------------------

Added
^^^^^
- :func:`~scim2_models.get_model_by_schema` and :func:`~scim2_models.get_model_by_payload` module functions.
  They look models up by schema, accept any sequence of :class:`~scim2_models.ScimObject` subclasses,
  and reflect the input types in the returned type.
- :class:`~scim2_models.ScimObject` and ``AnyScimObject`` are exposed in the public API, so that downstream projects can annotate values that are either resources or messages.
- :class:`~scim2_models.ExtensibleStringEnum` is exposed in the public API, so custom models
  can define string attributes that suggest canonical values without restricting them.
- :meth:`~scim2_models.BaseModel.model_validate_json` takes a ``scim_ctx`` parameter, like the
  other validation and serialization methods, so JSON payloads can be validated without being
  decoded first. :issue:`150`
- :class:`~scim2_models.ScimFilter` parses, validates and evaluates the filters of
  :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>`. Expressions compose with the Python boolean
  operators and render back to SCIM syntax, and
  :class:`~scim2_models.filters.FilterVisitor` walks them, so a SQL or ORM query can be built
  on top. See :doc:`filters`. :issue:`17`
- :attr:`~scim2_models.PatchOperation.path` supports value selections such as
  ``emails[type eq "work"].value``, honoured by :meth:`~scim2_models.PatchOp.patch` and by
  :meth:`Path.get <scim2_models.Path.get>`, :meth:`~scim2_models.Path.set` and
  :meth:`~scim2_models.Path.delete`.
- :meth:`Path.resolve <scim2_models.Path.resolve>` binds a path to the attribute it
  designates, and is what :attr:`Path.model <scim2_models.Path.model>` and its siblings are
  built on. It returns a :class:`~scim2_models.ResolvedAttribute`, now exposed in the public
  API so that downstream projects can annotate one.
- lark is a new dependency.

Changed
^^^^^^^
- ``model_dump`` and ``model_dump_json`` are defined on :class:`~scim2_models.BaseModel` instead of
  :class:`~scim2_models.ScimObject`, so every model is dumped in a SCIM context by default.
  Complex attributes dumped on their own use their SCIM attribute names:
  ``Name(family_name="Doe").model_dump()`` returns ``{"familyName": "Doe"}``
  instead of ``{"family_name": "Doe"}``.
- :meth:`~scim2_models.BaseModel.model_dump` with ``scim_ctx=None`` returns the native pydantic
  dump, ``None`` values included, as its documentation states. Pass ``exclude_none=True`` to get
  the former output.
- :meth:`~scim2_models.Resource.replace` does not mark the fields it copies from the original
  resource as set anymore, so ``model_fields_set`` only holds the attributes asserted by the
  client, as defined by :rfc:`7644` §3.5.1.
- Attributes suggesting :rfc:`7643` canonical values accept values outside of their canonical
  set, as :rfc:`7643` §2.3.1 only allows service providers to restrict them. This covers the
  ``type`` attribute of :class:`~scim2_models.Email`, :class:`~scim2_models.PhoneNumber`,
  :class:`~scim2_models.Im`, :class:`~scim2_models.Photo`, :class:`~scim2_models.Address` and
  :class:`~scim2_models.AuthenticationScheme`.
  :issue:`34`
- ``str()`` on those attributes returns the SCIM value instead of the enum representation:
  ``str(Email.Type.work)`` returns ``"work"`` instead of ``"Type.work"``.
- Canonical values are matched case-insensitively, as :rfc:`7643` §2.2 makes those attributes
  case-insensitive: ``Email(type="WORK").type`` is ``Email.Type.work``.
- The JSON schema of those attributes advertises the canonical values as ``examples`` instead of
  a restrictive ``enum``.
- The ``schemas`` attribute of SCIM payloads is built from the model definition on
  serialization, as it describes the serialized document rather than the object. It holds what
  a peer asserted, and is empty when a payload omitted it, so the omission stays visible in
  ``model_fields_set``. Objects built by the caller are still filled, as the model they are
  built from asserts their type.
- Resources omitting their ``schemas`` attribute are read instead of being rejected, which
  covers the partial responses of :rfc:`7644` §3.4.3. Their type comes from the
  :class:`~scim2_models.ListResponse` parameter, so a response holding several resource types
  still cannot decide the type of an unlabelled resource. :issue:`20`
- A ``schemas`` attribute that does not contain the model base schema is rejected whatever the
  validation context, as an object cannot contradict the model it is an instance of. It used to
  be accepted without a SCIM context.
- The ``schemas`` attribute is not subject to attribute filtering anymore, as :rfc:`7643` §3
  requires it in every representation. It lost its :attr:`~scim2_models.Returned.always`
  annotation, which :rfc:`7643` does not define for it, and which the filtering exemption
  replaces.

Fixed
^^^^^
- ``reference`` and ``binary`` attributes are case-exact, unless a schema explicitly states otherwise. :rfc:`7643` §2.3.6 and §2.3.7, `erratum 6001 <https://www.rfc-editor.org/errata/eid6001>`_
- :class:`~scim2_models.ResourceType` ``endpoint`` is case-exact. :rfc:`7643` `erratum 8475 <https://www.rfc-editor.org/errata/eid8475>`_
- :class:`~scim2_models.GroupMember` and :class:`~scim2_models.GroupMembership` ``value`` are case-exact, as they hold resource ``id`` values. :rfc:`7643` §3.1, in the spirit of `erratum 8472 <https://www.rfc-editor.org/errata/eid8472>`_
- :meth:`~scim2_models.Resource.from_schema` no longer crashes on ``reference`` attributes missing the optional ``referenceTypes``, and reads them as :class:`~scim2_models.URI` references.
- Looking a model up by schema no longer crashes when the model list mixes resources with messages such as :class:`~scim2_models.ListResponse`.
- Check recursively extensions' replace constraints.
- The ``readOnly``, ``immutable`` and ``required`` constraints of a PATCH operation are checked
  against the attribute its path resolves to, instead of against a literal field name match.
  They used to be skipped whenever the two differed, so ``userName`` could be removed and a
  path spelled ``GROUPS`` could write to a ``readOnly`` attribute, :rfc:`7643` §2.1 making
  attribute names case-insensitive.
- :attr:`Path.model <scim2_models.Path.model>`, :attr:`~scim2_models.Path.field_name`,
  :attr:`~scim2_models.Path.field_type`, :attr:`~scim2_models.Path.is_multivalued`,
  :attr:`~scim2_models.Path.urn` and :meth:`~scim2_models.Path.get_annotation` answer on every
  path shape. They used to return :data:`None` for anything but a plain attribute path, as they
  read the rendered expression instead of the attribute it designates. Accordingly,
  :attr:`Path.attr <scim2_models.Path.attr>` leaves the value selection out:
  ``emails[type eq "work"].value`` reports ``emails.value``.

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
- Cached commonly used metadata of fields to ``__scim_info__``.
- Collapsed all scim context validators in :class:`~scim2_models.BaseModel` to one model validator.
- Collapsed serialization to one model serializer in :class:`~scim2_models.BaseModel`.
- Moved ``model_dump`` and ``model_dump_json`` to :class:`~scim2_models.BaseModel`.
- Cached ``_normalize_attribute_name``.
- Simplified ``normalize_attribute_names``.

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
- The ``original`` parameter of :meth:`~scim2_models.base.BaseModel.model_validate` is deprecated. Use :meth:`~scim2_models.Resource.replace` on the validated instance instead. Will be removed in 0.8.0.

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
- :meth:`Error.from_validation_error <scim2_models.Error.from_validation_error>` to convert Pydantic :class:`~pydantic.ValidationError` to SCIM :class:`~scim2_models.Error`.
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
- Proper path validation for :attr:`~scim2_models.SearchRequest.attributes`, :attr:`~scim2_models.SearchRequest.excluded_attributes` and :attr:`~scim2_models.SearchRequest.sort_by`.
- Implement :meth:`~scim2_models.PatchOp.patch`

Fixed
^^^^^
- When using ``model_dump``, ignore invalid ``attributes`` and ``excluded_attributes``
  as suggested by RFC7644.
- Don't normalize attributes typed with :data:`Any`. :issue:`20`

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
- :attr:`~scim2_models.ListResponse.total_resuls` is required. :issue:`88`

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
  and :meth:`SearchRequest.start_index_1 <scim2_models.SearchRequest.start_index_1>`.

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
- :meth:`~BaseModel.get_field_root_type` supports :data:`~typing.UnionType`.

Changed
^^^^^^^
- :attr:`SearchRequest.attributes <scim2_models.SearchRequest.attributes>` and :attr:`SearchRequest.attributes <scim2_models.SearchRequest.excluded_attributes>` are mutually exclusive. :issue:`19`
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
- instance :meth:`~scim2_models.Resource.model_dump` with multiple extensions :issue:`57`

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
- :attr:`~scim2_models.ListResponse.resources` must be set when :attr:`~scim2_models.ListResponse.totalResults` is non-null.

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
- Implement :meth:`~scim2_models.Resource.guess_by_payload`

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
