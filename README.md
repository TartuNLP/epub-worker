# Domain Detection Worker

A component that automatically detects the domain of a given text which can be used to route translation request to the correct domain-specific machine translation model.

TODO: domain detection model description & reference to training code.

## Setup

The worker can be used by running the prebuilt [docker image](ghcr.io/project-mtee/domain-detection-worker). The 
container is designed to run in a CPU environment. For a manual setup, please refer to the included Dockerfile and 
the Conda environment specification described in `config/environment.yml`. 

The worker depends on the following components:
- [RabbitMQ message broker](https://www.rabbitmq.com/)

The following environment variables should be specified when running the container:
- `MQ_USERNAME` - RabbitMQ username
- `MQ_PASSWORD` - RabbitMQ user password
- `MQ_HOST` - RabbitMQ host
- `MQ_PORT` (optional) - RabbitMQ port (`5672` by default)

### Performance and Hardware Requirements

TODO

### Request Format

The worker consumes domain detection requests from a RabbitMQ message broker and responds with the detected domain 
name. The following format is compatible with the [text translation API](ghcr.io/project-mtee/text-translation-api).

Requests should be published with the following parameters:
- Exchange name: `domain-detection` (exchange type is `direct`)
- Routing key: `domain-detection.<src>` where `<src>` refers to 2-letter ISO language code of the given text. For 
  example `domain-detection.et`
- Message properties:
  - Correlation ID - a UID for each request that can be used to correlate requests and responses.
  - Reply To - name of the callback queue where the response should be posted.
  - Content Type - `application/json`
  - Headers:
    - `RequestId`
    - `ReturnMessageType`
- JSON-formatted message content with the following keys:
  - `text` – input text, either a string or a list of strings which are allowed to contain multiple sentences or 
    paragraphs.
  - `src` – 2-letter ISO language code

The worker will return a response with the following parameters:
- Exchange name: (empty string)
- Routing key: the Reply To property value from the request
- Message properties:
  - Correlation ID - the Correlation ID value of the request
  - Content Type - `application/json`
  - Headers:
    - `RequestId` - the `RequestId` value of the request
    - `MT-MessageType` - the `ReturnMessageType` value of the request
- JSON-formatted message content with the following keys:
  - `domain` – name of the detected domain (`general`, `legal`, `crisis` or `military`). In case of any exceptions, 
    the worker will default to `general`.