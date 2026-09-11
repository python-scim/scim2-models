Overview
========

scim2-models validates, serializes, and updates **System for Cross-domain Identity Management**
(**SCIM**) resources with Pydantic. Use it in a client or server application to represent SCIM
payloads and apply SCIM validation rules. It does not provide HTTP endpoints, persistence,
authorization, or database query generation.

The :rfc:`SCIM data model <7643>` and :rfc:`SCIM protocol <7644>` specifications define the
vocabulary used here.

Install scim2-models in the application environment:

.. code-block:: shell

   pip install scim2-models

This page introduces the operations used most often by SCIM clients and servers. Follow it in
order for a first tour. The :doc:`how-to guides <how-to/index>` cover focused tasks, the
:doc:`explanations <explanation/index>` cover protocol behaviour, the
:doc:`integrations <integrations/index>` cover frameworks, and the :doc:`reference` lists the
complete API.

Create and access a resource
----------------------------

Create a resource with Python's snake-case attribute names. Dot notation uses those Python names,
while brackets accept SCIM attribute names and paths:

.. doctest::

   >>> from scim2_models import User
   >>> user = User(user_name="bjensen")
   >>> user.display_name = "Barbara Jensen"
   >>> user["nickName"] = "Babs"
   >>> user["name.familyName"] = "Jensen"
   >>> user["name.familyName"]
   'Jensen'

Remove an attribute with ``del`` or assign :data:`None`:

.. doctest::

   >>> del user["nickName"]
   >>> user.nick_name is None
   True

The :doc:`how-to/access-resource-values` guide shows how to select, change, or remove values
through paths.

.. _overview-model-parsing:

Validate and serialize SCIM payloads
------------------------------------

Pass the :class:`~scim2_models.Context` matching the HTTP operation while parsing or serializing
a payload. The context applies SCIM rules such as ignoring client-supplied, server-managed
attributes:

.. doctest::

   >>> from scim2_models import Context, ResponseParameters, User
   >>> payload = {
   ...     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
   ...     "id": "client-supplied",
   ...     "userName": "bjensen",
   ... }
   >>> user = User.model_validate(payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST)
   >>> user.id is None
   True

Use the corresponding response context to produce a SCIM response. It also applies an attribute
projection requested by a client:

.. doctest::

   >>> user.id = "2819c223-7f76-453a-919d-413861904646"
   >>> user.display_name = "Babs Jensen"
   >>> response = user.model_dump(
   ...     scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
   ...     response_parameters=ResponseParameters(excluded_attributes=["displayName"]),
   ... )
   >>> response["id"]
   '2819c223-7f76-453a-919d-413861904646'
   >>> "displayName" in response
   False

:doc:`how-to/validate-and-serialize` walks through validating creation requests, serializing
projected responses, and replacing resources. :doc:`explanation/scim-contexts` describes contexts
and attribute characteristics. The :doc:`integrations/fastapi` guide shows context type aliases
in an endpoint signature.

Read a typed collection
-----------------------

Parameterize :class:`~scim2_models.ListResponse` with the resource type expected in the
``Resources`` collection:

.. doctest::

   >>> from scim2_models import ListResponse, User
   >>> response = ListResponse[User].model_validate(
   ...     {
   ...         "totalResults": 1,
   ...         "Resources": [
   ...             {
   ...                 "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
   ...                 "userName": "bjensen",
   ...             }
   ...         ],
   ...     }
   ... )
   >>> response.resources[0].user_name
   'bjensen'

Use a union such as :class:`~scim2_models.ListResponse`\ [:class:`~scim2_models.User` |
:class:`~scim2_models.Group`] when an endpoint returns multiple resource types.

Use a schema extension
----------------------

Add a standard or custom extension as a resource type parameter. Access extension values through
the extension type:

.. doctest::

   >>> from scim2_models import EnterpriseUser, User
   >>> user = User[EnterpriseUser](user_name="bjensen")
   >>> user[EnterpriseUser] = EnterpriseUser(employee_number="701984")
   >>> user.model_dump()[
   ...     "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
   ... ]["employeeNumber"]
   '701984'

:doc:`how-to/define-custom-models` explains how to expose a resource or extension specific to one
service. :doc:`how-to/generate-models-from-schemas` explains how to create a Python model from a
schema published by another SCIM server.

.. _overview-filters:

Filter resources
----------------

Bind :class:`~scim2_models.ScimFilter` to the resource model before matching it. This validates
both the filter syntax and the attributes and operators it uses:

.. doctest::

   >>> from scim2_models import ScimFilter, User
   >>> user = User(user_name="bjensen")
   >>> ScimFilter[User]('userName sw "bje"').match(user)
   True

:doc:`how-to/build-filters` explains how to construct filters safely from dynamic values or
application choices. :doc:`explanation/filters` describes where the implemented grammar departs
from the RFC.

.. _overview-patch:

Replace and patch a resource
----------------------------

Validate a replacement with :attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST`, then use
:meth:`~scim2_models.Resource.replace` with the stored resource. This checks immutable values:

.. doctest::

   >>> replacement = User.model_validate(
   ...     {"schemas": payload["schemas"], "userName": "bjensen"},
   ...     scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
   ... )
   >>> replacement.replace(user)

Apply a :class:`~scim2_models.PatchOp` to make a partial update:

.. doctest::

   >>> from scim2_models import PatchOp
   >>> patch = PatchOp[User].model_validate(
   ...     {
   ...         "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
   ...         "Operations": [{"op": "replace", "path": "displayName", "value": "Babs"}],
   ...     },
   ...     scim_ctx=Context.RESOURCE_PATCH_REQUEST,
   ... )
   >>> patch.patch(user)
   True
   >>> user.display_name
   'Babs'

:doc:`explanation/patch` describes what an operation does, what a path selects, and which error a
rejected one answers.

Return SCIM errors
------------------

Convert a Pydantic validation error into a SCIM error response before returning it from an HTTP
endpoint:

.. doctest::

   >>> from pydantic import ValidationError
   >>> from scim2_models import Error
   >>> try:
   ...     User.model_validate(
   ...         {"userName": None},
   ...         scim_ctx=Context.RESOURCE_CREATION_REQUEST,
   ...     )
   ... except ValidationError as exc:
   ...     error = Error.from_validation_error(exc.errors()[0])
   >>> error.scim_type
   'invalidValue'

Consult the :class:`reference <scim2_models.SCIMException>` for the complete SCIM exception
hierarchy.
