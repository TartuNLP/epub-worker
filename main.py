import threading
from argparse import ArgumentParser, FileType

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from epub_worker.config import epub_api_config, tts_api_config
from epub_worker.mq_consumer import MQConsumer
from epub_worker.ebook_tts import EBookTTS

import nltk
nltk.download('punkt')

parser = ArgumentParser()
parser.add_argument('--log-config', type=FileType('r'), default='logging/logging.ini',
                    help="Path to log config file.")
parser.add_argument('--port', type=int, default='8000',
                    help="Port used for healthcheck probes.")

args = parser.parse_args()

app = FastAPI()
mq_thread = threading.Thread()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.on_event("startup")
async def startup():
    global mq_thread
    ebooktts = EBookTTS(epub_api_config=epub_api_config, tts_api_config=tts_api_config)
    consumer = MQConsumer(ebooktts=ebooktts)

    mq_thread = threading.Thread(target=consumer.start)
    mq_thread.connected = False
    mq_thread.consume = True
    mq_thread.start()


@app.on_event("shutdown")
async def shutdown():
    global mq_thread
    mq_thread.consume = False


@app.get('/health/readiness')
@app.get('/health/startup')
async def health_check():
    # Returns 200 if models are loaded and connection to RabbitMQ is up
    global mq_thread
    if not mq_thread.is_alive() or not getattr(mq_thread, "connected"):
        raise HTTPException(500)
    return "OK"


@app.get('/health/liveness')
async def liveness():
    global mq_thread
    if not mq_thread.is_alive():
        raise HTTPException(500)
    return "OK"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_config=args.log_config.name)
