from enum import StrEnum
from pydantic import BaseModel
from typing import Any

class ToolResultType(StrEnum):
    """Enumeration for tool result types."""
    text = "text"
    image = "image"
    pyplot = "pyplot"
    plotly = "plotly"


class ToolResult(BaseModel):
    type: ToolResultType
    content: Any
    error: bool = False
    desc: str = ""