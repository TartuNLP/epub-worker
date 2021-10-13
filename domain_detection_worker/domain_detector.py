import logging
from transformers import XLMRobertaForSequenceClassification, Trainer, AutoTokenizer
import numpy as np
from nltk import sent_tokenize

from .utils import Response, Request

logger = logging.getLogger("domain_detection")


class DomainDetector:

    def __init__(self, labels: dict, checkpoint_path: str = "models/domain-detection-model", tokenizer_path: str =
    "models/tokenizer"):
        self.labels = labels
        model = XLMRobertaForSequenceClassification.from_pretrained(checkpoint_path)
        self.trainer = Trainer(model=model)
        self.tokenizer = AutoTokenizer.from_pretrained("xlm-roberta-base", cache_dir=tokenizer_path)

    @staticmethod
    def _sentence_tokenize(text: str) -> list:
        """
        Split text into sentences.
        """
        sentences = [sent.strip() for sent in sent_tokenize(text)]
        if len(sentences) == 0:
            return ['']

        return sentences

    def predict(self, sentences: list) -> str:
        tokenized_sents = self.tokenizer(sentences)
        predictions = self.trainer.predict(tokenized_sents)
        predictions = np.argmax(predictions[0], axis=1)

        counts = np.bincount(predictions)

        return self.labels[np.argmax(counts)]

    def process_request(self, request: Request) -> Response:
        if type(request.text) == str:
            sentences = [request.text]
        else:
            sentences = [sentence for text in request.text for sentence in self._sentence_tokenize(text)]
        domain = self.predict(sentences)

        return Response(domain=domain)
