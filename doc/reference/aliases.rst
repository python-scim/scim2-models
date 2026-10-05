Type aliases
============

Aliases used where an API accepts more than one SCIM object or resource type.

.. currentmodule:: scim2_models

.. data:: DescribedModel

   A model a schema describes: a resource, or an extension of one.
   :class:`~scim2_models.ScimProvider` holds these models in its catalog.

.. data:: AnyResource
   :type: typing.TypeVar

   Type bound to any subclass of :class:`~scim2_models.Resource`.

.. data:: AnyExtension
   :type: typing.TypeVar

   Type bound to any subclass of :class:`~scim2_models.Extension`.

.. data:: AnyScimObject
   :type: typing.TypeVar

   Type bound to any subclass of :class:`~scim2_models.ScimObject`.
