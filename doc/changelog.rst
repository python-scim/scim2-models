Changelog
=========

Unreleased
----------

Added
^^^^^

- Implement serialization and validation :class:`~scim2_models.Context`

Changed
^^^^^^^
- pydantic minimum version is 2.5
- use of pydantic discriminated unions to discriminate resources

[0.2.2] - 2024-05-28
--------------------

Added
^^^^^
- expose :data:`~scim2_models.AnyResource` type
- expose :class:`~scim2_models.SortOrder`

Changed
^^^^^^^
- :attr:`~scim2_models.Resource.id` and :attr:`~scim2_models.Resource.meta` are made optional

[0.2.1] - 2024-05-27
--------------------

Added
^^^^^
- add PyPI doc and repository links

[0.2.0] - 2024-05-27
--------------------

Added
^^^^^
- SCIM Extension support
- :class:`~scim2_models.ListResponse` generic types
- Documentation

[0.1.0] - 2024-05-23
--------------------

Added
^^^^^
- Initial release
