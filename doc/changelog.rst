Changelog
=========


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
- Dynamic pydantic model creation from SCIM schemas. #6

Changed
^^^^^^^
- Use a custom :data:`~scim2_models.Reference` type instead of :class:`~pydantic.AnyUrl` as RFC7643 reference type.

Fix
^^^
- Allow relative URLs in :data:`~scim2_models.Reference`.
- Models with multiples extensions could not be initialized. #37

[0.1.7] - 2024-06-16
--------------------
Added
^^^^^
- :attr:`~scim2_models.SearchRequest.count` value is floored to 1
- :attr:`~scim2_models.SearchRequest.start_index` value is floored to 0
- :attr:`~scim2_models.ListResponse.resources` must be set when :attr:`~scim2_models.ListResponse.totalResults` is non-null.

Fix
^^^
- Add missing default values. #33

[0.1.6] - 2024-06-06
--------------------
Added
^^^^^
- Implement :class:`~scim2_models.CaseExact` attributes annotations.
- Implement :class:`~scim2_models.Required` attributes annotations validation.

Changed
^^^^^^^
- Refactor :code:`get_field_mutability` and :code:`get_field_returability` in :code:`get_field_annotation`.

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
