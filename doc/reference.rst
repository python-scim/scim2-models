Reference
=========

This reference describes the public scim2-models API. It is generated from the API docstrings and
grouped by the kind of object it exposes. Use the :doc:`overview` and
:doc:`how-to guides <how-to/index>` for procedures; use :doc:`explanation/filters` for the filter
grammar.

Core models
-----------

Base classes and types used to define SCIM objects, resources, extensions, and complex
attributes.

.. automodule:: scim2_models
   :members: BaseModel, ScimObject, Resource, Extension, ComplexAttribute, MultiValuedComplexAttribute, ExtensibleStringEnum

Resource models
---------------

SCIM core resources and the complex attributes used by users and groups.

.. autoclass:: scim2_models.User
   :members:

.. autoclass:: scim2_models.Group
   :members:

.. autoclass:: scim2_models.EnterpriseUser
   :members:

.. autoclass:: scim2_models.Meta
   :members:

.. autoclass:: scim2_models.Name
   :members:

.. autoclass:: scim2_models.Address
   :members:

.. autoclass:: scim2_models.Email
   :members:

.. autoclass:: scim2_models.Entitlement
   :members:

.. autoclass:: scim2_models.GroupMember
   :members:

.. autoclass:: scim2_models.GroupMembership
   :members:

.. autoclass:: scim2_models.Im
   :members:

.. autoclass:: scim2_models.Manager
   :members:

.. autoclass:: scim2_models.PhoneNumber
   :members:

.. autoclass:: scim2_models.Photo
   :members:

.. autoclass:: scim2_models.Role
   :members:

.. autoclass:: scim2_models.X509Certificate
   :members:

Schemas and service discovery
-----------------------------

Models that describe resource schemas, resource types, and a service provider's capabilities,
and the registry gathering them.

.. autoclass:: scim2_models.ScimProvider
   :members:

.. autoclass:: scim2_models.ScimProviderError
   :members:

.. autoclass:: scim2_models.Attribute
   :members:

.. autoclass:: scim2_models.Schema
   :members:

.. autoclass:: scim2_models.ResourceType
   :members:

.. autoclass:: scim2_models.SchemaExtension
   :members:

.. autoclass:: scim2_models.ServiceProviderConfig
   :members:

.. autoclass:: scim2_models.AuthenticationScheme
   :members:

.. autoclass:: scim2_models.Patch
   :members:

.. autoclass:: scim2_models.Bulk
   :members:

.. autoclass:: scim2_models.Filter
   :members:

.. autoclass:: scim2_models.ChangePassword
   :members:

.. autoclass:: scim2_models.Sort
   :members:

.. autoclass:: scim2_models.ETag
   :members:

SCIM messages
-------------

Models for requests, responses, PATCH, search, bulk operations, response parameters, and SCIM
errors.

.. autoclass:: scim2_models.Message
   :members:

.. autoclass:: scim2_models.ListResponse
   :members:

.. autoclass:: scim2_models.SearchRequest
   :members:

.. autoclass:: scim2_models.ResponseParameters
   :members:

.. autoclass:: scim2_models.PatchOp
   :members:

.. autoclass:: scim2_models.PatchOperation
   :members:

.. autoclass:: scim2_models.BulkRequest
   :members:

.. autoclass:: scim2_models.BulkResponse
   :members:

.. autoclass:: scim2_models.BulkOperation
   :members:

.. autoclass:: scim2_models.Error
   :members:

Validation and serialization
----------------------------

The policy, contexts, annotations, and Pydantic metadata that control which attributes a SCIM
operation accepts or returns.

.. autoclass:: scim2_models.ScimPolicy
   :members:

.. autoclass:: scim2_models.Context
   :members:

.. autoclass:: scim2_models.SCIMValidator
   :members:

.. autoclass:: scim2_models.SCIMSerializer
   :members:

.. autoclass:: scim2_models.CreationRequestContext
   :members:

.. autoclass:: scim2_models.CreationResponseContext
   :members:

