import logging

from helpers import Response, Request

import settings

logger = logging.getLogger("domain_detection")


class DomainDetectionWorker:

    def __init__(self, _):
        # TODO implement model loading & other init activities
        logger.info("All models loaded")

    def process_request(self, request: Request) -> Response:
        # TODO implement domain detection
        return Response(domain="general")


if __name__ == "__main__":
    from mq_consumer import MQConsumer

    worker = DomainDetectionWorker(**settings.WORKER_PARAMETERS)
    consumer = MQConsumer(worker=worker,
                          connection_parameters=settings.MQ_PARAMETERS,
                          exchange_name=settings.EXCHANGE_NAME,
                          routing_keys=settings.ROUTING_KEYS)

    consumer.start()
