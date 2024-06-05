Changelog
=========

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
