import unittest
import yaml
from yaml.loader import SafeLoader

from domain_detection_worker.domain_detector import DomainDetector
from domain_detection_worker.utils import Response, Request

with open('config/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.load(f, Loader=SafeLoader)

domain_detector = DomainDetector(**config['parameters'])


class DomainDetectionTests(unittest.TestCase):
    def test_prediction(self):
        """
        Check that prediction a list of sentences returns a valid prediction label.
        """
        text = ["Eesti on iseseisev ja sõltumatu demokraatlik vabariik, kus kõrgeima riigivõimu kandja on rahvas.",
                "Eesti iseseisvus ja sõltumatus on aegumatu ning võõrandamatu."]
        prediction = domain_detector.predict(text)
        self.assertIn(prediction, config['parameters'].labels.values())

    def test_request_response(self):
        """
        Check that a response object is returned upon request.
        """
        request = Request(text=["Eesti on iseseisev ja sõltumatu demokraatlik vabariik, kus kõrgeima riigivõimu "
                                "kandja on rahvas. Eesti iseseisvus ja sõltumatus on aegumatu ning võõrandamatu."],
                          src="et")
        response = domain_detector.process_request(request)
        self.assertIsInstance(response, Response)


if __name__ == '__main__':
    unittest.main()
