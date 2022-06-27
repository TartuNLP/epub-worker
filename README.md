# Automatic Speech Recognition (ASR) Worker

A component that automatically recognises speech from an audio file and transcribes it into text. The implementation
is based entirely on [Kiirkirjutaja](https://github.com/alumae/kiirkirjutaja).

## Setup

The worker can be used by running the prebuilt [docker image](https://ghcr.io/tartunlp/speech-to-text-worker). The 
container is designed to run in a CPU environment. For a manual setup, please refer to the included Dockerfile and 
the pip packages specification described in `requirements.txt`. 

The worker depends on the following components:
- [RabbitMQ message broker](https://www.rabbitmq.com/)

The following environment variables should be specified when running the container:
- `MQ_HOST` - RabbitMQ host
- `MQ_PORT` (optional) - RabbitMQ port (`5672` by default)
- `MQ_USERNAME` - RabbitMQ username
- `MQ_PASSWORD` - RabbitMQ user password
- `MQ_EXCHANGE` (optional) - RabbitMQ exchange name (`speech-to-text` by default)
- `MQ_CONNECTION_NAME` (optional) - friendly connection name (`ASR worker` by default)
- `MQ_HEARTBEAT` (optional) - heartbeat value (`600` seconds by default)
- `API_HOST` - [ASR service api](https://ghcr.io/tartunlp/speech-to-text-api) endpoint
- `API_USERNAME` - ASR service API username (`user` by default)
- `API_PASSWORD` - ASR service API password (`pass` by default)

- Optional runtime flags (the `COMMAND` option):
  - `--log-config` - path to logging config files (`logging/logging.ini` by default), `logging/debug.ini` can be used
    for debug-level logging
  - `--port` - port of the healthcheck probes (`8000` by default):

- Endpoints for healthcheck probes:
  - `/health/startup`
  - `/health/readiness`
  - `/health/liveness`

### Performance and Hardware Requirements

The resource requirements of [Kiirkirjutaja](https://github.com/alumae/kiirkirjutaja) apply when running the worker:

- *Around 16 GB memory should be enough (probably you can do with less)*
- *Fairly modern fast CPU (development machine has Intel(R) Xeon(R) CPU E5-2699 v4 @ 2.20GHz)*
- *4 free CPU cores*

### Request Format

The worker consumes speech recognition requests from a RabbitMQ message broker and responds with the transcribed text 
straight to the ASR service. 

Requests should be published with the following parameters:
- Exchange name: `speech-to-text` (exchange type is `direct`)
- Routing key: `speech-to-text.<src>` where `<src>` refers to 2-letter ISO language code of the given text. For 
  example `speech-to-text.et`
- Message properties:
  - Correlation ID - a UID for each request that can be used to correlate requests and responses.
- JSON-formatted message content with the following keys:
  - `correlation_id` – same as the message property correlation ID
  - `file_extension` – the file extension of the uploaded audio file (.wav, .mp3, etc.)

The worker will return a response with the following parameters:
- JSON-formatted message content with the following keys:
  - `success` – whether the transcription of the audio file was a success or not (boolean).
  - `result` – the transcribed text.