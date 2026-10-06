Compare values
==============

Use this guide when a service must compare strings in another way than scim2-models does by
default, for instance to apply the PRECIS rules that :rfc:`RFC7644 §5 <7644#section-5>` requires
for ``userName`` and ``password``. See :doc:`../explanation/comparisons` for what the default does
and why.

Write a comparison key
----------------------

A comparison key is a function with two arguments: the
:class:`~scim2_models.AttributeBinding` of an attribute, and a string value of that attribute.
It returns the string that comparisons use in place of the value, such as the value in
lowercase. Two values are equal when the key returns the same string for both. Set the function
on :attr:`~scim2_models.ScimPolicy.comparison_key`:

.. doctest::

   >>> from unicodedata import normalize
   >>> from scim2_models import ScimFilter, ScimPolicy, User, default_comparison_key

   >>> def compatibility_key(binding, value):
   ...     return default_comparison_key(binding, normalize("NFKC", value))

   >>> policy = ScimPolicy(comparison_key=compatibility_key)
   >>> user = User(user_name="bjensen")
   >>> with policy:
   ...     ScimFilter[User]('userName eq "ＢＪＥＮＳＥＮ"').match(user)
   True

The key must be deterministic, have no side effects, and return its input unchanged when given
its own output. Fall back on :func:`~scim2_models.default_comparison_key` for the attributes the
key does not handle.

Apply PRECIS to usernames and passwords
---------------------------------------

The `precis-i18n <https://github.com/byllyfish/precis_i18n#readme>`_ library implements the profiles of
:rfc:`8265`. Pick the profile from the URN of the attribute:

.. doctest::

   >>> from precis_i18n import get_profile
   >>> USER = "urn:ietf:params:scim:schemas:core:2.0:User"
   >>> PROFILES = {
   ...     f"{USER}:userName": get_profile("UsernameCaseMapped"),
   ...     f"{USER}:password": get_profile("OpaqueString"),
   ... }

   >>> def precis_key(binding, value):
   ...     profile = PROFILES.get(binding.urn)
   ...     if profile is None:
   ...         return default_comparison_key(binding, value)
   ...     return profile.enforce(value)

   >>> precis = ScimPolicy(comparison_key=precis_key)

``UsernameCaseMapped`` maps fullwidth letters to ASCII, which the default key does not:

.. doctest::

   >>> with precis:
   ...     ScimFilter[User]('userName eq "ＢＪＥＮＳＥＮ"').match(user)
   True

It also refuses strings, such as a username holding a space. ``enforce`` raises a
:exc:`UnicodeEncodeError`, which is a :exc:`ValueError`, so a request that writes such a string
is refused with ``invalidValue``:

.. doctest::

   >>> from scim2_models import Context
   >>> payload = {"schemas": [USER], "userName": "Barbara Jensen"}
   >>> User.model_validate(
   ...     payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST, scim_policy=precis
   ... )
   Traceback (most recent call last):
     ...
   pydantic_core._pydantic_core.ValidationError: 1 validation error for User
   ...

A filter comparing such a string matches nothing, except with ``ne``.

Use the policy in a service
---------------------------

Give the policy to the :class:`~scim2_models.ScimProvider` of the service, so that every request
runs under it. :doc:`scim2-server <scim2_server:index>` applies the key to its filters, sorting
and uniqueness checks.

Changing the key of a service that already holds data has two effects:

- **Values that were distinct can become equal.** Under the default key, ``ＢＪＥＮＳＥＮ`` and
  ``bjensen`` are two userNames. Under PRECIS, they are the same one, and the two users that
  hold them break the uniqueness of ``userName``.
- **Stored values can become refused.** A stored string the new key refuses is equal to no value.
  A filter does not find it, and a removal by value does not remove it. Only replacing the whole
  attribute changes it.

A :doc:`storage <scim2_server:how-to/write-a-storage>` that saves the string returned by the key
next to each value, to filter and sort in its database, must compute these strings again.
