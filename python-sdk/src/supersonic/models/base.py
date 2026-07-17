"""pydantic model base class.

SuperSonic API uses camelCase (Java backend), Python convention is snake_case.
CamelModel via alias_generator + populate_by_name supports both forms for
construction and attribute access.
"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """pydantic model base with camelCase alias.

    - camelCase JSON from backend can be model_validate'd directly
    - Python side can use snake_case attribute access
    - both forms supported in construction
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",  # SuperSonic may add fields; SDK should not crash
    )
