import logging
import os
from io import TextIOBase

from .asr_utils import Response

import ray
# Needed for loading the speaker change detection model
from pytorch_lightning.utilities import argparse_utils
setattr(argparse_utils, "_gpus_arg_default", lambda x: 0)

from vad import SpeechSegmentGenerator
from turn import TurnGenerator
from asr import TurnDecoder
from lid import LanguageFilter
from online_scd.model import SCDModel
import vosk
from unk_decoder import UnkDecoder
from compound import CompoundReconstructor
from words2numbers import Words2Numbers
from punctuate import Punctuate
from confidence import confidence_filter
from presenters import *
import utils

# Use all the available CPUs
ray.init()

RemotePunctuate = ray.remote(Punctuate)
RemoteWords2Numbers = ray.remote(Words2Numbers)

unk_decoder = UnkDecoder()
compound_reconstructor = CompoundReconstructor()
remote_words2numbers = RemoteWords2Numbers.remote()
remote_punctuate = RemotePunctuate.remote("models/punctuator/checkpoints/best.ckpt", "models/punctuator/tokenizer.json")

logger = logging.getLogger("asr")


class ASR:
    def __init__(self, transcriber_path: str = "/opt/kiirkirjutaja", clean: bool = True):
        self.transcriber_path = transcriber_path
        self.clean = clean

        self.scd_model = SCDModel.load_from_checkpoint(
            "models/online-speaker-change-detector/checkpoints/epoch=102.ckpt")
        self.vosk_model = vosk.Model("models/asr_model")

    def predict(self, filename: str, output_file: TextIOBase):
        presenter = WordByWordPresenter(output_file)

        speech_segment_generator = SpeechSegmentGenerator(f"audio/{filename}")
        language_filter = LanguageFilter()
        for speech_segment in speech_segment_generator.speech_segments():
            # print("New segment")
            presenter.segment_start()

            speech_segment_start_time = speech_segment.start_sample / 16000

            turn_generator = TurnGenerator(self.scd_model, speech_segment)
            for i, turn in enumerate(turn_generator.turns()):
                # print("New turn")
                if i > 0:
                    presenter.new_turn()
                turn_start_time = (speech_segment.start_sample + turn.start_sample) / 16000

                turn_decoder = TurnDecoder(self.vosk_model, language_filter.filter(turn.chunks()))
                for res in turn_decoder.decode_results():
                    # logging.info("Result: " + str(res))
                    if "result" in res:
                        processed_res = self._process_result(res)

                        if res["final"]:
                            presenter.final_result(processed_res["result"])
                        else:
                            presenter.partial_result(processed_res["result"])
            presenter.segment_end()

    @staticmethod
    def _process_result(result):
        result = unk_decoder.post_process(result)
        text = ""
        if "result" in result:
            text = " ".join([wi["word"] for wi in result["result"]])

            text = compound_reconstructor.post_process(text)
            text = ray.get(remote_words2numbers.post_process.remote(text))
            text = ray.get(remote_punctuate.post_process.remote(text))
            result = utils.reconstruct_full_result(result, text)
            result = confidence_filter(result)
            return result
        else:
            return result

    @staticmethod
    def _cleanup(filename):
        if os.path.exists(filename):
            os.remove(filename)
        else:
            logger.warning(f"Cleanup of file {filename} failed because file doesn't exist")

    def process_request(self, filename: str):
        basename = os.path.splitext(filename)[0]
        with open(f"output/{basename}.txt", "w") as output_file:
            logger.info(f"Output file name: {output_file}")
            self.predict(filename=filename, output_file=output_file)

        with open(f"output/{basename}.txt", "r") as prediction_file:
            result = prediction_file.read()

            if self.clean:
                self._cleanup(f"audio/{filename}")
                self._cleanup(f"output/{basename}.txt")

            return Response(result=result, success=True)
