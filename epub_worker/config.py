from pydantic import BaseSettings


class MQConfig(BaseSettings):
    """
    Imports MQ configuration from environment variables
    """
    host: str = 'localhost'
    port: int = 5672
    username: str = 'guest'
    password: str = 'guest'
    exchange: str = 'epub_to_audiobook'
    heartbeat: int = 3600
    connection_name: str = 'epub-worker'

    class Config:
        env_prefix = 'mq_'


class EpubAPIConfig(BaseSettings):
    """
    API configuration from environment variables
    """
    protocol: str = 'http'
    host: str = 'localhost'
    port: int = 80
    username: str = 'guest'
    password: str = 'guest'

    class Config:
        env_prefix = 'epub_'


class TtsAPIConfig(BaseSettings):
    """
    API configuration from environment variables
    """
    protocol: str = 'http'
    host: str = 'localhost'
    port: int = 5000
    username: str = 'guest'
    password: str = 'guest'

    class Config:
        env_prefix = 'tts_'


mq_config = MQConfig()
epub_api_config = EpubAPIConfig()
tts_api_config = TtsAPIConfig()
