Generate models from SCIM schemas
=================================

Use this guide when a server publishes a schema an application does not know in advance. It shows
how to turn the schema returned by ``/Schemas`` into a model that parses and serializes its
resources.

Build a resource model
----------------------

Parse the schema response, then pass it to :meth:`~scim2_models.Resource.from_schema`:

.. doctest::

   >>> from scim2_models import Attribute, Resource, Schema
   >>> schema = Schema(
   ...     id="urn:example:schemas:Pet",
   ...     name="Pet",
   ...     attributes=[
   ...         Attribute(
   ...             name="name",
   ...             type=Attribute.Type.string,
   ...             multi_valued=False,
   ...         )
   ...     ],
   ... )
   >>> Pet = Resource.from_schema(schema)
   >>> pet = Pet.model_validate({"schemas": [schema.id], "name": "Mochi"})
   >>> pet.name
   'Mochi'

The generated class uses Python field names while accepting and producing the SCIM attribute
names declared in the schema.

Build an extension model
------------------------

Use :meth:`~scim2_models.Extension.from_schema` for a schema that extends a resource.
Parameterize the resource with the generated extension before parsing its payload:

.. doctest::

   >>> from scim2_models import Extension, User
   >>> extension_schema = Schema(
   ...     id="urn:example:schemas:extension:pet:2.0:User",
   ...     name="PetOwner",
   ...     attributes=[
   ...         Attribute(
   ...             name="petName",
   ...             type=Attribute.Type.string,
   ...             multi_valued=False,
   ...         )
   ...     ],
   ... )
   >>> PetOwner = Extension.from_schema(extension_schema)
   >>> user = User[PetOwner].model_validate(
   ...     {
   ...         "schemas": [User.__schema__, extension_schema.id],
   ...         "userName": "bjensen",
   ...         extension_schema.id: {"petName": "Mochi"},
   ...     }
   ... )
   >>> user[PetOwner].pet_name
   'Mochi'

Keep the schema with the generated class. It remains the source of the schema URN and attribute
characteristics used when the model validates or serializes a resource.
