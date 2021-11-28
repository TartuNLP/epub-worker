import json
from dataclasses import dataclass, asdict
from marshmallow import Schema, fields


class RequestSchema(Schema):
    correlation_id = fields.Str(required=True)
    file_extension = fields.Str(required=True)


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
        return json.dumps(asdict(self)).encode()
