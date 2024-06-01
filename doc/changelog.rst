Changelog
=========

Unreleased
----------

Added
^^^^^

- Implement serialization and validation :class:`~pydantic_scim2.Context`

Changed
^^^^^^^
- pydantic minimum version is 2.5
- use of pydantic discriminated unions to discriminate resources

[0.2.2] - 2024-05-28
--------------------

Added
^^^^^
- expose :data:`~pydantic_scim2.AnyResource` type
- expose :class:`~pydantic_scim2.SortOrder`

Changed
^^^^^^^
- :attr:`~pydantic_scim2.Resource.id` and :attr:`~pydantic_scim2.Resource.meta` are made optional

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
- :class:`~pydantic_scim2.ListResponse` generic types
- Documentation

[0.1.0] - 2024-05-23
--------------------

Added
^^^^^
- Initial release
