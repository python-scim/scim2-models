scim2-models
============

scim2-models represents the resources and messages of the SCIM protocol as
`Pydantic <https://pydantic.dev/docs/>`_ models, and applies the validation and serialization
rules of :rfc:`RFC 7643 <7643>` and :rfc:`RFC 7644 <7644>` to them. A client or a server uses it to parse the
payloads it receives, and to produce the ones it sends.

.. doctest::

   >>> from scim2_models import Context, User
   >>> user = User.model_validate(
   ...     {
   ...         "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
   ...         "id": "2819c223-7f76-453a-919d-413861904646",
   ...         "userName": "bjensen",
   ...     },
   ...     scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
   ... )
   >>> user.user_name
   'bjensen'

It provides no HTTP endpoint, no persistence and no authorization: those belong to the
application, and the :doc:`integrations <integrations/index>` show how to wire them together.

.. code-block:: shell

   pip install scim2-models

Choose a path
-------------

:doc:`Overview <overview>` gives a broad tour of the models and the operations used by
SCIM clients and servers.

:doc:`How-to guides <how-to/index>` show how to complete a specific task, such as accessing a
resource value with a SCIM path.

:doc:`Explanation <explanation/index>` gives the reasons behind the behaviour of the library, and
the SCIM rules it applies.

:doc:`Integrations <integrations/index>` shows how to build a SCIM server with Flask, Django,
FastAPI or SQLAlchemy.

:doc:`Reference <reference>` lists the complete public API.

.. toctree::
    :maxdepth: 2
    :hidden:

    Overview <overview>
    How-to guides <how-to/index>
    Explanation <explanation/index>
    Integrations <integrations/index>
    Reference <reference>
    Contributing <contributing>
    Changelog <changelog>
