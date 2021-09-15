import json
from dataclasses import dataclass, asdict
from marshmallow import Schema, fields
from typing import Optional


@dataclass
class MQItem:
    """
    Parameters of a request sent via RabbitMQ.
    """
    delivery_tag: Optional[int]
    reply_to: Optional[str]
    correlation_id: Optional[str]
    request: dict


class RequestSchema(Schema):
    text = fields.Raw(required=True, validate=(lambda obj: type(obj) in [str, list]))
    src = fields.Str(required=True)


@dataclass
class Request:
    """
    A dataclass that can be used to store requests
    # TODO convert between different ISO language code formats (post_init)
    """
    text: Optional[str, list]
    src: str


@dataclass
class Response:
    """
    A dataclass that can be used to store responses and transfer them over the message queue if needed.
    """
    domain: Optional[str] = None
    status_code: int = 200
    status: str = 'OK'

    def encode(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf8")
