from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class ResponseBase(BaseModel, Generic[T]):
    count: int = 0
    items: List[T] = []

class Message(BaseModel):
    message: str
