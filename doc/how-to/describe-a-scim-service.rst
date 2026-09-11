Describe a SCIM service
=======================

Use this guide when an application needs to know, in one place, which resources a SCIM service
serves and what it supports. A :class:`~scim2_models.ScimProvider` describes both, whether the
application exposes the service or queries it.

Describe the service you expose
-------------------------------

A :class:`~scim2_models.ScimProvider` holds the attributes that describe a service. ``models``
and ``resource_types`` cover the resources it serves and the endpoints it serves them under.

``models`` is the catalogue of what the service can build: bare resources and extensions, each
identified by its schema URI. ``resource_types`` binds extensions to a resource and gives it an
endpoint, as :rfc:`RFC7643 §6 <7643#section-6>` describes. Build one from a parameterized model
with :meth:`ResourceType.from_resource <scim2_models.ResourceType.from_resource>`, which supplies
default values:

.. doctest::

   >>> from scim2_models import EnterpriseUser, Group, ResourceType, ScimProvider, User
   >>> provider = ScimProvider(
   ...     models=[User, EnterpriseUser, Group],
   ...     resource_types=[
   ...         ResourceType.from_resource(User[EnterpriseUser]),
   ...         ResourceType.from_resource(Group),
   ...     ],
   ... )
   >>> for schema in provider.schemas:
   ...     print(schema.id)
   urn:ietf:params:scim:schemas:core:2.0:User
   urn:ietf:params:scim:schemas:extension:enterprise:2.0:User
   urn:ietf:params:scim:schemas:core:2.0:Group

The provider composes the two, and an endpoint serves the composed model. Look it up by the name
the resource type declares, the name ``meta.resourceType`` carries on every resource
(:rfc:`RFC7643 §6 <7643#section-6>`). Those are the defaults at work: here the name is ``"User"``,
the last segment of the schema URI, and the endpoint is ``/Users``, that segment with an ``s``
appended. Write the :class:`~scim2_models.ResourceType` yourself when a service publishes
something else.

.. doctest::

   >>> provider.model_for("User") is User[EnterpriseUser]
   True

Leave ``resource_types`` out for a service whose resources carry no extension: the provider
derives one per resource.

Announce what the service supports
----------------------------------

``config`` is the ``/ServiceProviderConfig`` response: which operations the service supports, and
within which bounds (:rfc:`RFC7644 §4 <7644#section-4>`). Pass it alongside the models:

.. doctest::

   >>> from scim2_models import Filter, Patch, ServiceProviderConfig
   >>> config = ServiceProviderConfig(
   ...     patch=Patch(supported=True),
   ...     filter=Filter(supported=True, max_results=200),
   ... )
   >>> provider = ScimProvider(
   ...     models=[User, EnterpriseUser, Group],
   ...     resource_types=[
   ...         ResourceType.from_resource(User[EnterpriseUser]),
   ...         ResourceType.from_resource(Group),
   ...     ],
   ...     config=config,
   ... )
   >>> provider.config.filter.max_results
   200

Serve two variants of one resource
----------------------------------

Two resource types may share a base schema, declare different extensions, and serve them under
different endpoints. Their resources carry identical ``schemas``, and ``meta.resourceType`` tells
them apart (:rfc:`RFC7643 §3 <7643#section-3>`):

.. doctest::

   >>> from scim2_models import URI, Reference, SchemaExtension
   >>> staff = ResourceType(
   ...     id="Staff",
   ...     name="Staff",
   ...     endpoint=Reference[URI]("/Staff"),
   ...     schema_=Reference[URI](str(User.__schema__)),
   ...     schema_extensions=[
   ...         SchemaExtension(
   ...             schema_=Reference[URI](str(EnterpriseUser.__schema__)),
   ...             required=True,
   ...         )
   ...     ],
   ... )
   >>> provider = ScimProvider(
   ...     models=[User, EnterpriseUser],
   ...     resource_types=[ResourceType.from_resource(User), staff],
   ...     config=config,
   ... )
   >>> provider.model_for_endpoint("/Users") is User
   True
   >>> provider.model_for_endpoint("/Staff") is provider.model_for("Staff")
   True

Route a request to a model
--------------------------

:meth:`~scim2_models.ScimProvider.model_for` takes a resource type name or a schema URI, and
:meth:`~scim2_models.ScimProvider.model_for_endpoint` takes an endpoint. A name gives the composed
model, a schema URI gives the catalogue entry: the bare resource, or the extension the URI names.
Neither method takes the name of a Python class:

.. doctest::

   >>> provider.model_for("/Staff") is None
   True
   >>> provider.model_for(str(User.__schema__)) is User
   True
   >>> provider.model_for(str(EnterpriseUser.__schema__)) is EnterpriseUser
   True

Both methods return :data:`None` for an unknown key, which a server turns into a 404. Both also
resolve the three discovery resources, even though ``models`` never lists them:

.. doctest::

   >>> from scim2_models import Schema
   >>> provider.model_for_endpoint("/Schemas") is Schema
   True
   >>> provider.model_for("Pet") is None
   True

Describe the service you query
------------------------------

A client queries the three discovery endpoints and validates each response, which gives it a
``ListResponse[Schema]``, a ``ListResponse[ResourceType]`` and a
:class:`~scim2_models.ServiceProviderConfig`. Pass the ``resources`` of the first two, and the
third one, to :meth:`~scim2_models.ScimProvider.from_discovery`:

.. doctest::
   :hide:

   >>> schemas, resource_types, service_provider_config = (
   ...     provider.schemas,
   ...     provider.resource_types,
   ...     provider.config,
   ... )

.. doctest::

   >>> discovered = ScimProvider.from_discovery(
   ...     schemas, resource_types, service_provider_config
   ... )

Each schema becomes a model, a resource or an extension depending on how the resource types name
it, and the resource types bind them back together:

.. doctest::

   >>> model = discovered.model_for("Staff")
   >>> list(model.get_extension_models())
   ['urn:ietf:params:scim:schemas:extension:enterprise:2.0:User']
   >>> discovered.config.filter.max_results
   200

The provider reads back an extension a resource type declares required, and the rebuilt model
refuses a creation request that leaves it out. See :doc:`define-custom-models` for what that
annotation means.

When a resource type references a schema the service did not publish,
:meth:`~scim2_models.ScimProvider.from_discovery` raises
:class:`~scim2_models.ScimProviderError` and names the missing schema.

Diagnose a refused provider
---------------------------

A provider validates its whole description at construction, since nothing can change afterwards.
Two models sharing a schema, or two resource types sharing a name or an endpoint, raise
:class:`~scim2_models.ScimProviderError`: one key would designate two models.

Passing an already parameterized model raises it too. List the bare resource and its extensions
instead, and bind them with a resource type:

.. doctest::

   >>> from scim2_models import ScimProviderError
   >>> try:
   ...     ScimProvider(models=[User[EnterpriseUser]])
   ... except ScimProviderError as exc:
   ...     print(exc)
   User[EnterpriseUser] is already parameterized: list the bare resource and its extensions, and bind them with a resource type, as ResourceType.from_resource builds one
