from pydantic import BaseSettings

LANGUAGES = ['et']


class MQConfig(BaseSettings):
    """
    Imports MQ configuration from environment variables
    """
    host: str = 'localhost'
    port: int = 5672
    username: str = 'guest'
    password: str = 'guest'
    exchange: str = 'speech-to-text'
    heartbeat: int = 600
    connection_name: str = 'ASR worker'

    class Config:
        env_prefix = 'mq_'


class APIConfig(BaseSettings):
    """
    API configuration from environment variables
    """
    host: str = 'localhost'
    username: str = 'user'
    password: str = 'pass'

    class Config:
        env_prefix = 'api_'


mq_config = MQConfig()
api_config = APIConfig()
