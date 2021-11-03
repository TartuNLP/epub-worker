import json
import logging
from sys import getsizeof
from time import time, sleep
import requests
from requests.auth import HTTPBasicAuth

from typing import List

import pika
import pika.exceptions

from .utils import Request, RequestSchema, Response
from .asr import ASR

LOGGER = logging.getLogger("asr")


class MQConsumer:
    def __init__(self, asr: ASR,
                 connection_parameters: pika.connection.ConnectionParameters,
                 exchange_name: str,
                 routing_keys: List[str],
                 http_host: str,
                 http_parameters: requests.auth.HTTPBasicAuth):
        """
        Initializes a RabbitMQ consumer class that listens for requests for a specific worker

        :param asr: An ASR instance to be used.
        :param connection_parameters: RabbitMQ connection_parameters parameters.
        :param exchange_name: RabbitMQ exchange name.
        :param routing_keys: RabbitMQ routing keys. The actual queue name will also automatically include the exchange
        :param http_parameters: HTTP Basic Authentication parameters
        name to ensure that unique queues names are used.
        """
        self.asr = asr

        self.exchange_name = exchange_name
        self.routing_keys = sorted(routing_keys)
        self.queue_name = self.routing_keys[0]
        self.connection_parameters = connection_parameters
        self.channel = None

        self.http_host = http_host
        self.http_parameters = http_parameters

    def start(self):
        """
        Connect to RabbitMQ and start listening for requests. Automatically tries to reconnect if the connection
        is lost.
        """
        while True:
            try:
                self._connect()
                LOGGER.info('Ready to process requests.')
                self.channel.start_consuming()
            except pika.exceptions.AMQPConnectionError as e:
                LOGGER.error(e)
                LOGGER.info('Trying to reconnect in 5 seconds.')
                sleep(5)
            except KeyboardInterrupt:
                LOGGER.info('Interrupted by user. Exiting...')
                self.channel.close()
                break

    def _connect(self):
        """
        Connects to RabbitMQ, (re)declares the exchange for the service and a queue for the worker binding
        any alternative routing keys as needed.
        """
        LOGGER.info(f'Connecting to RabbitMQ server: {{host: {self.connection_parameters.host}, '
                    f'port: {self.connection_parameters.port}}}')
        connection = pika.BlockingConnection(self.connection_parameters)
        self.channel = connection.channel()
        self.channel.queue_declare(queue=self.queue_name)
        self.channel.exchange_declare(exchange=self.exchange_name, exchange_type='direct')

        for route in self.routing_keys:
            self.channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name, routing_key=route)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self._on_request)

    def _on_request(self, channel: pika.adapters.blocking_connection.BlockingChannel, method: pika.spec.Basic.Deliver,
                    properties: pika.BasicProperties, body: bytes):
        """
        Pass the request to the worker and return its response.
        """
        t1 = time()
        LOGGER.info(f"Received request: {{id: {properties.correlation_id}, size: {getsizeof(body)} bytes}}")

        try:
            request = json.loads(body)
            request = RequestSchema().load(request)
            request = Request(**request)

            job_id = request.correlation_id
            file_extension = request.file_extension

            audio_response = requests.get(f"{self.http_host}/{job_id}/audio", auth=self.http_parameters)

            audio_response.raise_for_status()

            with open(f"{self.asr.transcriber_path}/src-audio/{job_id}.{file_extension}", "wb") as file:
                file.write(audio_response.content)
                response = self.asr.process_request(f"{job_id}.{file_extension}")

        except Exception as e:
            LOGGER.exception(e)
            response = Response(success=False, result='Internal exception')

        response_size = getsizeof(response)

        LOGGER.info(f"Transcription done, now sending it to {self.http_host}/{properties.correlation_id}/transcription")

        request = requests.post(f"{self.http_host}/{properties.correlation_id}/transcription",
                                data=response.encode(),
                                auth=self.http_parameters)
        if request.status_code == 200:
            # Send an acknowledgment to RabbitMQ
            channel.basic_ack(delivery_tag=method.delivery_tag)

        t2 = time()

        LOGGER.info(f"Request processed: {{id: {properties.correlation_id}, duration: {round(t2 - t1, 3)} s, "
                    f"size: {response_size} bytes}}")