.. autoclass:: scim2_models.QueryRequestContext
   :members:

.. autoclass:: scim2_models.QueryResponseContext
   :members:

.. autoclass:: scim2_models.ReplacementRequestContext
   :members:

.. autoclass:: scim2_models.ReplacementResponseContext
   :members:

.. autoclass:: scim2_models.SearchRequestContext
   :members:

.. autoclass:: scim2_models.SearchResponseContext
   :members:

.. autoclass:: scim2_models.PatchRequestContext
   :members:

.. autoclass:: scim2_models.PatchResponseContext
   :members:

.. autoclass:: scim2_models.CaseExact
   :members:

.. autoclass:: scim2_models.Mutability
   :members:

.. autoclass:: scim2_models.Required
   :members:

.. autoclass:: scim2_models.Returned
   :members:

.. autoclass:: scim2_models.Uniqueness
   :members:

Errors
------

Exceptions raised when a SCIM payload or operation is invalid.

.. autoclass:: scim2_models.SCIMException
   :members:

.. autoclass:: scim2_models.InvalidFilterException
   :members:

.. autoclass:: scim2_models.InvalidPathException
   :members:

.. autoclass:: scim2_models.InvalidSyntaxException
   :members:

.. autoclass:: scim2_models.InvalidValueException
   :members:

.. autoclass:: scim2_models.InvalidVersionException
   :members:

.. autoclass:: scim2_models.MutabilityException
   :members:

.. autoclass:: scim2_models.NoTargetException
   :members:

.. autoclass:: scim2_models.PathNotFoundException
   :members:

.. autoclass:: scim2_models.SensitiveException
   :members:

.. autoclass:: scim2_models.TooManyException
   :members:

.. autoclass:: scim2_models.UniquenessException
   :members:

Identifiers and model lookup
----------------------------

Types and functions for schema identifiers, references, and model discovery.

.. autoclass:: scim2_models.URN
   :members:

.. autoclass:: scim2_models.URI
   :members:

.. autoclass:: scim2_models.External
   :members:

.. autoclass:: scim2_models.Reference
   :members:

.. autofunction:: scim2_models.get_model_by_payload

.. autofunction:: scim2_models.get_model_by_schema

Paths and filters
-----------------

Paths select SCIM attributes. Filters represent SCIM filter expressions and evaluate them against
resources. The following constants and syntax-tree types support filter parsing and translation.

.. autoclass:: scim2_models.Path
   :members:

.. autoclass:: scim2_models.AttributeBinding
   :members:

.. autoclass:: scim2_models.ScimFilter
   :members:

.. automodule:: scim2_models.path
   :members:
   :exclude-members: Path, AttributeBinding, ScimFilter

.. currentmodule:: scim2_models.path

.. data:: ORDERING_OPERATORS
   :type: frozenset[CompareOperator]

   Operators that impose an ordering, and are thus invalid on boolean and binary
   attributes per :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>`.

.. data:: STRING_OPERATORS
   :type: frozenset[CompareOperator]

   Operators that require a string operand.

.. data:: PathNode
   :type: AttrPath | ValuePath | Comparison | Present

   A parsed PATCH path, per the ``PATH`` rule of
   :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` as corrected by errata 7122:
   ``PATH = attrPath / valuePath [subAttr] / attrExp``.

Type aliases
------------

Aliases used where an API accepts more than one SCIM object or resource type.

.. data:: scim2_models.DescribedModel

   A model a schema describes: a resource, or an extension of one. This is what
   :class:`~scim2_models.ScimProvider` holds in its catalogue.

.. data:: scim2_models.AnyResource
   :type: typing.TypeVar

   Type bound to any subclass of :class:`~scim2_models.Resource`.

.. data:: scim2_models.AnyExtension
   :type: typing.TypeVar

   Type bound to any subclass of :class:`~scim2_models.Extension`.

.. data:: scim2_models.AnyScimObject
   :type: typing.TypeVar

   Type bound to any subclass of :class:`~scim2_models.ScimObject`.
