import re
import io
import logging
import os
import requests
from requests.auth import HTTPBasicAuth

import vosk
from kiirkirjutaja.vad import SpeechSegmentGenerator, SpeechSegment
from kiirkirjutaja.turn import TurnGenerator
from kiirkirjutaja.asr import TurnDecoder
from kiirkirjutaja.lid import LanguageFilter
from online_scd.model import SCDModel
from kiirkirjutaja.presenters import WordByWordPresenter
from kiirkirjutaja.main import process_result

from .config import APIConfig
from .schemas import Response, Request

logger = logging.getLogger(__name__)
GAP = re.compile(r'---( ---)*')


class ASR:
    def __init__(self, api_config: APIConfig):
        self.api_config = api_config
        self.api_auth = HTTPBasicAuth(self.api_config.username, self.api_config.password)

        self.scd_model = SCDModel.load_from_checkpoint(
            "models/online-speaker-change-detector/checkpoints/epoch=102.ckpt")
        self.vosk_model = vosk.Model("models/asr_model")

        self.presenter = WordByWordPresenter(io.StringIO())
        self.language_filter = LanguageFilter()

    def predict(self, filename: str, correlation_id):
        speech_segment_generator = SpeechSegmentGenerator(filename)

        for speech_segment in speech_segment_generator.speech_segments():
            self.presenter.segment_start()
            turn_generator = TurnGenerator(self.scd_model, speech_segment)
            for i, turn in enumerate(turn_generator.turns()):
                if i > 0:
                    self.presenter.new_turn()
                self._process_turn(turn, correlation_id)
            self.presenter.segment_end()
        self._send_transcription(correlation_id, final=True)

    def _process_turn(self, turn: SpeechSegment, correlation_id: str):
        turn_decoder = TurnDecoder(self.vosk_model, self.language_filter.filter(turn.chunks()))
        for res in turn_decoder.decode_results():
            if "result" in res:
                processed_res = process_result(res)

                if res["final"]:
                    self._send_transcription(correlation_id)
                    self.presenter.final_result(processed_res["result"])
                else:
                    self.presenter.partial_result(processed_res["result"])

    def _send_transcription(self, correlation_id: id, final: bool = False):
        result = self.presenter.output_file.getvalue()
        result = GAP.sub('...', result)

        logger.debug(f'Partial result: "{result}"')
        self.presenter.output_file.close()
        response = Response(result=result, final=final)
        self.respond(response, correlation_id)
        self.presenter.output_file = io.StringIO()

    def _download_file(self, correlation_id, file_extension="wav"):
        filename = f"audio/{correlation_id}.{file_extension}"
        with requests.get(f"{self.api_config.host}/{correlation_id}/audio", auth=self.api_auth, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return filename

    def respond(self, response: Response, correlation_id: str):
        requests.post(f"{self.api_config.host}/{correlation_id}/transcription",
                      data=response.encode(),
                      auth=self.api_auth,
                      headers={'content-type': 'application/json'})

    def process_request(self, request: Request):
        filename = self._download_file(request.correlation_id, request.file_extension)
        self.predict(filename, request.correlation_id)

        if os.path.exists(filename):
            os.remove(filename)
