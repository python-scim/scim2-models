Define custom SCIM models
=========================

Use this guide when a service exposes a SCIM resource or extension that is not part of the
standard models. It assumes familiarity with :doc:`../overview`.

Define a resource
-----------------

Subclass :class:`~scim2_models.Resource`, set its schema URN, and declare optional fields using
Python names. scim2-models serializes them with SCIM's camel-case names:

.. doctest::

   >>> from scim2_models import Resource, URN
   >>> class Pet(Resource):
   ...     __schema__ = URN("urn:example:schemas:Pet")
   ...     name: str | None = None
   ...
   >>> Pet(name="Mochi").model_dump()["name"]
   'Mochi'

Use :class:`~scim2_models.ComplexAttribute` for an attribute with sub-attributes. Declare fields
as optional because SCIM can omit an attribute in a valid request or response.

.. doctest::

   >>> from scim2_models import ComplexAttribute
   >>> class PetDetails(ComplexAttribute):
   ...     color: str | None = None
   ...     weight_kg: float | None = None
   ...
   >>> class Pet(Resource):
   ...     __schema__ = URN("urn:example:schemas:Pet")
   ...     name: str | None = None
   ...     details: PetDetails | None = None
   ...
   >>> pet = Pet(name="Mochi", details={"color": "ginger", "weightKg": 4.2})
   >>> pet.details.weight_kg
   4.2
   >>> pet.model_dump()["details"]
   {'color': 'ginger', 'weightKg': 4.2}

Apply SCIM attribute metadata
-----------------------------

Use :data:`typing.Annotated` to state the rules the service applies. This example requires
``name`` when a client creates or replaces a pet, preserves it after creation, and always returns
it:

.. doctest::

   >>> from typing import Annotated
   >>> from scim2_models import Mutability, Required, Returned
   >>> class Pet(Resource):
   ...     __schema__ = URN("urn:example:schemas:Pet")
   ...     name: Annotated[
   ...         str | None,
   ...         Required.true,
   ...         Mutability.immutable,
   ...         Returned.always,
   ...     ] = None

:doc:`../explanation/scim-contexts` describes when each characteristic is enforced.

Reference another resource
--------------------------

An attribute holding the URI of another resource is typed
:class:`~scim2_models.Reference`, parameterized with the resource types it may point to.
:class:`~scim2_models.External` stands for a resource outside the SCIM service, such as a photo
or a website. :meth:`~scim2_models.Resource.to_schema` publishes those types as the
``referenceTypes`` of the attribute:

.. doctest::

   >>> from scim2_models import External, Group, Reference, User
   >>> class Pet(Resource):
   ...     __schema__ = URN("urn:example:schemas:Pet")
   ...     owner: Reference[User | Group] | None = None
   ...     photo: Reference[External] | None = None
   ...
   >>> pet = Pet(owner="https://example.com/v2/Users/2819c223")
   >>> [(attribute.name, attribute.reference_types) for attribute in Pet.to_schema().attributes]
   [('owner', ['User', 'Group']), ('photo', ['external'])]

Accept values beyond the canonical ones
---------------------------------------

:rfc:`RFC7643 §7 <7643#section-7>` calls the values an attribute suggests *canonical*, and does
not close the list: a peer may send another one. Subclass
:class:`~scim2_models.ExtensibleStringEnum` to declare the expected values without rejecting the
rest, and read the value through the ``value`` of the member:

.. doctest::

   >>> from scim2_models import ExtensibleStringEnum
   >>> class Kind(ExtensibleStringEnum):
   ...     cat = "cat"
   ...     dog = "dog"
   ...
   >>> class Pet(Resource):
   ...     __schema__ = URN("urn:example:schemas:Pet")
   ...     kind: Kind | None = None
   ...
   >>> Pet.model_validate({"schemas": ["urn:example:schemas:Pet"], "kind": "cat"}).kind is Kind.cat
   True
   >>> Pet.model_validate({"schemas": ["urn:example:schemas:Pet"], "kind": "ferret"}).kind.value
   'ferret'

The standard models use the same type, which is why
:attr:`Email.type <scim2_models.Email.type>` reads through ``.value`` rather than as a plain
string.

Define an extension
-------------------

Subclass :class:`~scim2_models.Extension` for attributes that extend an existing resource. Add
the extension as the resource type parameter, then access its values through the extension type:

.. doctest::

   >>> from scim2_models import Extension, User
   >>> class PetOwner(Extension):
   ...     __schema__ = URN("urn:example:schemas:extension:pet:2.0:User")
   ...     pet_name: str | None = None
   ...
   >>> user = User[PetOwner](user_name="bjensen")
   >>> user[PetOwner] = PetOwner(pet_name="Mochi")
   >>> user.model_dump()["urn:example:schemas:extension:pet:2.0:User"]["petName"]
   'Mochi'

Publish the schema
------------------

Call :meth:`Resource.to_schema <scim2_models.Resource.to_schema>` or
:meth:`Extension.to_schema <scim2_models.Extension.to_schema>` when building a ``/Schemas``
response:

.. doctest::

   >>> Pet.to_schema().id
   'urn:example:schemas:Pet'

The :doc:`../integrations/index` integration guides show how to expose schemas, resource types, and
service-provider configuration from a server.
