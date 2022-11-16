FROM python:3.10-alpine

# Install system dependencies
RUN apk update && \
    apk add --no-cache \
        gcc \
        g++ \
        libffi-dev \
        musl-dev \
		gfortran \
		cmake \
		pkgconfig \
		openblas-dev \
		ffmpeg

WORKDIR /opt/app/out
WORKDIR /opt/app/epub
WORKDIR /opt/app

RUN addgroup -S app && \
    adduser -S -D -G app app && \
    chown -R app:app /opt/app && \
    chown -R app:app /opt/app/epub && \
	chown -R app:app /opt/app/out
USER app

RUN pip install --user --upgrade pip

ENV PATH="/home/app/.local/bin:${PATH}"

COPY --chown=app:app requirements.txt .
COPY --chown=app:app env.yml .

RUN pip install --user -r requirements.txt && \
	rm requirements.txt

COPY --chown=app:app . .

ENTRYPOINT ["python", "main.py"]