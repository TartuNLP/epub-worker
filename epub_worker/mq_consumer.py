import threading
import json
import logging
import hashlib
from sys import getsizeof
from time import time, sleep

import pika
import pika.exceptions
from pika import credentials, BlockingConnection, ConnectionParameters

from .config import mq_config
from .schemas import Request #, Response
from .ebook_tts import EBookTTS

logger = logging.getLogger(__name__)

X_EXPIRES = 60000

class MQConsumer:

    def __init__(self, ebooktts: EBookTTS):
        """
        Initializes a RabbitMQ consumer class that listens for requests for a specific worker and responds to
        them.
        """
        self.ebooktts = ebooktts
        self.routing_key = ''
        self.queue_name = None
        self.channel = None

        self._generate_queue_config()

    def _generate_queue_config(self):
        """
        Produce routing keys with the following format: exchange_name.src.tgt.domain.input_type
        """
        self.routing_key = mq_config.exchange
        hashed = hashlib.sha256(str(self.routing_key).encode('utf-8')).hexdigest()[:8]
        self.queue_name = f'{mq_config.exchange}_{hashed}'

    def start(self):
        """
        Connect to RabbitMQ and start listening for requests. Automatically tries to reconnect if the connection
        is lost.
        """
        t = threading.current_thread()
        while getattr(t, "consume", True):
            try:
                self._connect()
                setattr(t, "connected", True)
                logger.info('Ready to process requests.')
                self.channel.start_consuming()
            except pika.exceptions.AMQPConnectionError as e:
                setattr(t, "connected", False)
                logger.error(e)
                logger.info('Trying to reconnect in 5 seconds.')
                sleep(5)
            except Exception as e:
                logger.error(e)
                logger.info('Unexpected error ocurred. Exiting...')
                break

        if not getattr(t, "consume", True):
            logger.info('Interrupted by user. Exiting...')

        self.channel.close()
        setattr(t, "connected", False)

    def _connect(self):
        """
        Connects to RabbitMQ, (re)declares the exchange for the service and a queue for the worker binding
        any alternative routing keys as needed.
        """
        logger.info(f'Connecting to RabbitMQ server: {{host: {mq_config.host}, port: {mq_config.port}}}')
        connection = BlockingConnection(ConnectionParameters(
            host=mq_config.host,
            port=mq_config.port,
            credentials=credentials.PlainCredentials(
                username=mq_config.username,
                password=mq_config.password
            ),
            heartbeat=mq_config.heartbeat,
            client_properties={
                'connection_name': mq_config.connection_name
            }
        ))
        self.channel = connection.channel()
        self.channel.queue_declare(queue=self.queue_name, arguments={
            'x-expires': X_EXPIRES
        })
        self.channel.exchange_declare(exchange=mq_config.exchange, exchange_type='direct')

        self.channel.queue_bind(exchange=mq_config.exchange, queue=self.queue_name,
                                routing_key=self.routing_key)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self._on_request)

    def _on_request(self, channel: pika.adapters.blocking_connection.BlockingChannel, method: pika.spec.Basic.Deliver,
                    properties: pika.BasicProperties, body: bytes):
        """
        Pass the request to the worker and return its response.
        """
        t1 = time()
        logger.info(f"Received request: {{id: {properties.correlation_id}, size: {getsizeof(body)} bytes}}")

        try:
            request = json.loads(body)
            request = Request(**request)
            self.ebooktts.process_request(request)

        except Exception as e:
            logger.exception(e)
            self.ebooktts.respond_fail(error_message=str(e))

        channel.basic_ack(delivery_tag=method.delivery_tag)

        t2 = time()

        logger.info(f"Request processed: {{id: {properties.correlation_id}, duration: {round(t2 - t1, 3)} s}}")
