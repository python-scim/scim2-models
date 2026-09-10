Access resource values with paths
=================================

Use this guide when application code needs to inspect or change a resource through a SCIM path,
rather than through a PATCH request. It assumes the
:ref:`model-parsing example <overview-model-parsing>` of the :doc:`../overview`.

Select values in a complex attribute
------------------------------------

A :class:`~scim2_models.Path` selects an attribute or values within a multi-valued attribute.
Call :meth:`~scim2_models.Path.get` to read its selection:

.. doctest::

   >>> from scim2_models import Path, User
   >>> user = User(
   ...     user_name="bjensen",
   ...     emails=[
   ...         {"type": "work", "value": "work@example.com"},
   ...         {"type": "home", "value": "home@example.com"},
   ...     ],
   ... )
   >>> path = Path[User]('emails[type eq "home"].value')
   >>> path.get(user)
   ['home@example.com']

Change the selected values
--------------------------

Use :meth:`~scim2_models.Path.set` to replace the value at a path. The path created in the
previous step selects the ``value`` sub-attribute only on the home email, so the work email is
left unchanged:

.. doctest::

   >>> path.set(user, "personal@example.com")
   True
   >>> [email.value for email in user.emails]
   ['work@example.com', 'personal@example.com']

An unfiltered path reaches every entry of a multi-valued attribute. Use one only when replacing
every selected sub-attribute is intended:

.. doctest::

   >>> Path[User]("emails.value").set(user, "shared@example.com")
   True
   >>> [email.value for email in user.emails]
   ['shared@example.com', 'shared@example.com']

Add an entry without replacing the list
----------------------------------------

By default, setting a multi-valued attribute replaces its list. Pass ``is_add=True`` to append a
new entry instead; an equivalent entry is not added twice:

.. doctest::

   >>> Path[User]("emails").set(
   ...     user,
   ...     {"type": "other", "value": "other@example.com"},
   ...     is_add=True,
   ... )
   True
   >>> [email.type.value for email in user.emails]
   ['work', 'home', 'other']

An entry type reads through ``.value``: SCIM leaves the canonical values of an attribute open, so
:attr:`Email.type <scim2_models.Email.type>` is an
:class:`~scim2_models.ExtensibleStringEnum` member rather than a plain string.

Remove values from a scalar list
--------------------------------

A multi-valued attribute whose entries are scalar values has no sub-attribute to compare. Select
one of its values with a bare comparison, then call :meth:`~scim2_models.Path.delete`:

.. doctest::

   >>> user.schemas = ["urn:ietf:params:scim:schemas:core:2.0:User", "urn:a:b:c"]
   >>> Path[User]('schemas eq "urn:a:b:c"').delete(user)
   True
   >>> user.schemas
   ['urn:ietf:params:scim:schemas:core:2.0:User']

The ``value`` convention used by SCIM implementations selects the same entry:

.. doctest::

   >>> Path[User]('schemas[value eq "urn:ietf:params:scim:schemas:core:2.0:User"]').get(user)
   ['urn:ietf:params:scim:schemas:core:2.0:User']

:doc:`../explanation/filters` explains the supported grammar differences.

Handle paths that may not apply
-------------------------------

Methods raise an exception by default when the path is invalid for the resource. For a path that
comes from optional configuration or another system, where a non-match is acceptable, pass
``strict=False`` to receive ``None`` from :meth:`~scim2_models.Path.get` or ``False`` from a
write instead:

.. doctest::

   >>> unknown = Path[User]("customAttribute")
   >>> unknown.get(user, strict=False) is None
   True
   >>> unknown.set(user, "value", strict=False)
   False
