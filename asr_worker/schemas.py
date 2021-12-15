import json
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder


@dataclass
class Request:
    """
    A dataclass that can be used to store requests
    """
    correlation_id: str
    file_extension: str


@dataclass
class Response:
    """
    A dataclass that can be used to store responses and transfer them over the message queue if needed.
    """
    result: str
    success: bool = True
    final: bool = True

    def encode(self) -> bytes:
        return json.dumps(self, default=pydantic_encoder).encode()
