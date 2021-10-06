import logging

from .utils import Response, Request

logger = logging.getLogger("domain_detection")


class DomainDetector:

    def __init__(self, **kwargs):
        pass

    def process_request(self, request: Request) -> Response:
        # TODO
        return Response(domain="general")
