import logging.config
from os import environ
from argparse import ArgumentParser, FileType
import yaml
from yaml.loader import SafeLoader
from pika import ConnectionParameters, credentials

from domain_detection_worker.mq_consumer import MQConsumer
from domain_detection_worker.domain_detector import DomainDetector

if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument('--worker-config', type=FileType('r'), default='config/config.yaml',
                        help="The worker config YAML file to load.")
    parser.add_argument('--log-config', type=FileType('r'), default='config/logging.ini',
                        help="Path to log config file.")
    args = parser.parse_known_args()[0]
    logging.config.fileConfig(args.log_config.name)

    with open(args.worker_config.name, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=SafeLoader)

    exchange_name = 'domain-detection'

    routing_keys = []  # routing key format: exchange_name.src
    for language in config['languages']:
        # routing key format: exchange_name.src
        key = f'{exchange_name}.{language}'
        routing_keys.append(key)

    mq_parameters = ConnectionParameters(host=environ.get('MQ_HOST', 'localhost'),
                                         port=int(environ.get('MQ_PORT', '5672')),
                                         credentials=credentials.PlainCredentials(
                                             username=environ.get('MQ_USERNAME', 'guest'),
                                             password=environ.get('MQ_PASSWORD', 'guest')))

    domain_detector = DomainDetector(**config['parameters'])
    worker = MQConsumer(domain_detector=domain_detector,
                        connection_parameters=mq_parameters,
                        exchange_name=exchange_name,
                        routing_keys=routing_keys)

    worker.start()
