# pydantic-scim2

Pydantic models for SCIM2 schemas defined in [RFC7643](https://www.rfc-editor.org/rfc/rfc7643) and [RFC7644](https://www.rfc-editor.org/rfc/rfc7644).
This allows to parse and produce SCIM2 payloads.

pydantic-scim2 is a fork of [pydantic-scim](https://github.com/chalk-ai/pydantic-scim) to bring support for pydantic 2.

## Installation

```shell
pip install pydantic-scim2
```

## Example

```python
from pydantic_scim2 import User
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

# Pythonize JSON SCIM payload:

user = User.model_validate(payload)
assert user.user_name == "bjensen@example.com"
assert user.meta.created == datetime.datetime(
    2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
)

# JSONify Python SCIM models:

dump = user.model_dump(
    exclude_none=True, exclude_unset=True, by_alias=True, mode="json",
)
assert dump == payload
```
