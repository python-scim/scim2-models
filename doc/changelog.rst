Changelog
=========

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
