from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class SCIM2Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def int_to_str(status: Optional[int]) -> Optional[str]:
    return None if status is None else str(status)
