Build safe SCIM filters
=======================

Use this guide when an application builds a SCIM filter from a value supplied by a user or
another system. It assumes the :ref:`model-parsing example <overview-model-parsing>` of the
:doc:`../overview`.

Quote dynamic comparison values
-------------------------------

A filter value is syntax, not text alone. Interpolating an untrusted value directly can let its
operators and quotes change the meaning of the filter. For example, this code can turn an exact
user-name match into a filter that also matches every resource with a
:attr:`userName <scim2_models.User.user_name>`:

.. code-block:: python

   value = 'x" or userName pr or userName eq "y'
   scim_filter = ScimFilter[User](f'userName eq "{value}"')

Pass each dynamic comparison value to :meth:`ScimFilter.quote() <scim2_models.ScimFilter.quote>`
instead. It creates one SCIM string literal and escapes quotes in the value. Do not add quotes
around the placeholder.

.. doctest::

   >>> from scim2_models import ScimFilter, User
   >>> value = 'x" or userName pr or userName eq "y'
   >>> scim_filter = ScimFilter[User](f"userName eq {ScimFilter.quote(value)}")
   >>> print(scim_filter)
   userName eq "x\" or userName pr or userName eq \"y"

On Python 3.14 and later, template strings provide the same protection automatically for
interpolated values:

.. doctest::

   >>> print(ScimFilter[User](t"userName eq {value}"))  # doctest: +SKIP
   userName eq "x\" or userName pr or userName eq \"y"

Validate and allow dynamic attribute names
------------------------------------------

SCIM filter syntax has no quoted form for an attribute name. Validate a dynamic name as a
:class:`Path <scim2_models.Path>` before inserting it into a filter. A path rejects an expression
where an attribute name is required.

.. doctest::

   >>> from scim2_models import Path
   >>> attribute = Path[User]("userName")
   >>> scim_filter = ScimFilter[User](f"{attribute} eq {ScimFilter.quote('bjensen')}")
   >>> print(scim_filter)
   userName eq "bjensen"

:doc:`access-resource-values` shows how to read or change a resource after validating a path.

Choose dynamic names and operators from an allowlist
----------------------------------------------------

A valid path is not necessarily one an application should expose. Likewise, quoting cannot make a
dynamic operator safe: it is syntax, not a comparison value. Map the choices the application
accepts to a set of selected paths and operators:

.. doctest::

   >>> from scim2_models.path import CompareOperator
   >>> paths = {
   ...     "user-name": Path[User]("userName"),
   ...     "email": Path[User]("emails.value"),
   ... }
   >>> operators = {
   ...     "is": CompareOperator.eq,
   ...     "contains": CompareOperator.co,
   ... }
   >>> path = paths["user-name"]
   >>> operator = operators["is"]
   >>> print(ScimFilter[User](f"{path} {operator.value} {ScimFilter.quote('bjensen')}"))
   userName eq "bjensen"

A choice absent from these mappings is rejected. An operator or an attribute path is never
constructed directly from an untrusted string.

Use expression nodes when the filter shape is known
---------------------------------------------------

For a filter assembled by application code, expression nodes avoid hand-written SCIM syntax. They
render valid syntax and quote comparison values.

.. doctest::

   >>> from scim2_models.path import AttrPath, Comparison, CompareOperator, Present
   >>> named = Comparison(AttrPath("userName"), CompareOperator.eq, "bjensen")
   >>> active = Present(AttrPath("active"))
   >>> print(named & active)
   userName eq "bjensen" and active pr

:doc:`../explanation/filters` describes the grammar deviations and the errata applied, and
:doc:`../integrations/filter-transpiler` turns a filter into a database query.
