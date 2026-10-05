Paths and filters
=================

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
