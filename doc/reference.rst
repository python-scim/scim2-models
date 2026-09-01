Reference
=========

This page presents all the models provided by scim2-models.

.. data:: scim2_models.AnyResource
   :type: typing.TypeVar

   Type bound to any subclass of :class:`~scim2_models.Resource`.

.. data:: scim2_models.AnyScimObject
   :type: typing.TypeVar

   Type bound to any subclass of :class:`~scim2_models.ScimObject`.

.. automodule:: scim2_models
   :members:

Filters
=======

The filter abstract syntax tree and the tools to walk it, used to turn a SCIM
filter into a backend query. See :ref:`filter-transpiling` for a worked example.

.. automodule:: scim2_models.filters
   :members:
   :exclude-members: ScimFilter

.. currentmodule:: scim2_models.filters

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
