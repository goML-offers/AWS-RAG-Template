from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# EXAMPLES SCHEMAS
class Example(BaseModel):
    """Example schema for a single example"""

    id: str
    text: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


