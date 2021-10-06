import json
from dataclasses import dataclass, asdict
from marshmallow import Schema, fields
from typing import Optional, Union


class RequestSchema(Schema):
    text = fields.Raw(required=True, validate=(
        lambda obj: type(obj) == str or (type(obj) == list and all(type(item) == str for item in obj))),
                      )
    src = fields.Str(required=True)


@dataclass
class Request:
    """
    A dataclass that can be used to store requests
    """
    text: Optional[Union[str, list]]
    src: str


@dataclass
class Response:
    """
    A dataclass that can be used to store responses and transfer them over the message queue if needed.
    """
    domain: str = 'general'

    def encode(self) -> bytes:
        return json.dumps(asdict(self)).encode()
