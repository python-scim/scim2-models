"""Base SCIM object classes with schema identification."""

from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import Optional

from .annotations import Required
from .base import BaseModel
from .context import Context

if TYPE_CHECKING:
    pass


class ScimObject(BaseModel):
    schemas: Annotated[list[str], Required.true]
    """The "schemas" attribute is a REQUIRED attribute and is an array of
    Strings containing URIs that are used to indicate the namespaces of the
    SCIM schemas that define the attributes present in the current JSON
    structure."""

    def _prepare_model_dump(
        self,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs.setdefault("context", {}).setdefault("scim", scim_ctx)

        if scim_ctx:
            kwargs.setdefault("exclude_none", True)
            kwargs.setdefault("by_alias", True)

        return kwargs

    def model_dump(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        """
        dump_kwargs = self._prepare_model_dump(scim_ctx, **kwargs)
        if scim_ctx:
            dump_kwargs.setdefault("mode", "json")
        return super(BaseModel, self).model_dump(*args, **dump_kwargs)

    def model_dump_json(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        **kwargs: Any,
    ) -> str:
        """Create a JSON model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump_json`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        """
        dump_kwargs = self._prepare_model_dump(scim_ctx, **kwargs)
        return super(BaseModel, self).model_dump_json(*args, **dump_kwargs)
