# scim2-models

[Pydantic](https://pydantic.dev/docs/) models for the SCIM schemas and protocol defined in
[RFC7643](https://datatracker.ietf.org/doc/html/rfc7643) and
[RFC7644](https://datatracker.ietf.org/doc/html/rfc7644).
It parses and produces SCIM payloads as native Python objects, and serves as a basis for SCIM
servers and clients.

## Features

- Models for the resources and messages of RFC 7643 and RFC 7644: `User`, `Group`,
  `EnterpriseUser`, `Schema`, `ResourceType`, `ServiceProviderConfig`, `ListResponse`,
  `SearchRequest`, `PatchOp` and `Error`
- Pydantic 2 models, with validation, serialization and IDE completion
- Validation and serialization per HTTP operation, driven by the SCIM attribute characteristics
  `required`, `mutability`, `returned` and `uniqueness`
- SCIM filters and paths: parsing, validation against a model, and evaluation on resources
- PATCH operations applied to a resource, with the SCIM path grammar
- Schema extensions, and conversion between SCIM schemas and Python models
- SCIM exceptions, convertible to `Error` responses

## Example

```python
from scim2_models import User
import datetime

payload = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "id": "2819c223-7f76-453a-919d-413861904646",
    "userName": "bjensen@example.com",
    "meta": {
        "resourceType": "User",
        "created": "2010-01-23T04:56:22Z",
        "lastModified": "2011-05-13T04:42:34Z",
        "version": 'W\\/"3694e05e9dff590"',
        "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    },
}

user = User.model_validate(payload)
assert user.user_name == "bjensen@example.com"
assert user.meta.created == datetime.datetime(
    2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
)
```

## Installation

```shell
pip install scim2-models
```

## Documentation

- [Overview](https://scim2-models.readthedocs.io/en/latest/overview.html) tours the models and
  the operations used by SCIM clients and servers.
- [How-to guides](https://scim2-models.readthedocs.io/en/latest/how-to/index.html) cover focused
  tasks.
- [Explanation](https://scim2-models.readthedocs.io/en/latest/explanation/index.html) covers the
  SCIM rules and the choices behind them.
- [Integrations](https://scim2-models.readthedocs.io/en/latest/integrations/index.html) build a
  SCIM server with Flask, Django, FastAPI or SQLAlchemy.
- [Reference](https://scim2-models.readthedocs.io/en/latest/reference.html) lists the public API.

## What's SCIM anyway?

SCIM stands for System for Cross-domain Identity Management, and it is a provisioning protocol.
Provisioning is the action of managing a set of resources across different services, usually users and groups.
SCIM is often used between Identity Providers and applications in completion of standards like OAuth2 and OpenID Connect.
It allows users and groups creations, modifications and deletions to be synchronized between applications.

## Getting help

Questions and bug reports go to the
[issue tracker](https://github.com/python-scim/scim2-models/issues).

## Contributing

The [contribution page](https://scim2-models.readthedocs.io/en/latest/contributing.html)
describes how to run the tests, the style checks and the documentation build.

## License

scim2-models is released under the Apache-2.0 license.

scim2-models belongs in a collection of SCIM tools developed by [Yaal Coop](https://yaal.coop),
with [scim2-client](https://github.com/python-scim/scim2-client),
[scim2-tester](https://github.com/python-scim/scim2-tester) and
[scim2-cli](https://github.com/python-scim/scim2-cli).
It started as a fork of [pydantic-scim](https://github.com/chalk-ai/pydantic-scim), to bring
support for Pydantic 2.
