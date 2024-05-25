from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class SCIM2Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
