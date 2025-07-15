"""Base SCIM object classes with schema identification."""

from typing import Annotated
from typing import Any
from typing import Optional

from .annotations import Required
from .base import BaseModel
from .base import validate_attribute_urn
from .context import Context


class ScimObject(BaseModel):
    schemas: Annotated[list[str], Required.true]
    """The "schemas" attribute is a REQUIRED attribute and is an array of
    Strings containing URIs that are used to indicate the namespaces of the
    SCIM schemas that define the attributes present in the current JSON
    structure."""

    def _prepare_model_dump(
        self,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[list[str]] = None,
        excluded_attributes: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs = super()._prepare_model_dump(scim_ctx, **kwargs)
        kwargs["context"]["scim_attributes"] = [
            validate_attribute_urn(attribute, self.__class__)
            for attribute in (attributes or [])
        ]
        kwargs["context"]["scim_excluded_attributes"] = [
            validate_attribute_urn(attribute, self.__class__)
            for attribute in (excluded_attributes or [])
        ]
        return kwargs

    def model_dump(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[list[str]] = None,
        excluded_attributes: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict:
        """Create a model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        :param attributes: A multi-valued list of strings indicating the names of resource
            attributes to return in the response, overriding the set of attributes that
            would be returned by default.
        :param excluded_attributes: A multi-valued list of strings indicating the names of resource
            attributes to be removed from the default set of attributes to return.
        """
        dump_kwargs = self._prepare_model_dump(
            scim_ctx, attributes, excluded_attributes, **kwargs
        )
        if scim_ctx:
            dump_kwargs.setdefault("mode", "json")
        return super(BaseModel, self).model_dump(*args, **dump_kwargs)

    def model_dump_json(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[list[str]] = None,
        excluded_attributes: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> str:
        """Create a JSON model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump_json`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        :param attributes: A multi-valued list of strings indicating the names of resource
            attributes to return in the response, overriding the set of attributes that
            would be returned by default.
        :param excluded_attributes: A multi-valued list of strings indicating the names of resource
            attributes to be removed from the default set of attributes to return.
        """
        dump_kwargs = self._prepare_model_dump(
            scim_ctx, attributes, excluded_attributes, **kwargs
        )
        return super(BaseModel, self).model_dump_json(*args, **dump_kwargs)
