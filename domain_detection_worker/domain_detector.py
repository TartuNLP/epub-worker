import logging
from transformers import XLMRobertaForSequenceClassification, Trainer, AutoTokenizer
import numpy as np
from nltk import sent_tokenize

from .utils import Response, Request

logger = logging.getLogger("domain_detection")

labelmap = {0: "general", 1: "crisis",  2: "legal", 3: "military"}

class DomainDetector:

    def __init__(self, checkpoint_path: str = "models/domain-detection-model", tokenizer_path: str = "models/tokenizer"):
        self._model = XLMRobertaForSequenceClassification.from_pretrained(checkpoint_path)
        self.trainer = Trainer(model=self._model)
        self.tokenizer =  AutoTokenizer.from_pretrained("xlm-roberta-base", cache_dir=tokenizer_path)

    def _sentence_tokenize(self, text: Union[str, List]) -> (List, Optional[List]):
        """
        Split text into sentences.
        """
        if type(text) == str:
            sentences = [sent.strip() for sent in sent_tokenize(text)]
        else:
            sentences = [sent.strip() for sent in text]

        return sentences

    def predict(self, sentences):
        tokenized_sents = self.tokenizer(sentences)
        predictions = self.trainer.predict(tokenized_sents)
        predictions = np.argmax(predictions[0], axis=1)

        counts = np.bincount(predictions)

        return labelmap[np.argmax(counts)]

    def process_request(self, request: Request) -> Response:
        sentences = self._sentence_tokenize(request.text)
        domain = self.predict(sentences)

        return Response(domain=domain)
