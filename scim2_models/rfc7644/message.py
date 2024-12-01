from ..base import BaseModel


class Message(BaseModel):
    """SCIM protocol messages as defined by :rfc:`RFC7644 §3.1 <7644#section-3.1>`."""

    schemas: list[str]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "scim_schema"):
            raise AttributeError(
                f"{cls.__name__} did not define a scim_schema attribute"
            )

        def init_schemas():
            return [cls.scim_schema]

        cls.model_fields["schemas"].default_factory = init_schemas
