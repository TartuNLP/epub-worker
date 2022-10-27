# Epub to audiobook Worker

A component that automatically processes text in an epub file, sends requests to TTS API and returns zippped audio clips of every chapter.

## Setup

The worker can be used by running the prebuilt [docker image](https://ghcr.io/rlellep/epub-worker). For a manual setup,
please refer to the included Dockerfile and the pip packages specification described in `requirements.txt`. 

The worker depends on the following components:
- [RabbitMQ message broker](https://www.rabbitmq.com/)

The following environment variables should be specified when running the container:
- `MQ_HOST` - RabbitMQ host
- `MQ_PORT` (optional) - RabbitMQ port (`5672` by default)
- `MQ_USERNAME` - RabbitMQ username
- `MQ_PASSWORD` - RabbitMQ user password
- `MQ_EXCHANGE` (optional) - RabbitMQ exchange name (`epub-to-audiobook` by default)
- `MQ_CONNECTION_NAME` (optional) - friendly connection name (`epub worker` by default)
- `MQ_HEARTBEAT` (optional) - heartbeat value (`600` seconds by default)
- `API_HOST` - [Epub service api](https://ghcr.io/rlellep/epub-api) endpoint
- `API_USERNAME` - Epub service API username (`user` by default)
- `API_PASSWORD` - Epub service API password (`pass` by default)

- Optional runtime flags (the `COMMAND` option):
  - `--log-config` - path to logging config files (`logging/logging.ini` by default), `logging/debug.ini` can be used
    for debug-level logging
  - `--port` - port of the healthcheck probes (`9000` by default):

- Endpoints for healthcheck probes:
  - `/health/startup`
  - `/health/readiness`
  - `/health/liveness`

### Performance and Hardware Requirements

The following resource requirements apply when running the worker:

- *Around 16 GB memory should be enough (probably you can do with less)*
- *Fairly modern fast CPU (development machine has Intel(R) Xeon(R) CPU E5-2699 v4 @ 2.20GHz)*
- *4 free CPU cores*

### Request Format

The worker consumes epub job requests from a RabbitMQ message broker and after finishing audiobook,
responds with the audiobook file to the Epub API service.

Requests should be published with the following parameters:
- Exchange name: `epub-to-audiobook` (exchange type is `direct`)
- Message properties:
  - Correlation ID - a UID for each request that can be used to correlate requests and responses.
- JSON-formatted message content with the following keys:
  - `correlation_id` – same as the message property correlation ID
  - `file_extension` – the file extension of the uploaded audio file (.wav, .mp3, etc.)

The worker will return a response with the following parameters:
- Post request containing the audiobook zip file if the job was successful.
- JSON-formatted message content with the following key if the job failed:
  - `error` – error message encountered when job failed.