import logging
import os
import subprocess

from .utils import Response

logger = logging.getLogger("asr")


class ASR:
    def __init__(self, transcriber_path: str = "/opt/kaldi-offline-transcriber", nthreads: int = 1, clean: bool = True):
        self.transcriber_path = transcriber_path
        self.nthreads = nthreads
        self.clean = clean

    def predict(self, filename: str):
        basename = os.path.splitext(filename)[0]
        output_file = f"build/output/{basename}.txt"

        try:
            make_command = ["make", "-C", self.transcriber_path, f"nthreads={self.nthreads}", output_file]
            subprocess.run(make_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as e:
            logger.exception(e)

        if self.clean:
            try:
                make_command = ["make", f".{basename}.clean"]
                subprocess.run(make_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                os.remove(f"{self.transcriber_path}/src-audio/{filename}")
            except Exception as e:
                logger.exception(e)

        with open(f"{self.transcriber_path}/{output_file}") as f:
            out = f.read()
            return out

    def process_request(self, job_id: str):
        result = self.predict(filename=job_id)
        return Response(result=result, success=True)
