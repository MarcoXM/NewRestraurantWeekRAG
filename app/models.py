import os
import time
import uuid
import boto3
from pydantic import BaseModel, Field
from typing import List, Optional



# Define request and response models
class QueryRequest(BaseModel):
    query_text: str


class QueryResult(BaseModel):
    query_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    create_time: int = Field(default_factory=lambda: int(time.time()))
    query_text: str
    answer_text: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    is_complete: bool = False