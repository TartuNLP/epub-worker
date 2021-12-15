import logging.config
from argparse import ArgumentParser, FileType

from asr_worker.config import MQConfig, APIConfig
from asr_worker.mq_consumer import MQConsumer
from asr_worker.asr import ASR


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--log-config', type=FileType('r'), default='logging/logging.ini',
                        help="Path to log config file.")
    return parser.parse_args()


def main():
    args = parse_args()
    logging.config.fileConfig(args.log_config.name)

    api_config = APIConfig()
    mq_config = MQConfig()

    asr = ASR(api_config=api_config)
    worker = MQConsumer(asr=asr, mq_config=mq_config)

    worker.start()


if __name__ == "__main__":
    main()
