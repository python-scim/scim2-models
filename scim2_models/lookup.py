"""Helpers to find the models matching SCIM schemas."""

from collections.abc import Sequence
from typing import TYPE_CHECKING
from typing import Any

from .scim_object import AnyScimObject

if TYPE_CHECKING:
    from .resources.resource import Extension


def get_model_by_schema(
    models: Sequence[type[AnyScimObject]],
    schema: str,
    with_extensions: bool = True,
) -> "type[AnyScimObject] | type[Extension] | None":
    """Given a model list and a schema, find the matching model.

    :param models: The models to look into.
    :param schema: The schema of the model to look for.
    :param with_extensions: Whether to look into the model extensions.
    """
    from .resources.resource import Resource

    by_schema: dict[str, type[AnyScimObject] | type[Extension]] = {
        getattr(model, "__schema__", "").lower(): model for model in (models or [])
    }
    if with_extensions:
        for model in models:
            if not issubclass(model, Resource):
                continue

            by_schema.update(
                {
                    extension_schema.lower(): extension
                    for extension_schema, extension in model.get_extension_models().items()
                }
            )

    return by_schema.get(schema.lower())


def get_model_by_payload(
    models: Sequence[type[AnyScimObject]],
    payload: dict[str, Any],
    **kwargs: Any,
) -> "type[AnyScimObject] | type[Extension] | None":
    """Given a model list and a payload, find the matching model.

    :param models: The models to look into.
    :param payload: The payload which schemas are used to look for a model.
    :param kwargs: Additional parameters passed to :func:`get_model_by_schema`.
    """
    if not payload or not payload.get("schemas"):
        return None

    schema = payload["schemas"][0]
    return get_model_by_schema(models, schema, **kwargs)
